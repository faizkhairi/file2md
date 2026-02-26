# file2md

## Quick Reference
- **Language**: Python 3.11+
- **Package manager**: pip (use venv)
- **Test command**: `pytest`
- **Lint command**: `ruff check src/ tests/`
- **Format command**: `ruff format src/ tests/`
- **Build**: `python -m build`
- **Dev install**: `pip install -e ".[all]"`
- **Run web UI**: `file2md serve`
- **Run CLI**: `file2md convert input.pdf -o output.md`

## Architecture
- `src/file2md/` — source layout (prevents accidental local imports)
- `convert.py` — dispatcher, entry point for library usage
- `pdf.py` — PDF → Markdown (PyMuPDF)
- `docx_converter.py` — DOCX → Markdown (python-docx)
- `normalize.py` — markdown cleanup (reflow, hyphenation, headers/footers)
- `cli.py` — Click CLI with convert/batch/serve subcommands
- `web.py` — FastAPI web server with drag-and-drop UI
- `utils.py` — shared data classes, validation, metadata builder

## Conventions
- Exit codes: 0=success, 2=unsupported, 3=failed, 4=scanned PDF
- All output normalized to LF line endings
- Deterministic: same input → same output (except timestamp in metadata)
- No OCR — scanned PDFs return exit code 4
- PyMuPDF table API: `for table in page.find_tables(): table.to_markdown()`
- DOCX lists: style-name detection only (flat, no nested list API)
- Upload validation: extension + MIME + content sniffing (magic bytes)
