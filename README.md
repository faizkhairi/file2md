# file2md

Convert PDF and DOCX files to clean, grep-friendly Markdown optimized for AI tools and IDE workflows.

[![CI](https://github.com/faizkhairi/file2md/actions/workflows/ci.yml/badge.svg)](https://github.com/faizkhairi/file2md/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**[Try the Web UI](https://file2md.onrender.com)** | **[PyPI](https://pypi.org/project/file2md/)**

## Features

- **PDF conversion** — text extraction with PyMuPDF, page separators, scanned PDF detection
- **DOCX conversion** — headings, lists, tables, bold/italic preserved as Markdown
- **Grep-friendly output** — paragraph reflow, hyphenation fix, whitespace normalization
- **Drag-and-drop web UI** — upload and convert files in your browser
- **Full CLI** — single file, batch, and web server modes
- **Table extraction** — PDF tables converted to GitHub-flavored Markdown
- **Header/footer removal** — heuristic detection of repeating headers/footers
- **Metadata headers** — source filename and conversion timestamp in output
- **YAML frontmatter** — optional structured metadata for downstream tools

## Installation

```bash
# CLI only (lightweight)
pip install file2md

# With web UI
pip install file2md[web]

# Development (all dependencies)
pip install file2md[all]
```

## Quick Start

### Web UI

```bash
file2md serve
# Open http://127.0.0.1:8000 and drag your files
```

### CLI — Single File

```bash
# Basic conversion
file2md convert document.pdf -o document.md

# With all enhancements
file2md convert report.pdf -o report.md --clean --frontmatter --page-labels --extract-tables
```

### CLI — Batch

```bash
# Convert all PDFs and DOCXs in a directory
file2md batch ./documents --out-dir ./markdown --recursive
```

## CLI Reference

### `file2md convert`

Convert a single PDF or DOCX file to Markdown.

| Flag | Description |
|------|-------------|
| `-o / --output` | Output file path (defaults to input name with `.md`) |
| `--clean` | Normalize whitespace, reflow paragraphs, fix hyphenation |
| `--frontmatter` | Add YAML frontmatter (source, timestamp, converter) |
| `--page-labels` | Add `## Page N` headings (PDF only) |
| `--extract-tables` | Detect and convert tables to GFM (PDF) |
| `--max-chars N` | Truncate output at N characters |
| `--overwrite` | Overwrite existing output file |
| `--quiet` | Suppress warnings |
| `--verbose` | Show detailed progress |
| `--json` | Machine-readable JSON output |

### `file2md batch`

Batch convert all PDF/DOCX files in a directory.

| Flag | Description |
|------|-------------|
| `--out-dir` | Output directory (required) |
| `--recursive` | Process subdirectories |
| All flags from `convert` | Same options available |

### `file2md serve`

Start the web UI server.

| Flag | Description |
|------|-------------|
| `--host` | Host to bind to (default: `127.0.0.1`) |
| `--port` | Port to listen on (default: `8000`) |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `2` | Unsupported file type |
| `3` | Extraction failed |
| `4` | Scanned PDF detected (no OCR) |

## Output Conventions

### Metadata

Every converted file includes a metadata comment:

```markdown
<!-- source: document.pdf | converted: 2026-02-26T12:00:00Z | converter: file2md v0.1.0 -->
```

With `--frontmatter`:

```yaml
---
source: document.pdf
converted: 2026-02-26T12:00:00Z
converter: file2md v0.1.0
---
```

### PDF Page Separators

Pages are separated by `---`. With `--page-labels`:

```markdown
## Page 1

Content of page 1...

---

## Page 2

Content of page 2...
```

### Clean Mode (`--clean`)

- **Paragraph reflow** — undoes hard line wraps from PDF extraction
- **Hyphenation fix** — merges `hyphen-\nated` words across lines
- **Header/footer removal** — detects and removes repeating page headers/footers
- **Whitespace normalization** — collapses extra spaces, limits blank lines

## Architecture

```
src/file2md/
├── convert.py          # Main entry point — dispatches by file type
├── pdf.py              # PDF → Markdown (PyMuPDF)
├── docx_converter.py   # DOCX → Markdown (python-docx)
├── normalize.py        # Text cleanup (reflow, hyphenation, headers/footers)
├── cli.py              # Click CLI (convert, batch, serve)
├── web.py              # FastAPI web server
├── utils.py            # Shared types, validation, metadata
└── templates/
    └── index.html      # Drag-and-drop web UI
```

## Development

```bash
git clone https://github.com/faizkhairi/file2md.git
cd file2md
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -e ".[all]"

# Run tests
pytest

# Lint
ruff check src/ tests/

# Build
python -m build
```

## Known Limitations

- **No OCR** — scanned/image-only PDFs are detected and rejected with a clear error (exit code 4). OCR support is planned for a future release.
- **Complex PDF layouts** — multi-column documents, sidebars, and footnotes may produce text in unexpected order.
- **Nested DOCX lists** — only flat bullet/numbered lists are supported. Nested and mixed lists are not preserved.
- **Merged table cells** — may produce duplicated or empty cells in the Markdown output.

## Troubleshooting

**"All pages appear to be scanned images"** — The PDF contains only images, no extractable text. You need to OCR the PDF first using a tool like `ocrmypdf` before converting.

**Tables not appearing (PDF)** — Use the `--extract-tables` flag. Table detection is off by default to keep output clean for text-heavy documents.

**Output has hard line breaks** — Use the `--clean` flag to enable paragraph reflow, which joins lines that were artificially broken by PDF formatting.

## License

[MIT](LICENSE)
