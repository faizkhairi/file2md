"""Main conversion dispatcher — detects file type and calls the appropriate converter."""

from __future__ import annotations

from pathlib import Path

from .docx_converter import convert_docx
from .pdf import convert_pdf
from .utils import ConversionOptions, ConversionResult, ExitCode, detect_file_type


def convert_file(
    path: Path | str,
    options: ConversionOptions | None = None,
) -> ConversionResult:
    """Convert a PDF or DOCX file to Markdown.

    This is the main entry point for programmatic usage.

    Args:
        path: Path to the input file.
        options: Conversion options (defaults applied if None).

    Returns:
        ConversionResult with markdown content and metadata.
    """
    if options is None:
        options = ConversionOptions()

    path = Path(path)

    if not path.exists():
        return ConversionResult(
            markdown="",
            source_file=str(path),
            warnings=[f"File not found: {path}"],
            exit_code=ExitCode.EXTRACTION_FAILED,
        )

    try:
        file_type = detect_file_type(path)
    except ValueError as e:
        return ConversionResult(
            markdown="",
            source_file=str(path),
            warnings=[str(e)],
            exit_code=ExitCode.UNSUPPORTED_FILE,
        )

    if file_type == "pdf":
        return convert_pdf(path, options)
    else:  # docx
        return convert_docx(path, options)
