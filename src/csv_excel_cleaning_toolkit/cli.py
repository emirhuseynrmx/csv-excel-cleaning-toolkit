from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from csv_excel_cleaning_toolkit.cleaner import clean_file, load_options, write_report

app = typer.Typer(help="Clean messy CSV and Excel files into analysis-ready outputs.")
console = Console()


@app.command()
def clean(
    input_path: Annotated[Path, typer.Argument(help="Input CSV or Excel file.")],
    out: Annotated[Path, typer.Option(help="Clean output path.")] = Path("outputs/clean.csv"),
    report: Annotated[Path, typer.Option(help="Markdown report path.")] = Path("outputs/report.md"),
    profile: Annotated[Path | None, typer.Option(help="Optional cleaning profile JSON.")] = None,
) -> None:
    options = load_options(profile)
    cleaned, cleaning_report = clean_file(input_path, out, options)
    write_report(cleaning_report, report)

    console.print(f"[green]Cleaned {len(cleaned)} rows[/green]")
    console.print(f"[green]Exported to {out}[/green]")
    console.print(f"[green]Report written to {report}[/green]")
