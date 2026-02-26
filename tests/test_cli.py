"""Tests for the CLI using Click's CliRunner."""

import json
from pathlib import Path

from click.testing import CliRunner

from file2md.cli import cli


class TestConvertCommand:
    def test_convert_pdf(self, sample_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        output = tmp_path / "output.md"
        result = runner.invoke(cli, ["convert", str(sample_pdf), "-o", str(output)])
        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "<!-- source:" in content

    def test_convert_docx(self, sample_docx: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        output = tmp_path / "output.md"
        result = runner.invoke(cli, ["convert", str(sample_docx), "-o", str(output)])
        assert result.exit_code == 0
        assert output.exists()

    def test_convert_default_output(self, sample_pdf: Path) -> None:
        runner = CliRunner()
        runner.invoke(cli, ["convert", str(sample_pdf)])
        # Default output is same name with .md extension
        expected_output = sample_pdf.with_suffix(".md")
        assert expected_output.exists()
        expected_output.unlink()  # cleanup

    def test_convert_no_overwrite(self, sample_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        output = tmp_path / "output.md"
        output.write_text("existing content")
        result = runner.invoke(cli, ["convert", str(sample_pdf), "-o", str(output)])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_convert_with_overwrite(self, sample_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        output = tmp_path / "output.md"
        output.write_text("existing content")
        result = runner.invoke(cli, ["convert", str(sample_pdf), "-o", str(output), "--overwrite"])
        assert result.exit_code == 0

    def test_convert_json_output(self, sample_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        output = tmp_path / "output.md"
        result = runner.invoke(cli, ["convert", str(sample_pdf), "-o", str(output), "--json"])
        data = json.loads(result.output)
        assert data["exit_code"] == 0
        assert data["chars"] > 0
        assert data["pages"] == 3

    def test_convert_with_flags(self, sample_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        output = tmp_path / "output.md"
        result = runner.invoke(
            cli,
            [
                "convert",
                str(sample_pdf),
                "-o",
                str(output),
                "--clean",
                "--frontmatter",
                "--page-labels",
            ],
        )
        assert result.exit_code == 0
        content = output.read_text(encoding="utf-8")
        assert "---\n" in content

    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert "file2md" in result.output
        assert "0.3.0" in result.output


class TestBatchCommand:
    def test_batch_convert(self, sample_pdf: Path, sample_docx: Path, tmp_path: Path) -> None:
        # Create input dir with files
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        # Copy fixtures to input dir
        import shutil

        shutil.copy(sample_pdf, input_dir / "test.pdf")
        shutil.copy(sample_docx, input_dir / "test.docx")

        out_dir = tmp_path / "output"
        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(input_dir), "--out-dir", str(out_dir)])
        assert result.exit_code == 0
        assert (out_dir / "test.md").exists()

    def test_batch_empty_dir(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "empty"
        input_dir.mkdir()
        out_dir = tmp_path / "output"
        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(input_dir), "--out-dir", str(out_dir)])
        assert result.exit_code == 0
