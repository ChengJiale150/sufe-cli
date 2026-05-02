import re
from pathlib import Path

import typer

from sufe_cli.client.http import sufe_get_canvas

CANVAS_BASE = "https://canvas.shufe.edu.cn"

app = typer.Typer(help="Canvas 文件相关命令")


def _extract_filename(response) -> str:
    """从 Content-Disposition header 中提取文件名"""
    disposition = response.headers.get("Content-Disposition", "")
    match = re.search(r'filename="?([^"]+)"?', disposition)
    if match:
        return match.group(1)
    return "canvas_file"


@app.command(name="download")
def download_file(
    file_id: int = typer.Option(..., "--id", help="文件 ID"),
    output: str | None = typer.Option(None, "--output", "-o", help="保存路径（文件或目录，默认为当前目录）"),
):
    """下载 Canvas 文件"""
    url = f"{CANVAS_BASE}/files/{file_id}/download?download_frd=1"
    response = sufe_get_canvas(url, stream=True)

    if output is None:
        save_path = Path.cwd() / _extract_filename(response)
    else:
        output_path = Path(output)
        if output_path.is_dir() or output.endswith(("/", "\\")):
            save_path = output_path / _extract_filename(response)
        else:
            save_path = output_path

    try:
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        typer.secho(f"文件保存失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    typer.secho(f"文件已保存: {save_path}", fg=typer.colors.GREEN)
