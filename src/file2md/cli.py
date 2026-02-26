"""CLI entry point using Click."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from . import __version__
from .convert import convert_file
from .utils import ConversionOptions, ExitCode


@click.group()
@click.version_option(version=__version__, prog_name="file2md")
def cli() -> None:
    """Convert PDF and DOCX files to clean, grep-friendly Markdown."""


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), help="Output .md file path.")
@click.option("--clean", is_flag=True, help="Normalize whitespace, reflow, fix hyphenation.")
@click.option("--frontmatter", is_flag=True, help="Add YAML frontmatter with source metadata.")
@click.option("--page-labels", is_flag=True, help="Add ## Page N headings (PDF only).")
@click.option("--extract-tables", is_flag=True, help="Detect and convert tables to GFM (PDF).")
@click.option("--max-chars", type=int, default=None, help="Truncate output at N characters.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing output file.")
@click.option("--quiet", is_flag=True, help="Suppress warnings.")
@click.option("--verbose", is_flag=True, help="Show detailed progress.")
@click.option("--json", "json_output", is_flag=True, help="Machine-readable JSON output.")
def convert(
    input_file: Path,
    output: Path | None,
    clean: bool,
    frontmatter: bool,
    page_labels: bool,
    extract_tables: bool,
    max_chars: int | None,
    overwrite: bool,
    quiet: bool,
    verbose: bool,
    json_output: bool,
) -> None:
    """Convert a single PDF or DOCX file to Markdown."""
    options = ConversionOptions(
        clean=clean,
        frontmatter=frontmatter,
        page_labels=page_labels,
        extract_tables=extract_tables,
        max_chars=max_chars,
    )

    if verbose and not quiet:
        click.echo(f"Converting: {input_file}", err=True)

    result = convert_file(input_file, options)

    if json_output:
        click.echo(
            json.dumps(
                {
                    "source": result.source_file,
                    "exit_code": result.exit_code.value,
                    "warnings": result.warnings,
                    "chars": len(result.markdown),
                    "pages": result.page_count,
                }
            )
        )
        sys.exit(result.exit_code)

    if result.exit_code != ExitCode.SUCCESS:
        if not quiet:
            for w in result.warnings:
                click.echo(f"Warning: {w}", err=True)
        sys.exit(result.exit_code)

    # Determine output path
    if output is None:
        output = input_file.with_suffix(".md")

    if output.exists() and not overwrite:
        click.echo(f"Error: {output} already exists. Use --overwrite to replace.", err=True)
        sys.exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result.markdown, encoding="utf-8")

    if not quiet:
        if result.warnings:
            for w in result.warnings:
                click.echo(f"Warning: {w}", err=True)
        click.echo(f"Converted: {input_file} -> {output}")

    sys.exit(result.exit_code)


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--out-dir", type=click.Path(path_type=Path), required=True, help="Output directory.")
@click.option("--recursive", is_flag=True, help="Process subdirectories.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing files.")
@click.option("--clean", is_flag=True, help="Normalize whitespace, reflow paragraphs.")
@click.option("--frontmatter", is_flag=True, help="Add YAML frontmatter.")
@click.option("--page-labels", is_flag=True, help="Add ## Page N headings (PDF).")
@click.option("--extract-tables", is_flag=True, help="Detect and convert tables (PDF).")
@click.option("--max-chars", type=int, default=None, help="Truncate output at N characters.")
@click.option("--quiet", is_flag=True, help="Suppress warnings.")
@click.option("--verbose", is_flag=True, help="Show detailed progress.")
@click.option("--json", "json_output", is_flag=True, help="Machine-readable JSON output.")
def batch(
    input_dir: Path,
    out_dir: Path,
    recursive: bool,
    overwrite: bool,
    clean: bool,
    frontmatter: bool,
    page_labels: bool,
    extract_tables: bool,
    max_chars: int | None,
    quiet: bool,
    verbose: bool,
    json_output: bool,
) -> None:
    """Batch convert all PDF/DOCX files in a directory."""
    options = ConversionOptions(
        clean=clean,
        frontmatter=frontmatter,
        page_labels=page_labels,
        extract_tables=extract_tables,
        max_chars=max_chars,
    )

    # Find files
    pattern_pdf = "**/*.pdf" if recursive else "*.pdf"
    pattern_docx = "**/*.docx" if recursive else "*.docx"
    files = sorted(set(input_dir.glob(pattern_pdf)) | set(input_dir.glob(pattern_docx)))

    if not files:
        if not quiet:
            click.echo("No PDF or DOCX files found.", err=True)
        sys.exit(0)

    out_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0
    results: list[dict[str, object]] = []

    for file_path in files:
        # Preserve relative directory structure in output
        rel_path = file_path.relative_to(input_dir)
        output_path = out_dir / rel_path.with_suffix(".md")

        if output_path.exists() and not overwrite:
            if verbose and not quiet:
                click.echo(f"Skipping (exists): {file_path}", err=True)
            continue

        if verbose and not quiet:
            click.echo(f"Converting: {file_path}", err=True)

        result = convert_file(file_path, options)

        if result.exit_code == ExitCode.SUCCESS:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.markdown, encoding="utf-8")
            success_count += 1
            if not quiet and not json_output:
                click.echo(f"  -> {output_path}")
        else:
            fail_count += 1
            if not quiet and not json_output:
                for w in result.warnings:
                    click.echo(f"  Warning ({file_path}): {w}", err=True)

        if json_output:
            results.append(
                {
                    "source": str(file_path),
                    "output": str(output_path),
                    "exit_code": result.exit_code.value,
                    "warnings": result.warnings,
                    "chars": len(result.markdown),
                    "pages": result.page_count,
                }
            )

    if json_output:
        click.echo(json.dumps({"files": results, "success": success_count, "failed": fail_count}))
    elif not quiet:
        click.echo(f"\nDone: {success_count} converted, {fail_count} failed.")

    sys.exit(0 if fail_count == 0 else ExitCode.EXTRACTION_FAILED)


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to.")
@click.option("--port", default=8000, type=int, help="Port to listen on.")
def serve(host: str, port: int) -> None:
    """Start the web UI server for drag-and-drop conversion."""
    try:
        import uvicorn
    except ImportError:
        click.echo(
            "Web dependencies not installed. Run: pip install file2md[web]",
            err=True,
        )
        sys.exit(1)

    from .web import app

    click.echo(f"Starting file2md web UI at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
