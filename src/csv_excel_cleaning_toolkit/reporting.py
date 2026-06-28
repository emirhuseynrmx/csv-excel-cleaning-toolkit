from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from csv_excel_cleaning_toolkit.cleaner import CleaningOptions, CleaningReport, clean_file


class CleaningReportView(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    input_rows: int = Field(ge=0)
    output_rows: int = Field(ge=0)
    duplicates_removed: int = Field(ge=0)
    renamed_columns: dict[str, str]
    invalid_email_counts: dict[str, int]
    outlier_counts: dict[str, int]
    missing_after: dict[str, int]
    inferred_types: dict[str, str]
    validation_errors: tuple[str, ...]
    sample_records: tuple[dict[str, Any], ...]
    output_path: str | None

    @property
    def quality_score(self) -> float:
        penalties = 0.0
        penalties += min(self.duplicates_removed, 10) * 2.0
        penalties += sum(self.invalid_email_counts.values()) * 6.0
        penalties += sum(self.outlier_counts.values()) * 3.0
        penalties += sum(self.missing_after.values()) * 1.5
        penalties += len(self.validation_errors) * 10.0
        return round(max(0.0, 100.0 - penalties), 1)


def build_report_view(
    report: CleaningReport,
    cleaned: pd.DataFrame,
    *,
    title: str,
) -> CleaningReportView:
    return CleaningReportView(
        title=title,
        input_rows=report.input_rows,
        output_rows=report.output_rows,
        duplicates_removed=report.duplicates_removed,
        renamed_columns=report.renamed_columns,
        invalid_email_counts=report.invalid_email_counts,
        outlier_counts=report.outlier_counts,
        missing_after=report.missing_after,
        inferred_types=report.inferred_types,
        validation_errors=tuple(report.validation_errors),
        sample_records=tuple(_sample_records(cleaned)),
        output_path=report.output_path.as_posix() if report.output_path else None,
    )


def generate_sample_report(
    input_path: Path,
    output_dir: Path,
    *,
    title: str = "CSV / Excel Cleaning Report",
    compile_pdf: bool = True,
) -> tuple[Path, Path | None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_output = output_dir / "customers_clean.csv"
    cleaned, report = clean_file(input_path, clean_output, CleaningOptions())
    view = build_report_view(report, cleaned, title=title)
    typ_path = output_dir / "cleaning_report.typ"
    pdf_path = output_dir / "cleaning_report.pdf"
    typ_path.write_text(render_typst(view), encoding="utf-8")
    if not compile_pdf:
        return typ_path, None
    typst = shutil.which("typst")
    if typst is None:
        return typ_path, None
    subprocess.run(
        [typst, "compile", typ_path.name, pdf_path.name],
        check=True,
        cwd=output_dir,
    )
    return typ_path, pdf_path


def render_typst(report: CleaningReportView) -> str:
    score_color = _score_color(report.quality_score)
    renamed_rows = "\n".join(
        f"  [{_typ_text(source)}], [{_typ_text(target)}],"
        for source, target in report.renamed_columns.items()
    )
    if not renamed_rows:
        renamed_rows = "  [No renamed columns], [No change],"
    type_rows = "\n".join(
        f"  [{_typ_text(column)}], [{_typ_text(dtype)}], [{report.missing_after.get(column, 0)}],"
        for column, dtype in report.inferred_types.items()
    )
    sample_rows = "\n".join(_sample_row(record) for record in report.sample_records)
    warnings = _warnings(report)
    warning_rows = "\n".join(f"- {_typ_text(item)}" for item in warnings)
    if not warning_rows:
        warning_rows = "- No blocking issues were found."

    return f"""#set page(margin: 42pt)
#set text(font: "Arial", size: 10pt)
#set heading(numbering: none)

#let accent = rgb("#1457d9")
#let good = rgb("#11845b")
#let warn = rgb("#b86b00")
#let bad = rgb("#b42318")
#let muted = rgb("#667085")
#let panel = rgb("#f6f8fb")

#let stat(label, value, color: accent) = block[
  #rect(fill: panel, radius: 5pt, inset: 10pt, width: 100%)[
    #text(size: 8pt, fill: muted, weight: "bold")[#upper(label)]
    #linebreak()
    #text(size: 18pt, fill: color, weight: "bold")[#value]
  ]
]

= {_typ_text(report.title)}

#text(fill: muted)[
  Data cleaning summary for a CRM, spreadsheet, dashboard, or analytics import.
  The report focuses on what changed and which fields still need review.
]

#grid(columns: (1fr, 1fr, 1fr, 1fr), gutter: 8pt)[
  #stat("Quality score", "{report.quality_score:.1f}/100", color: {score_color})
][
  #stat("Rows", "{report.input_rows} -> {report.output_rows}")
][
  #stat("Duplicates", "{report.duplicates_removed}", color: warn)
][
  #stat("Validation", "{'passed' if not report.validation_errors else 'review'}")
]

== Cleaning Summary

#grid(columns: (1fr, 1fr), gutter: 12pt)[
  === Warnings
  {warning_rows}
][
  === Output
  - Cleaned file: `{_typ_text(report.output_path or "not written")}`
  - Email flags: `{sum(report.invalid_email_counts.values())}`
  - Outlier flags: `{sum(report.outlier_counts.values())}`
]

== Renamed Columns

#table(
  columns: (1fr, 1fr),
  inset: 5pt,
  stroke: rgb("#d0d5dd"),
  [*Before*], [*After*],
{renamed_rows}
)

== Column Types and Missing Values

#table(
  columns: (1.2fr, .8fr, .7fr),
  inset: 5pt,
  stroke: rgb("#d0d5dd"),
  [*Column*], [*Type*], [*Missing*],
{type_rows}
)

== Cleaned Sample

#table(
  columns: (1.2fr, 1.5fr, 1fr, 1fr),
  inset: 5pt,
  stroke: rgb("#d0d5dd"),
  [*Customer*], [*Email*], [*Spend*], [*Segment*],
{sample_rows}
)
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the sample cleaning PDF report.")
    parser.add_argument("input", type=Path, nargs="?", default=Path("data/sample_customers.csv"))
    parser.add_argument("--out", type=Path, default=Path("outputs/sample_report"))
    parser.add_argument("--title", default="CSV / Excel Cleaning Report")
    parser.add_argument("--no-pdf", action="store_true")
    args = parser.parse_args()
    typ_path, pdf_path = generate_sample_report(
        args.input,
        args.out,
        title=args.title,
        compile_pdf=not args.no_pdf,
    )
    print(f"Wrote {typ_path}")
    if pdf_path is not None:
        print(f"Wrote {pdf_path}")


def _warnings(report: CleaningReportView) -> list[str]:
    warnings: list[str] = []
    if report.duplicates_removed:
        warnings.append(f"{report.duplicates_removed} duplicate rows were removed.")
    for column, count in report.invalid_email_counts.items():
        if count:
            warnings.append(f"{column} has {count} invalid email values.")
    for column, count in report.outlier_counts.items():
        if count:
            warnings.append(f"{column} has {count} numeric outlier values.")
    for column, count in report.missing_after.items():
        if count:
            warnings.append(f"{column} still has {count} missing values.")
    warnings.extend(report.validation_errors)
    return warnings[:7]


def _sample_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.where(pd.notna(frame), None).head(6).to_dict(orient="records")


def _sample_row(record: dict[str, Any]) -> str:
    customer = record.get("customer_name") or record.get("name") or ""
    email = record.get("email_address") or record.get("email") or ""
    spend = record.get("total_spend") or record.get("spend") or ""
    segment = record.get("segment") or record.get("status") or ""
    return (
        f"  [{_typ_text(customer)}],"
        f" [{_typ_text(email)}],"
        f" [{_typ_text(spend)}],"
        f" [{_typ_text(segment)}],"
    )


def _score_color(score: float) -> str:
    if score >= 90:
        return "good"
    if score >= 75:
        return "warn"
    return "bad"


def _typ_text(value: Any) -> str:
    if value is not None:
        try:
            if pd.isna(value):
                return ""
        except TypeError:
            pass
    text = "" if value is None else str(value)
    replacements = {
        "\\": "\\\\",
        "[": "\\[",
        "]": "\\]",
        "#": "\\#",
        "$": "\\$",
        "@": "\\@",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
