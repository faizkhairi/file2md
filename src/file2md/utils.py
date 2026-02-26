"""Shared data classes, exit codes, and utility functions."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path


class ExitCode(IntEnum):
    """CLI exit codes."""

    SUCCESS = 0
    UNSUPPORTED_FILE = 2
    EXTRACTION_FAILED = 3
    SCANNED_PDF = 4


@dataclass
class ConversionOptions:
    """Options controlling conversion behavior."""

    clean: bool = False
    frontmatter: bool = False
    page_labels: bool = False
    extract_tables: bool = False
    max_chars: int | None = None


@dataclass
class ConversionResult:
    """Result of a file conversion."""

    markdown: str
    source_file: str
    page_count: int | None = None
    warnings: list[str] = field(default_factory=list)
    exit_code: ExitCode = ExitCode.SUCCESS


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

# Max upload size in bytes (50 MB)
MAX_UPLOAD_SIZE = 50 * 1024 * 1024


def detect_file_type(path: Path) -> str:
    """Return 'pdf' or 'docx' based on file extension.

    Raises ValueError for unsupported file types.
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "docx"
    raise ValueError(f"Unsupported file type: {suffix}. Only .pdf and .docx are supported.")


def validate_pdf_content(path: Path) -> bool:
    """Verify file starts with PDF magic bytes (%PDF-)."""
    try:
        with open(path, "rb") as f:
            header = f.read(5)
        return header == b"%PDF-"
    except OSError:
        return False


def validate_docx_content(path: Path) -> bool:
    """Verify file is a valid DOCX (ZIP with word/document.xml)."""
    try:
        if not zipfile.is_zipfile(path):
            return False
        with zipfile.ZipFile(path, "r") as zf:
            return "word/document.xml" in zf.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe filesystem use."""
    # Strip path components
    name = Path(filename).name
    # Remove unsafe characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    # Limit length
    if len(name) > 200:
        stem = Path(name).stem[:190]
        suffix = Path(name).suffix
        name = stem + suffix
    return name


def build_metadata(path: Path, options: ConversionOptions, timestamp: str | None = None) -> str:
    """Build metadata comment or YAML frontmatter.

    Args:
        path: Source file path.
        options: Conversion options.
        timestamp: Optional ISO 8601 timestamp override (for deterministic testing).
    """
    if timestamp is None:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    if options.frontmatter:
        return (
            "---\n"
            f"source: {path.name}\n"
            f"converted: {timestamp}\n"
            f"converter: file2md v0.1.0\n"
            "---"
        )

    return f"<!-- source: {path.name} | converted: {timestamp} | converter: file2md v0.1.0 -->"
