"""Tests for the normalize module — text cleanup and quality functions."""

from file2md.normalize import (
    apply_normalization,
    collapse_blank_lines,
    fix_hyphenation,
    normalize_whitespace,
    reflow_paragraphs,
    remove_headers_footers,
)


class TestFixHyphenation:
    def test_basic_hyphenation(self) -> None:
        text = "This is a para-\ngraph that continues."
        assert fix_hyphenation(text) == "This is a paragraph that continues."

    def test_no_hyphenation(self) -> None:
        text = "This is a normal line.\nAnother line."
        assert fix_hyphenation(text) == text

    def test_hyphen_before_uppercase(self) -> None:
        """Uppercase continuation should NOT be merged (likely a real hyphen)."""
        text = "Self-\nAwareness is important."
        assert fix_hyphenation(text) == text

    def test_multiple_hyphenations(self) -> None:
        text = "docu-\nment and para-\ngraph"
        result = fix_hyphenation(text)
        assert "document" in result
        assert "paragraph" in result

    def test_hyphen_with_indentation(self) -> None:
        text = "para-\n  graph"
        assert fix_hyphenation(text) == "paragraph"


class TestReflowParagraphs:
    def test_joins_wrapped_lines(self) -> None:
        text = "This is a line that\ncontinues on the next"
        result = reflow_paragraphs(text)
        assert "This is a line that continues on the next" in result

    def test_preserves_headings(self) -> None:
        text = "# Heading\nSome text"
        result = reflow_paragraphs(text)
        assert result.startswith("# Heading")

    def test_preserves_list_items(self) -> None:
        text = "- First item\n- Second item"
        result = reflow_paragraphs(text)
        assert "- First item" in result
        assert "- Second item" in result

    def test_preserves_blank_line_separation(self) -> None:
        text = "First paragraph.\n\nSecond paragraph."
        result = reflow_paragraphs(text)
        assert "First paragraph." in result
        assert "Second paragraph." in result
        assert "\n\n" in result or "\n" in result

    def test_does_not_join_after_period(self) -> None:
        text = "End of sentence.\nNew sentence starts here"
        result = reflow_paragraphs(text)
        # Should not join because previous line ends with period
        assert "End of sentence." in result

    def test_preserves_table_rows(self) -> None:
        text = "| col1 | col2 |\n| --- | --- |"
        result = reflow_paragraphs(text)
        assert "| col1 | col2 |" in result


class TestRemoveHeadersFooters:
    def test_removes_repeating_header(self) -> None:
        pages = [
            "Company Report\nContent on page 1",
            "Company Report\nContent on page 2",
            "Company Report\nContent on page 3",
            "Company Report\nContent on page 4",
        ]
        cleaned, removed = remove_headers_footers(pages, threshold=0.6)
        assert any("Company Report" in p for p in removed)
        for page in cleaned:
            assert "Company Report" not in page

    def test_removes_page_numbers(self) -> None:
        pages = [
            "Content\nPage 1",
            "Content\nPage 2",
            "Content\nPage 3",
        ]
        cleaned, removed = remove_headers_footers(pages, threshold=0.6)
        # Page numbers (with digits normalized) should be detected
        assert len(removed) > 0

    def test_too_few_pages_skips(self) -> None:
        pages = ["Content page 1", "Content page 2"]
        cleaned, removed = remove_headers_footers(pages)
        assert cleaned == pages
        assert removed == []

    def test_non_repeating_content_preserved(self) -> None:
        pages = [
            "Unique header alpha\nFirst page body text",
            "Unique header bravo\nSecond page body text",
            "Unique header charlie\nThird page body text",
        ]
        cleaned, removed = remove_headers_footers(pages, threshold=0.6)
        assert removed == []


class TestNormalizeWhitespace:
    def test_collapses_spaces(self) -> None:
        text = "Hello    world   test"
        assert normalize_whitespace(text) == "Hello world test"

    def test_normalizes_line_endings(self) -> None:
        text = "line1\r\nline2\rline3"
        result = normalize_whitespace(text)
        assert "\r" not in result
        assert result == "line1\nline2\nline3"

    def test_preserves_table_formatting(self) -> None:
        text = "| col1  |  col2  |"
        assert normalize_whitespace(text) == text


class TestCollapseBlankLines:
    def test_collapses_multiple_blanks(self) -> None:
        text = "para1\n\n\n\n\npara2"
        result = collapse_blank_lines(text)
        assert result.count("\n") <= 3

    def test_preserves_double_blanks(self) -> None:
        text = "para1\n\npara2"
        assert collapse_blank_lines(text) == text


class TestApplyNormalization:
    def test_combined_normalization(self) -> None:
        text = "Hello    world\r\n\r\n\r\n\r\nNext"
        result = apply_normalization(text)
        assert "Hello world" in result
        assert "\r" not in result
        assert result.endswith("\n")
