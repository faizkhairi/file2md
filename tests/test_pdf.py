"""Tests for PDF conversion."""

from pathlib import Path

import pymupdf

from file2md.pdf import _detect_images, _strip_leading_spaces, convert_pdf, is_scanned_page
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


class TestStripLeadingSpaces:
    def test_strips_indented_lines(self) -> None:
        text = "   Indented line\n      More indented\nNormal"
        result = _strip_leading_spaces(text)
        assert result == "Indented line\nMore indented\nNormal"

    def test_preserves_empty_lines(self) -> None:
        text = "Line 1\n\nLine 2"
        result = _strip_leading_spaces(text)
        assert result == "Line 1\n\nLine 2"


class TestDetectImages:
    def test_detects_large_image(self, pdf_with_images: Path) -> None:
        doc = pymupdf.open(str(pdf_with_images))
        result = _detect_images(doc[0], 1)
        assert "<!-- [image: figure on page 1] -->" in result
        doc.close()

    def test_no_images_on_text_page(self, single_page_pdf: Path) -> None:
        doc = pymupdf.open(str(single_page_pdf))
        result = _detect_images(doc[0], 1)
        assert result == ""
        doc.close()

    def test_empty_page_no_images(self, empty_pdf: Path) -> None:
        doc = pymupdf.open(str(empty_pdf))
        result = _detect_images(doc[0], 1)
        assert result == ""
        doc.close()


class TestPipelineIntegration:
    def test_clean_strips_leading_spaces(self, pdf_with_leading_spaces: Path) -> None:
        options = ConversionOptions(clean=True)
        result = convert_pdf(pdf_with_leading_spaces, options)
        # Lines should not start with excessive whitespace
        for line in result.markdown.split("\n"):
            stripped = line.lstrip()
            if stripped:
                # Allow up to 1 space (from markdown formatting) but not 5+
                assert len(line) - len(stripped) < 5, f"Excessive leading space: {line!r}"

    def test_clean_detects_4_line_headers(self, pdf_with_4_line_headers: Path) -> None:
        options = ConversionOptions(clean=True)
        result = convert_pdf(pdf_with_4_line_headers, options)
        # "Confidential" appears on every page — should be removed
        # Count occurrences in content (excluding the removed patterns comment)
        content_lines = [
            line for line in result.markdown.split("\n")
            if not line.startswith("<!-- Removed")
        ]
        content = "\n".join(content_lines)
        assert "Confidential" not in content

    def test_image_placeholders_in_clean_mode(self, pdf_with_images: Path) -> None:
        options = ConversionOptions(clean=True)
        result = convert_pdf(pdf_with_images, options)
        assert "<!-- [image: figure on page 1] -->" in result.markdown

    def test_no_image_placeholders_in_raw_mode(self, pdf_with_images: Path) -> None:
        options = ConversionOptions(clean=False)
        result = convert_pdf(pdf_with_images, options)
        assert "<!-- [image:" not in result.markdown

    def test_toc_cleanup_in_clean_mode(self, pdf_with_toc: Path) -> None:
        options = ConversionOptions(clean=True)
        result = convert_pdf(pdf_with_toc, options)
        assert "- Introduction (p. 5)" in result.markdown
        assert ".........." not in result.markdown
