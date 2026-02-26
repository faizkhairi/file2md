"""Tests for the FastAPI web server."""

from pathlib import Path

from fastapi.testclient import TestClient

from file2md.web import app

client = TestClient(app)

DEFAULT_DATA = {
    "clean": "false",
    "frontmatter": "false",
    "page_labels": "false",
    "extract_tables": "false",
}


class TestHealthEndpoint:
    def test_health(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestIndexPage:
    def test_index_returns_html(self) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "file2md" in resp.text


class TestConvertEndpoint:
    def test_upload_pdf(self, sample_pdf: Path) -> None:
        with open(sample_pdf, "rb") as f:
            resp = client.post(
                "/convert",
                files={"file": ("test.pdf", f, "application/pdf")},
                data=DEFAULT_DATA,
            )
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        disp = resp.headers["content-disposition"]
        assert 'attachment; filename="test.md"' in disp
        assert "<!-- source:" in resp.text

    def test_upload_docx(self, sample_docx: Path) -> None:
        with open(sample_docx, "rb") as f:
            resp = client.post(
                "/convert",
                files={"file": ("test.docx", f, "application/octet-stream")},
                data=DEFAULT_DATA,
            )
        assert resp.status_code == 200
        assert "# Test Document" in resp.text

    def test_unsupported_file_type(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello")
        with open(txt_file, "rb") as f:
            resp = client.post(
                "/convert",
                files={"file": ("test.txt", f, "text/plain")},
                data=DEFAULT_DATA,
            )
        assert resp.status_code == 415

    def test_oversized_file(self, tmp_path: Path) -> None:
        small_pdf = tmp_path / "small.pdf"
        small_pdf.write_bytes(b"%PDF-" + b"x" * 100)
        with open(small_pdf, "rb") as f:
            resp = client.post(
                "/convert",
                files={"file": ("small.pdf", f, "application/pdf")},
                data=DEFAULT_DATA,
            )
        # Will fail due to invalid PDF, but should NOT be 413
        assert resp.status_code != 413

    def test_scanned_pdf(self, scanned_pdf: Path) -> None:
        with open(scanned_pdf, "rb") as f:
            resp = client.post(
                "/convert",
                files={"file": ("scanned.pdf", f, "application/pdf")},
                data=DEFAULT_DATA,
            )
        assert resp.status_code == 422

    def test_with_options(self, sample_pdf: Path) -> None:
        data = {
            "clean": "true",
            "frontmatter": "true",
            "page_labels": "true",
            "extract_tables": "false",
        }
        with open(sample_pdf, "rb") as f:
            resp = client.post(
                "/convert",
                files={"file": ("test.pdf", f, "application/pdf")},
                data=data,
            )
        assert resp.status_code == 200
        assert "---\n" in resp.text
