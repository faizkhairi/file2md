"""PDF to Markdown conversion using PyMuPDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pymupdf

from .normalize import (
    apply_normalization,
    fix_hyphenation,
    reflow_paragraphs,
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


def convert_pdf(path: Path, options: ConversionOptions) -> ConversionResult:
    """Convert a PDF file to Markdown.

    Args:
        path: Path to the PDF file.
        options: Conversion options.

    Returns:
        ConversionResult with the markdown content.
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

    pages_text: list[str] = []
    warnings: list[str] = []
    scanned_count = 0
    total_pages = len(doc)

    for page in doc:
        if is_scanned_page(page):
            scanned_count += 1
            pages_text.append("")
            continue

        parts: list[str] = []

        # Extract tables if requested
        if options.extract_tables:
            try:
                tables = page.find_tables()
                for table in tables:
                    md_table = table.to_markdown()
                    if md_table.strip():
                        parts.append(md_table)
            except Exception:  # noqa: BLE001
                pass  # Table extraction is best-effort

        # Extract text in reading order
        text = page.get_text("text", sort=True)
        if text.strip():
            parts.append(text)

        pages_text.append("\n\n".join(parts))

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

    # Apply header/footer removal
    removed_patterns: list[str] = []
    if options.clean:
        non_empty = [p for p in pages_text if p.strip()]
        if len(non_empty) >= 3:
            pages_text, removed_patterns = remove_headers_footers(pages_text)

    # Build final markdown with page separators
    sections: list[str] = []
    for i, page_text in enumerate(pages_text, start=1):
        if not page_text.strip():
            continue

        processed = page_text
        if options.clean:
            processed = fix_hyphenation(processed)
            processed = reflow_paragraphs(processed)

        if options.page_labels:
            sections.append(f"## Page {i}\n\n{processed.strip()}")
        else:
            sections.append(processed.strip())

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
