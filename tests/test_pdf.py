"""Tests for PDF conversion."""

from pathlib import Path

import pymupdf

from file2md.pdf import convert_pdf, is_scanned_page
from file2md.utils import ConversionOptions, ExitCode


class TestConvertPdf:
    def test_basic_conversion(self, sample_pdf: Path) -> None:
        result = convert_pdf(sample_pdf, ConversionOptions())
        assert result.exit_code == ExitCode.SUCCESS
        assert result.page_count == 3
        assert "<!-- source:" in result.markdown
        assert "file2md" in result.markdown

    def test_with_clean(self, sample_pdf: Path) -> None:
        options = ConversionOptions(clean=True)
        result = convert_pdf(sample_pdf, options)
        assert result.exit_code == ExitCode.SUCCESS
        assert len(result.markdown) > 0

    def test_with_frontmatter(self, sample_pdf: Path) -> None:
        options = ConversionOptions(frontmatter=True)
        result = convert_pdf(sample_pdf, options)
        assert result.markdown.startswith("---\n")
        assert "source:" in result.markdown
        assert "converted:" in result.markdown

    def test_with_page_labels(self, sample_pdf: Path) -> None:
        options = ConversionOptions(page_labels=True)
        result = convert_pdf(sample_pdf, options)
        assert "## Page 1" in result.markdown
        assert "## Page 2" in result.markdown

    def test_page_separators(self, sample_pdf: Path) -> None:
        result = convert_pdf(sample_pdf, ConversionOptions())
        assert "---" in result.markdown

    def test_scanned_pdf_detection(self, scanned_pdf: Path) -> None:
        result = convert_pdf(scanned_pdf, ConversionOptions())
        assert result.exit_code == ExitCode.SCANNED_PDF
        assert result.markdown == ""

    def test_single_page(self, single_page_pdf: Path) -> None:
        result = convert_pdf(single_page_pdf, ConversionOptions())
        assert result.exit_code == ExitCode.SUCCESS
        assert "Hello World" in result.markdown

    def test_max_chars_truncation(self, sample_pdf: Path) -> None:
        options = ConversionOptions(max_chars=100)
        result = convert_pdf(sample_pdf, options)
        assert "truncated" in result.markdown

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        result = convert_pdf(tmp_path / "nope.pdf", ConversionOptions())
        assert result.exit_code == ExitCode.EXTRACTION_FAILED


class TestIsScannedPage:
    def test_text_page_not_scanned(self, single_page_pdf: Path) -> None:
        doc = pymupdf.open(str(single_page_pdf))
        assert not is_scanned_page(doc[0])
        doc.close()

    def test_empty_page_not_scanned(self, empty_pdf: Path) -> None:
        doc = pymupdf.open(str(empty_pdf))
        # Empty page with no text AND no images is not "scanned"
        assert not is_scanned_page(doc[0])
        doc.close()
