from __future__ import annotations

from typer.testing import CliRunner

from csv_excel_cleaning_toolkit.cli import app


def test_cli_clean_command(tmp_path) -> None:
    output_path = tmp_path / "clean.csv"
    report_path = tmp_path / "report.md"

    result = CliRunner().invoke(
        app,
        [
            "data/sample_customers.csv",
            "--out",
            str(output_path),
            "--report",
            str(report_path),
        ],
    )

    assert result.exit_code == 0
    assert "Cleaned 5 rows" in result.output
    assert output_path.exists()
    assert report_path.exists()
