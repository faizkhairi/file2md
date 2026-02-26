"""Tests for the normalize module — text cleanup and quality functions."""

from file2md.normalize import (
    apply_normalization,
    clean_toc_lines,
    collapse_blank_lines,
    dedup_table_columns,
    fix_hyphenation,
    normalize_whitespace,
    reflow_paragraphs,
    remove_false_blanks,
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

    def test_dynamic_n_check_detects_4_line_headers(self) -> None:
        """Headers in lines 4-6 should be detected with dynamic n_check."""
        pages = []
        for i in range(1, 6):
            pages.append(
                f"Title Line\nSubtitle\nDoc ID: 123\nConfidential\n"
                f"Line five header\nContent for page {i}"
            )
        cleaned, removed = remove_headers_footers(pages, threshold=0.6)
        # "Confidential" is on line 4, should be detected with n_check > 3
        assert any("Confidential" in p for p in removed)

    def test_n_check_clamped_for_short_pages(self) -> None:
        """Short pages (< 15 lines) should use n_check=3."""
        pages = [
            "Header\nContent 1\nFooter",
            "Header\nContent 2\nFooter",
            "Header\nContent 3\nFooter",
        ]
        cleaned, removed = remove_headers_footers(pages, threshold=0.6)
        # Header and Footer should be detected (within n_check=3)
        assert len(removed) >= 1


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


class TestRemoveFalseBlanks:
    def test_removes_single_blank_between_content(self) -> None:
        text = "This line continues\n\non the next line"
        result = remove_false_blanks(text)
        assert result == "This line continues\non the next line"

    def test_preserves_blank_after_sentence_end(self) -> None:
        text = "End of sentence.\n\nNew paragraph starts"
        result = remove_false_blanks(text)
        assert "\n\n" in result

    def test_preserves_blank_before_heading(self) -> None:
        text = "Some content\n\n# New Section"
        result = remove_false_blanks(text)
        assert "\n\n" in result

    def test_preserves_blank_after_list_item(self) -> None:
        text = "- List item\n\nFollowing text"
        result = remove_false_blanks(text)
        assert "\n\n" in result

    def test_preserves_blank_before_html_comment(self) -> None:
        text = "Some text\n\n<!-- [image: figure on page 1] -->"
        result = remove_false_blanks(text)
        assert "\n\n" in result

    def test_preserves_multiple_consecutive_blanks(self) -> None:
        text = "First paragraph.\n\n\nSecond paragraph."
        result = remove_false_blanks(text)
        assert "\n\n\n" in result

    def test_short_text_unchanged(self) -> None:
        text = "Just one line"
        assert remove_false_blanks(text) == text

    def test_removes_multiple_false_blanks(self) -> None:
        text = "Line A\n\nLine B\n\nLine C"
        result = remove_false_blanks(text)
        # Both blanks should be removed since A→B and B→C are non-terminal
        assert result == "Line A\nLine B\nLine C"


class TestDedupTableColumns:
    def test_dedup_adjacent_identical_cells(self) -> None:
        text = "| val | val | other |"
        result = dedup_table_columns(text)
        assert result == "| val | | other |"

    def test_preserves_unique_cells(self) -> None:
        text = "| Alice | 30 | KL |"
        assert dedup_table_columns(text) == text

    def test_preserves_separator_row(self) -> None:
        text = "| --- | --- | --- |"
        assert dedup_table_columns(text) == text

    def test_dedup_with_aligned_separator(self) -> None:
        text = "| Name | Name | Value |\n| --- | --- | --- |\n| foo | foo | bar |"
        result = dedup_table_columns(text)
        assert "| Name | | Value |" in result
        assert "| foo | | bar |" in result
        assert "| --- | --- | --- |" in result

    def test_no_table_passthrough(self) -> None:
        text = "No tables here, just regular text."
        assert dedup_table_columns(text) == text

    def test_non_adjacent_duplicates_preserved(self) -> None:
        text = "| val | other | val |"
        assert dedup_table_columns(text) == text


class TestCleanTocLines:
    def test_basic_toc_line(self) -> None:
        text = "Introduction .............. 5"
        result = clean_toc_lines(text)
        assert result == "- Introduction (p. 5)"

    def test_numbered_toc_line(self) -> None:
        text = "3.1 API Flow ......... 12"
        result = clean_toc_lines(text)
        assert result == "- 3.1 API Flow (p. 12)"

    def test_preserves_normal_text(self) -> None:
        text = "This is a normal paragraph with no dots."
        assert clean_toc_lines(text) == text

    def test_preserves_short_dots(self) -> None:
        """Lines with fewer than 4 dots should not be treated as TOC."""
        text = "Something... 3"
        assert clean_toc_lines(text) == text

    def test_multiple_toc_lines(self) -> None:
        text = "Introduction .............. 5\n3.1 API Flow ......... 12\nNormal text."
        result = clean_toc_lines(text)
        assert "- Introduction (p. 5)" in result
        assert "- 3.1 API Flow (p. 12)" in result
        assert "Normal text." in result


class TestApplyNormalization:
    def test_combined_normalization(self) -> None:
        text = "Hello    world\r\n\r\n\r\n\r\nNext"
        result = apply_normalization(text)
        assert "Hello world" in result
        assert "\r" not in result
        assert result.endswith("\n")
