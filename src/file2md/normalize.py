"""Markdown normalization and cleanup functions.

This module handles the 'grep-friendly' quality of the output:
- Paragraph reflow (undo PDF hard wraps)
- Hyphenation fix (merge split words)
- Header/footer removal (heuristic)
- False blank line removal
- Table column deduplication
- TOC dot leader cleanup
- Whitespace normalization
"""

from __future__ import annotations

import re

_TOC_RE = re.compile(r"^(.+?)\s*\.{4,}\s*(\d+)\s*$", re.MULTILINE)
_TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")


def fix_hyphenation(text: str) -> str:
    """Merge words split across lines by hyphenation.

    Matches: word fragment + hyphen + newline + optional whitespace + lowercase continuation.
    Example: 'para-\\ngraph' -> 'paragraph'
    """
    return re.sub(r"(\w)-\n\s*([a-z])", r"\1\2", text)


def reflow_paragraphs(text: str) -> str:
    """Undo PDF hard wraps by joining lines that are part of the same paragraph.

    Preserves headings, list items, table rows, block quotes, and separators.
    Only joins lines where the previous line doesn't end with a sentence terminator.
    """
    lines = text.split("\n")
    result: list[str] = []

    for i, line in enumerate(lines):
        stripped = line.rstrip()

        # Blank line — preserve as paragraph boundary
        if not stripped:
            result.append("")
            continue

        # Don't join block-level elements
        if _is_block_element(stripped):
            result.append(stripped)
            continue

        # Check if next line starts a new block or is blank
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if not next_line or _is_block_element(next_line):
                result.append(stripped)
                continue

        # Join with previous line if it didn't end with a sentence terminator
        if (
            result
            and result[-1]
            and not result[-1].endswith((".", ":", "!", "?", '"', "'"))
            and not _is_block_element(result[-1])
        ):
            result[-1] = result[-1] + " " + stripped
        else:
            result.append(stripped)

    return "\n".join(result)


def _is_block_element(line: str) -> bool:
    """Check if a line is a markdown block element that shouldn't be joined."""
    stripped = line.lstrip()
    return bool(
        stripped.startswith(
            ("#", "- ", "* ", "> ", "| ", "---", "```", "1. ", "2. ", "3. ", "<!--")
        )
        or re.match(r"^\d+\.\s", stripped)
    )


def remove_false_blanks(text: str) -> str:
    """Remove single blank lines between lines that are likely part of the same paragraph.

    PyMuPDF often inserts blank lines between visual text lines that belong to
    the same paragraph due to vertical spacing in the PDF layout. This function
    removes those false paragraph breaks so that reflow can join them properly.

    Only removes a blank line when:
    - Line before is non-empty and not a block element
    - Line before does not end with a sentence terminator
    - Line after is non-empty and not a block element
    """
    lines = text.split("\n")
    if len(lines) < 3:
        return text

    result: list[str] = []
    i = 0
    while i < len(lines):
        if (
            i + 2 < len(lines)
            and lines[i].strip()
            and not lines[i + 1].strip()
            and lines[i + 2].strip()
            and not _is_block_element(lines[i].strip())
            and not _is_block_element(lines[i + 2].strip())
            and not lines[i].strip().endswith((".", ":", "!", "?", '"', "'"))
        ):
            # Skip the false blank line between A and C
            result.append(lines[i])
            i += 2  # jump to C (the blank at i+1 is dropped)
        else:
            result.append(lines[i])
            i += 1
    return "\n".join(result)


def dedup_table_columns(text: str) -> str:
    """Remove duplicate content in adjacent table cells caused by merged cells.

    When PyMuPDF extracts tables with merged cells, the same content appears in
    multiple adjacent columns. This function blanks duplicate adjacent cells,
    keeping only the first occurrence.
    """
    if "|" not in text:
        return text

    lines = text.split("\n")
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Only process table data rows (not separator rows like | --- | --- |)
        if stripped.startswith("|") and not _TABLE_SEP_RE.match(stripped):
            cells = stripped.split("|")
            # cells[0] and cells[-1] are empty strings from leading/trailing |
            if len(cells) >= 3:
                deduped = [cells[0]]
                for j in range(1, len(cells) - 1):
                    if (
                        j > 1
                        and cells[j].strip()
                        and cells[j].strip() == cells[j - 1].strip()
                    ):
                        deduped.append(" ")
                    else:
                        deduped.append(cells[j])
                deduped.append(cells[-1])
                result.append("|".join(deduped))
            else:
                result.append(line)
        else:
            result.append(line)
    return "\n".join(result)


def clean_toc_lines(text: str) -> str:
    """Clean up Table of Contents dot leaders.

    Converts lines like 'Introduction .............. 5' into
    '- Introduction (p. 5)' — a clean markdown list.
    """
    return _TOC_RE.sub(r"- \1 (p. \2)", text)


def remove_headers_footers(pages: list[str], threshold: float = 0.6) -> tuple[list[str], list[str]]:
    """Remove repeating headers/footers from page texts.

    Heuristic: lines appearing on >threshold fraction of pages near top/bottom
    are likely headers/footers. Uses a dynamic scan window of 3–6 lines based
    on 20% of each page's line count.

    Returns:
        Tuple of (cleaned pages, list of removed patterns).
    """
    if len(pages) < 3:
        return pages, []

    top_counts: dict[str, int] = {}
    bottom_counts: dict[str, int] = {}

    for page_text in pages:
        lines = [line.strip() for line in page_text.split("\n") if line.strip()]
        n_check = min(6, max(3, len(lines) // 5))
        for line in lines[:n_check]:
            normalized = _normalize_for_comparison(line)
            if normalized:
                top_counts[normalized] = top_counts.get(normalized, 0) + 1
        for line in lines[-n_check:]:
            normalized = _normalize_for_comparison(line)
            if normalized:
                bottom_counts[normalized] = bottom_counts.get(normalized, 0) + 1

    min_count = max(2, int(len(pages) * threshold))
    header_patterns = {k for k, v in top_counts.items() if v >= min_count}
    footer_patterns = {k for k, v in bottom_counts.items() if v >= min_count}
    all_patterns = header_patterns | footer_patterns

    if not all_patterns:
        return pages, []

    cleaned: list[str] = []
    for page_text in pages:
        lines = page_text.split("\n")
        filtered = []
        for line in lines:
            normalized = _normalize_for_comparison(line.strip())
            if normalized and normalized in all_patterns:
                continue
            filtered.append(line)
        cleaned.append("\n".join(filtered))

    return cleaned, sorted(all_patterns)


def _normalize_for_comparison(line: str) -> str:
    """Normalize a line for header/footer comparison.

    Replaces digits with 'NUM' so 'Page 1' and 'Page 2' match.
    """
    if not line:
        return ""
    return re.sub(r"\d+", "NUM", line).strip()


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace: collapse multiple spaces, standardize newlines."""
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple spaces (but not in lines that look like tables or code)
    lines = text.split("\n")
    result: list[str] = []
    for line in lines:
        if line.strip().startswith("|") or line.strip().startswith("```"):
            result.append(line)
        else:
            result.append(re.sub(r"[ \t]+", " ", line))
    return "\n".join(result)


def collapse_blank_lines(text: str) -> str:
    """Collapse more than 2 consecutive blank lines into 2."""
    return re.sub(r"\n{4,}", "\n\n\n", text)


def apply_normalization(text: str) -> str:
    """Apply all normalization steps to markdown text."""
    text = normalize_whitespace(text)
    text = collapse_blank_lines(text)
    return text.strip() + "\n"
