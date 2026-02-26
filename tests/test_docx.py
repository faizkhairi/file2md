"""Tests for DOCX conversion."""

from pathlib import Path

from file2md.docx_converter import convert_docx
from file2md.utils import ConversionOptions, ExitCode


class TestConvertDocx:
    def test_basic_conversion(self, sample_docx: Path) -> None:
        result = convert_docx(sample_docx, ConversionOptions())
        assert result.exit_code == ExitCode.SUCCESS
        assert "<!-- source:" in result.markdown
        assert "file2md" in result.markdown

    def test_headings(self, sample_docx: Path) -> None:
        result = convert_docx(sample_docx, ConversionOptions())
        assert "# Test Document" in result.markdown
        assert "## Section Two" in result.markdown
        assert "## Data Table" in result.markdown
        assert "## Conclusion" in result.markdown

    def test_bullet_list(self, sample_docx: Path) -> None:
        result = convert_docx(sample_docx, ConversionOptions())
        assert "- First bullet item" in result.markdown
        assert "- Second bullet item" in result.markdown

    def test_numbered_list(self, sample_docx: Path) -> None:
        result = convert_docx(sample_docx, ConversionOptions())
        assert "1. First numbered item" in result.markdown
        assert "1. Second numbered item" in result.markdown

    def test_table(self, sample_docx: Path) -> None:
        result = convert_docx(sample_docx, ConversionOptions())
        assert "| Name | Age | City |" in result.markdown
        assert "| --- | --- | --- |" in result.markdown
        assert "Alice" in result.markdown
        assert "Bob" in result.markdown

    def test_inline_formatting(self, formatted_docx: Path) -> None:
        result = convert_docx(formatted_docx, ConversionOptions())
        assert "**bold text**" in result.markdown
        assert "*italic text*" in result.markdown

    def test_with_frontmatter(self, sample_docx: Path) -> None:
        options = ConversionOptions(frontmatter=True)
        result = convert_docx(sample_docx, options)
        assert result.markdown.startswith("---\n")
        assert "source:" in result.markdown

    def test_with_clean(self, sample_docx: Path) -> None:
        options = ConversionOptions(clean=True)
        result = convert_docx(sample_docx, options)
        assert result.exit_code == ExitCode.SUCCESS
        assert result.markdown.endswith("\n")

    def test_max_chars_truncation(self, sample_docx: Path) -> None:
        options = ConversionOptions(max_chars=50)
        result = convert_docx(sample_docx, options)
        assert "truncated" in result.markdown

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        result = convert_docx(tmp_path / "nope.docx", ConversionOptions())
        assert result.exit_code == ExitCode.EXTRACTION_FAILED
