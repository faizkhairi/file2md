"""Tests for the main conversion dispatcher."""

from pathlib import Path

from file2md.convert import convert_file
from file2md.utils import ConversionOptions, ExitCode


class TestConvertFile:
    def test_converts_pdf(self, sample_pdf: Path) -> None:
        result = convert_file(sample_pdf)
        assert result.exit_code == ExitCode.SUCCESS
        assert len(result.markdown) > 0

    def test_converts_docx(self, sample_docx: Path) -> None:
        result = convert_file(sample_docx)
        assert result.exit_code == ExitCode.SUCCESS
        assert len(result.markdown) > 0

    def test_unsupported_file(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello")
        result = convert_file(txt_file)
        assert result.exit_code == ExitCode.UNSUPPORTED_FILE

    def test_missing_file(self, tmp_path: Path) -> None:
        result = convert_file(tmp_path / "nonexistent.pdf")
        assert result.exit_code == ExitCode.EXTRACTION_FAILED

    def test_options_passed_through(self, sample_pdf: Path) -> None:
        options = ConversionOptions(frontmatter=True, page_labels=True)
        result = convert_file(sample_pdf, options)
        assert "---\n" in result.markdown
        assert "## Page" in result.markdown

    def test_default_options(self, sample_pdf: Path) -> None:
        result = convert_file(sample_pdf, None)
        assert result.exit_code == ExitCode.SUCCESS

    def test_string_path(self, sample_pdf: Path) -> None:
        result = convert_file(str(sample_pdf))
        assert result.exit_code == ExitCode.SUCCESS
