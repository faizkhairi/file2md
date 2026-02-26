"""PDF to Markdown conversion using PyMuPDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pymupdf

from .normalize import (
    apply_normalization,
    clean_toc_lines,
    dedup_table_columns,
    fix_hyphenation,
    reflow_paragraphs,
    remove_false_blanks,
    remove_headers_footers,
)
from .utils import ConversionOptions, ConversionResult, ExitCode, build_metadata


def is_scanned_page(page: Any) -> bool:
    """Detect if a page is a scanned image with no extractable text."""
    text = page.get_text("text").strip()
    if text:
        return False
    images = page.get_images(full=True)
    if not images:
        return False
    # Check if any image covers most of the page
    page_area = abs(page.rect)
    for img in images:
        try:
            bbox = page.get_image_bbox(img)
            if bbox.is_empty:
                continue
            coverage = abs(bbox) / page_area if page_area > 0 else 0
            if coverage >= 0.5:
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def _strip_leading_spaces(text: str) -> str:
    """Strip leading whitespace from each line.

    PyMuPDF preserves X-coordinate positioning as leading spaces,
    which produces indented lines in the output. Strip them.
    """
    return "\n".join(line.lstrip() for line in text.split("\n"))


def _detect_images(page: Any, page_num: int) -> str:
    """Detect significant images on a page and return placeholder comments.

    Uses the same get_images() + get_image_bbox() pattern as is_scanned_page().
    Skips dead entries (empty bboxes). Only includes images covering >10% of
    the page area.

    Returns:
        Placeholder comments joined with newlines, or empty string if none.
    """
    images = page.get_images(full=True)
    if not images:
        return ""

    page_area = abs(page.rect)
    if page_area <= 0:
        return ""

    placeholders: list[str] = []
    for img in images:
        try:
            bbox = page.get_image_bbox(img)
            if bbox.is_empty:
                continue
            coverage = abs(bbox) / page_area
            if coverage >= 0.1:
                placeholders.append(f"<!-- [image: figure on page {page_num}] -->")
        except Exception:  # noqa: BLE001
            continue

    return "\n".join(placeholders)


def _extract_tables(page: Any) -> str:
    """Extract tables from a page as GFM markdown.

    Returns:
        Table markdown or empty string if no tables found.
    """
    try:
        tables = page.find_tables()
        parts: list[str] = []
        for table in tables:
            md_table = table.to_markdown()
            if md_table.strip():
                parts.append(md_table)
        return "\n\n".join(parts)
    except Exception:  # noqa: BLE001
        return ""  # Table extraction is best-effort


def convert_pdf(path: Path, options: ConversionOptions) -> ConversionResult:
    """Convert a PDF file to Markdown.

    Pipeline (v0.2.0):
    1. Per-page: extract raw text, tables, and image placeholders as separate streams
    2. Strip leading spaces from raw text
    3. Dedup table columns (merged cell fix)
    4. Header/footer removal on raw text only (before tables injected)
    5. Recombine per page, then per-page: hyphenation → TOC cleanup →
       false blank removal → reflow
    6. Join pages with separators, apply final normalization
    """
    try:
        doc: Any = pymupdf.open(str(path))  # type: ignore[no-untyped-call]
    except Exception as e:  # noqa: BLE001
        return ConversionResult(
            markdown="",
            source_file=path.name,
            warnings=[f"Failed to open PDF: {e}"],
            exit_code=ExitCode.EXTRACTION_FAILED,
        )

    raw_texts: list[str] = []
    table_texts: list[str] = []
    image_texts: list[str] = []
    warnings: list[str] = []
    scanned_count = 0
    total_pages = len(doc)

    # Phase 1: Per-page extraction into separate streams
    for i, page in enumerate(doc, start=1):
        if is_scanned_page(page):
            scanned_count += 1
            raw_texts.append("")
            table_texts.append("")
            image_texts.append("")
            continue

        # Extract raw text and strip leading spaces
        raw_text = page.get_text("text", sort=True)
        if options.clean:
            raw_text = _strip_leading_spaces(raw_text)

        # Detect significant images (clean mode only)
        image_placeholders = _detect_images(page, i) if options.clean else ""

        # Extract tables and dedup merged cells
        table_md = _extract_tables(page) if options.extract_tables else ""
        if table_md and options.clean:
            table_md = dedup_table_columns(table_md)

        raw_texts.append(raw_text)
        table_texts.append(table_md)
        image_texts.append(image_placeholders)

    doc.close()

    # If ALL pages are scanned, return error
    if total_pages > 0 and scanned_count == total_pages:
        return ConversionResult(
            markdown="",
            source_file=path.name,
            page_count=total_pages,
            warnings=["All pages appear to be scanned images. OCR is not supported."],
            exit_code=ExitCode.SCANNED_PDF,
        )

    if scanned_count > 0:
        warnings.append(f"{scanned_count} scanned page(s) skipped (no extractable text)")

    # Phase 2: Header/footer removal on RAW TEXT and TABLE TEXT separately
    removed_patterns: list[str] = []
    if options.clean:
        non_empty = [p for p in raw_texts if p.strip()]
        if len(non_empty) >= 3:
            raw_texts, removed_patterns = remove_headers_footers(raw_texts)
        # Also check table texts for repeating header/footer tables
        non_empty_tables = [p for p in table_texts if p.strip()]
        if len(non_empty_tables) >= 3:
            table_texts, table_removed = remove_headers_footers(table_texts)
            removed_patterns.extend(table_removed)

    # Phase 3: Recombine and apply per-page cleanup
    sections: list[str] = []
    for i, (raw, tables, images) in enumerate(
        zip(raw_texts, table_texts, image_texts, strict=True), start=1
    ):
        parts = [p for p in [images, tables, raw] if p.strip()]
        if not parts:
            continue

        page_text = "\n\n".join(parts)

        if options.clean:
            page_text = fix_hyphenation(page_text)
            page_text = clean_toc_lines(page_text)
            page_text = remove_false_blanks(page_text)
            page_text = reflow_paragraphs(page_text)

        if options.page_labels:
            sections.append(f"## Page {i}\n\n{page_text.strip()}")
        else:
            sections.append(page_text.strip())

    # Join with page separators
    markdown = "\n\n---\n\n".join(sections)

    # Apply general normalization
    if options.clean:
        markdown = apply_normalization(markdown)

    # Add removed patterns note
    if removed_patterns:
        note = "<!-- Removed repeating headers/footers: " + ", ".join(removed_patterns) + " -->\n\n"
        markdown = note + markdown

    # Add metadata header
    metadata = build_metadata(path, options)
    markdown = metadata + "\n\n" + markdown

    # Truncation
    if options.max_chars and len(markdown) > options.max_chars:
        markdown = (
            markdown[: options.max_chars]
            + f"\n\n[... truncated at {options.max_chars} characters]"
        )

    return ConversionResult(
        markdown=markdown,
        source_file=path.name,
        page_count=total_pages,
        warnings=warnings,
        exit_code=ExitCode.SUCCESS,
    )
