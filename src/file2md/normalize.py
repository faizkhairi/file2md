"""Markdown normalization and cleanup functions.

This module handles the 'grep-friendly' quality of the output:
- Paragraph reflow (undo PDF hard wraps)
- Hyphenation fix (merge split words)
- Header/footer removal (heuristic)
- Whitespace normalization
"""

from __future__ import annotations

import re


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
        stripped.startswith(("#", "- ", "* ", "> ", "| ", "---", "```", "1. ", "2. ", "3. "))
        or re.match(r"^\d+\.\s", stripped)
    )


def remove_headers_footers(pages: list[str], threshold: float = 0.6) -> tuple[list[str], list[str]]:
    """Remove repeating headers/footers from page texts.

    Heuristic: lines appearing on >threshold fraction of pages near top/bottom
    (first/last 3 lines of each page) are likely headers/footers.

    Returns:
        Tuple of (cleaned pages, list of removed patterns).
    """
    if len(pages) < 3:
        return pages, []

    n_check = 3  # check first/last N lines of each page
    top_counts: dict[str, int] = {}
    bottom_counts: dict[str, int] = {}

    for page_text in pages:
        lines = [line.strip() for line in page_text.split("\n") if line.strip()]
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
