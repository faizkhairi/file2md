"""Shared test fixtures — programmatic PDF/DOCX generation."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from docx import Document


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Generate a simple multi-page test PDF."""
    doc = pymupdf.open()

    # Page 1
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Company Report Header", fontsize=12)
    page1.insert_text((72, 110), "This is the first paragraph of the document.")
    page1.insert_text((72, 130), "It continues on the next line with more text.")
    page1.insert_text((72, 170), "Another paragraph follows after a gap.")
    page1.insert_text((72, 750), "Page 1 of 3")

    # Page 2
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Company Report Header", fontsize=12)
    page2.insert_text((72, 110), "Second page content begins here.")
    page2.insert_text((72, 130), "This page has a hyphen-")
    page2.insert_text((72, 150), "ated word split across lines.")
    page2.insert_text((72, 750), "Page 2 of 3")

    # Page 3
    page3 = doc.new_page()
    page3.insert_text((72, 72), "Company Report Header", fontsize=12)
    page3.insert_text((72, 110), "Final page of the document.")
    page3.insert_text((72, 750), "Page 3 of 3")

    path = tmp_path / "sample.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def single_page_pdf(tmp_path: Path) -> Path:
    """Generate a single-page PDF."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello World", fontsize=14)
    page.insert_text((72, 110), "This is a simple single-page PDF.")
    path = tmp_path / "single.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def scanned_pdf(tmp_path: Path) -> Path:
    """Generate a PDF with only an image (simulating scanned document)."""
    doc = pymupdf.open()
    page = doc.new_page()
    # Create a large image-like pixmap covering most of the page
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 200, 200), 0)
    pix.set_rect(pix.irect, (200, 200, 200))
    page.insert_image(page.rect, pixmap=pix)
    path = tmp_path / "scanned.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    """Generate a test DOCX with headings, lists, and a table."""
    doc = Document()

    doc.add_heading("Test Document", level=1)
    doc.add_paragraph("This is the first paragraph with some content.")

    doc.add_heading("Section Two", level=2)
    doc.add_paragraph("Another paragraph here.")

    # Bullet list
    doc.add_paragraph("First bullet item", style="List Bullet")
    doc.add_paragraph("Second bullet item", style="List Bullet")

    # Numbered list
    doc.add_paragraph("First numbered item", style="List Number")
    doc.add_paragraph("Second numbered item", style="List Number")

    doc.add_heading("Data Table", level=2)

    # Table
    table = doc.add_table(rows=3, cols=3)
    headers = ["Name", "Age", "City"]
    for i, header in enumerate(headers):
        table.rows[0].cells[i].text = header
    data = [["Alice", "30", "KL"], ["Bob", "25", "Penang"]]
    for row_idx, row_data in enumerate(data, start=1):
        for col_idx, value in enumerate(row_data):
            table.rows[row_idx].cells[col_idx].text = value

    doc.add_heading("Conclusion", level=2)
    doc.add_paragraph("This concludes the test document.")

    path = tmp_path / "sample.docx"
    doc.save(str(path))
    return path


@pytest.fixture
def formatted_docx(tmp_path: Path) -> Path:
    """Generate a DOCX with bold, italic, and mixed formatting."""
    doc = Document()
    doc.add_heading("Formatted Document", level=1)

    para = doc.add_paragraph()
    para.add_run("Normal text, ")
    run_bold = para.add_run("bold text")
    run_bold.bold = True
    para.add_run(", and ")
    run_italic = para.add_run("italic text")
    run_italic.italic = True
    para.add_run(".")

    path = tmp_path / "formatted.docx"
    doc.save(str(path))
    return path


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """Generate a PDF with no text content."""
    doc = pymupdf.open()
    doc.new_page()
    path = tmp_path / "empty.pdf"
    doc.save(str(path))
    doc.close()
    return path
