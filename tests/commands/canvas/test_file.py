import pytest

from sufe_cli.commands.canvas.file import download_file


class DummyStreamResponse:
    def __init__(self, content: bytes = b"test content", filename: str = "test.pdf") -> None:
        self.content = content
        self.headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        self.status_code = 200

    def iter_content(self, chunk_size: int = 8192):
        yield self.content


def test_download_file_default_path(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """测试文件下载到当前目录"""
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.file.sufe_get_canvas",
        lambda url, **kwargs: DummyStreamResponse(b"hello world", "hw1.pdf"),
    )

    download_file(file_id=1185673, output=None)

    saved_file = tmp_path / "hw1.pdf"
    assert saved_file.exists()
    assert saved_file.read_bytes() == b"hello world"


def test_download_file_to_directory(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """测试文件下载到指定目录"""
    target_dir = tmp_path / "downloads"
    target_dir.mkdir()

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.file.sufe_get_canvas",
        lambda url, **kwargs: DummyStreamResponse(b"hello world", "hw2.pdf"),
    )

    download_file(file_id=1185673, output=str(target_dir))

    saved_file = target_dir / "hw2.pdf"
    assert saved_file.exists()
    assert saved_file.read_bytes() == b"hello world"


def test_download_file_to_specific_path(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """测试文件下载到指定文件路径"""
    target_file = tmp_path / "custom_name.pdf"

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.file.sufe_get_canvas",
        lambda url, **kwargs: DummyStreamResponse(b"hello world", "original.pdf"),
    )

    download_file(file_id=1185673, output=str(target_file))

    assert target_file.exists()
    assert target_file.read_bytes() == b"hello world"


def test_download_file_without_disposition(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """测试没有 Content-Disposition 时的默认文件名"""
    monkeypatch.chdir(tmp_path)

    response = DummyStreamResponse(b"hello world", "")
    response.headers = {}

    monkeypatch.setattr(
        "sufe_cli.commands.canvas.file.sufe_get_canvas",
        lambda url, **kwargs: response,
    )

    download_file(file_id=1185673, output=None)

    saved_file = tmp_path / "canvas_file"
    assert saved_file.exists()
    assert saved_file.read_bytes() == b"hello world"
