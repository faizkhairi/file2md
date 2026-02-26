"""FastAPI web server for drag-and-drop file conversion."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from . import __version__
from .convert import convert_file
from .utils import (
    MAX_UPLOAD_SIZE,
    ConversionOptions,
    ExitCode,
    sanitize_filename,
    validate_docx_content,
    validate_pdf_content,
)

app = FastAPI(title="file2md", version=__version__)

_templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    """Serve the drag-and-drop upload page."""
    return templates.TemplateResponse(request, "index.html", {"version": __version__})


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/convert")
async def convert(
    file: UploadFile = File(...),  # noqa: B008
    clean: bool = Form(default=False),
    frontmatter: bool = Form(default=False),
    page_labels: bool = Form(default=False),
    extract_tables: bool = Form(default=False),
) -> Response:
    """Convert an uploaded PDF or DOCX file to Markdown."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".docx"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {suffix}. Only .pdf and .docx are accepted.",
        )

    # Read file content
    content = await file.read()

    # Validate size
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB.",
        )

    # Write to temp file for conversion
    safe_name = sanitize_filename(file.filename)
    tmp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        # Content sniffing — verify file is actually what the extension claims
        if suffix == ".pdf" and not validate_pdf_content(tmp_path):
            raise HTTPException(
                status_code=415,
                detail="File does not appear to be a valid PDF.",
            )
        if suffix == ".docx" and not validate_docx_content(tmp_path):
            raise HTTPException(
                status_code=415,
                detail="File does not appear to be a valid DOCX (Word document).",
            )

        options = ConversionOptions(
            clean=clean,
            frontmatter=frontmatter,
            page_labels=page_labels,
            extract_tables=extract_tables,
        )
        result = convert_file(tmp_path, options)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    if result.exit_code == ExitCode.SCANNED_PDF:
        raise HTTPException(
            status_code=422,
            detail="This PDF appears to be scanned/image-only. OCR is not currently supported.",
        )

    if result.exit_code != ExitCode.SUCCESS:
        raise HTTPException(
            status_code=500,
            detail=f"Conversion failed: {'; '.join(result.warnings)}",
        )

    # Build response with warnings header if any
    output_name = Path(safe_name).stem + ".md"
    headers: dict[str, str] = {
        "Content-Disposition": f'attachment; filename="{output_name}"',
    }
    if result.warnings:
        headers["X-Conversion-Warnings"] = "; ".join(result.warnings)

    return Response(
        content=result.markdown.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers=headers,
    )
