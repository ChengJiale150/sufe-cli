from pathlib import Path

import pytest
import typer

from sufe_cli.commands.canvas.assignment import _upload_single_file, submit_assignment
from sufe_cli.errors import UploadFailedError


class DummyResponse:
    def __init__(self, data: dict | None = None, status_code: int = 200, headers: dict | None = None) -> None:
        self._data = data or {}
        self.status_code = status_code
        self.headers = headers or {}

    def json(self) -> dict:
        return self._data


class DummyUploadResponse:
    """模拟 Step 2 的上传响应（requests.post 返回）"""

    def __init__(self, status_code: int = 302, headers: dict | None = None) -> None:
        self.status_code = status_code
        self.headers = headers or {}


def _build_upload_mocks(
    monkeypatch: pytest.MonkeyPatch,
    file_ids: list[int],
    step2_status: int = 302,
    step1_error: dict | None = None,
) -> None:
    """构建三步上传的 mock，支持多个文件"""
    upload_index = [0]

    def mock_sufe_post(url: str, **kwargs) -> DummyResponse:
        # Step 1: 上传准备
        if "/submissions/self/files" in url:
            if step1_error:
                return DummyResponse(step1_error)
            return DummyResponse(
                {
                    "upload_url": "https://upload.example.com/",
                    "upload_params": {"key": "value"},
                }
            )
        # Final: 提交作业
        if "/submissions" in url and "/self/files" not in url:
            return DummyResponse(
                {
                    "id": 999,
                    "assignment_id": 456,
                    "attempt": 2,
                    "submitted_at": "2025-12-15T14:30:00Z",
                    "late": False,
                }
            )
        return DummyResponse({})

    def mock_requests_post(url: str, **kwargs) -> DummyUploadResponse:
        if url == "https://upload.example.com/":
            idx = upload_index[0]
            upload_index[0] += 1
            return DummyUploadResponse(
                status_code=step2_status,
                headers={"Location": f"https://canvas.shufe.edu.cn/api/v1/files/{file_ids[idx]}"},
            )
        return DummyUploadResponse()

    def mock_sufe_get(url: str, **kwargs) -> DummyResponse:
        idx = upload_index[0] - 1
        file_id = file_ids[idx] if idx < len(file_ids) else file_ids[0]
        return DummyResponse(
            {
                "id": file_id,
                "display_name": f"test_{file_id}.pdf",
                "filename": f"test_{file_id}.pdf",
                "size": 1024,
            }
        )

    monkeypatch.setattr("sufe_cli.commands.canvas.assignment.sufe_post_canvas", mock_sufe_post)
    monkeypatch.setattr("sufe_cli.commands.canvas.assignment.sufe_get_canvas", mock_sufe_get)
    monkeypatch.setattr("sufe_cli.commands.canvas.assignment.requests.post", mock_requests_post)


def test_submit_single_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """测试单文件上传并提交"""
    test_file = tmp_path / "hw1.pdf"
    test_file.write_bytes(b"hello")

    _build_upload_mocks(monkeypatch, file_ids=[123])

    submit_assignment(
        course_id=100,
        assignment_id=200,
        files=[test_file],
        comment=None,
    )

    captured = capsys.readouterr()
    output = captured.out

    assert "作业提交成功" in output
    assert "尝试次数: 2" in output
    assert "提交时间: 2025-12-15 22:30" in output
    assert "状态: 正常" in output
    assert "test_123.pdf" in output


def test_submit_multiple_files(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """测试多文件上传并提交"""
    file1 = tmp_path / "hw1.pdf"
    file1.write_bytes(b"hello")
    file2 = tmp_path / "hw2.pdf"
    file2.write_bytes(b"world")

    _build_upload_mocks(monkeypatch, file_ids=[111, 222])

    submit_assignment(
        course_id=100,
        assignment_id=200,
        files=[file1, file2],
        comment=None,
    )

    captured = capsys.readouterr()
    output = captured.out

    assert "文件 (2 个):" in output
    assert "test_111.pdf" in output
    assert "test_222.pdf" in output


def test_submit_with_comment(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """测试带评论提交"""
    test_file = tmp_path / "hw1.pdf"
    test_file.write_bytes(b"hello")

    _build_upload_mocks(monkeypatch, file_ids=[123])

    submit_assignment(
        course_id=100,
        assignment_id=200,
        files=[test_file],
        comment="这是我的作业",
    )

    captured = capsys.readouterr()
    output = captured.out

    assert "评论: 这是我的作业" in output


def test_submit_file_not_found(tmp_path: Path) -> None:
    """测试文件不存在时提前退出"""
    missing_file = tmp_path / "not_exist.pdf"

    with pytest.raises(typer.Exit):
        submit_assignment(
            course_id=100,
            assignment_id=200,
            files=[missing_file],
            comment=None,
        )


def test_submit_step1_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """测试 Step 1 上传准备失败"""
    test_file = tmp_path / "hw1.pdf"
    test_file.write_bytes(b"hello")

    _build_upload_mocks(
        monkeypatch,
        file_ids=[123],
        step1_error={"errors": [{"message": "文件大小超过限制"}]},
    )

    with pytest.raises(UploadFailedError):
        _upload_single_file(
            course_id=100,
            assignment_id=200,
            file_path=test_file,
            assignment_page="https://canvas.shufe.edu.cn/courses/100/assignments/200",
        )


def test_submit_step2_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """测试 Step 2 文件上传失败"""
    test_file = tmp_path / "hw1.pdf"
    test_file.write_bytes(b"hello")

    _build_upload_mocks(monkeypatch, file_ids=[123], step2_status=500)

    with pytest.raises(UploadFailedError):
        _upload_single_file(
            course_id=100,
            assignment_id=200,
            file_path=test_file,
            assignment_page="https://canvas.shufe.edu.cn/courses/100/assignments/200",
        )
