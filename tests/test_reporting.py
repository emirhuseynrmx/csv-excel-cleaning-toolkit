from __future__ import annotations

from pathlib import Path

import pandas as pd

from csv_excel_cleaning_toolkit.cleaner import CleaningOptions, clean_frame
from csv_excel_cleaning_toolkit.reporting import (
    build_report_view,
    generate_sample_report,
    render_typst,
)


def test_build_report_view_scores_quality_issues() -> None:
    frame = pd.DataFrame(
        {
            "Customer Name": ["Alice", "Alice", "Bob"],
            "Email Address": ["alice@example.com", "alice@example.com", "bad-email"],
            "Total Spend": ["10", "10", "999"],
        }
    )

    cleaned, report = clean_frame(frame, CleaningOptions())
    view = build_report_view(report, cleaned, title="Cleaning")

    assert view.duplicates_removed == 1
    assert view.invalid_email_counts["email_address"] == 1
    assert view.quality_score < 100


def test_render_typst_contains_client_sections() -> None:
    cleaned, report = clean_frame(pd.DataFrame({"Email": ["alice@example.com"]}))
    typst = render_typst(build_report_view(report, cleaned, title="Cleaning"))

    assert "= Cleaning" in typst
    assert "Cleaning Summary" in typst
    assert "Renamed Columns" in typst
    assert "Cleaned Sample" in typst


def test_generate_sample_report_writes_typst_without_pdf(tmp_path: Path) -> None:
    input_path = tmp_path / "customers.csv"
    input_path.write_text("Name,Email\nAlice,alice@example.com\n", encoding="utf-8")

    typ_path, pdf_path = generate_sample_report(input_path, tmp_path / "out", compile_pdf=False)

    assert typ_path.exists()
    assert pdf_path is None
    assert "CSV / Excel Cleaning Report" in typ_path.read_text(encoding="utf-8")
