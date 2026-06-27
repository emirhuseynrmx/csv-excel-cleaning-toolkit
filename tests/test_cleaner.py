from __future__ import annotations

from pathlib import Path

import pandas as pd

from csv_excel_cleaning_toolkit.cleaner import (
    CleaningOptions,
    clean_file,
    clean_frame,
    normalize_column_name,
    write_report,
)


def test_normalize_column_name() -> None:
    assert normalize_column_name(" Customer Name ") == "customer_name"
    assert normalize_column_name("Total Spend ($)") == "total_spend"


def test_clean_frame_normalizes_headers_emails_and_duplicates() -> None:
    frame = pd.DataFrame(
        {
            " Customer Name ": [" Alice ", "Alice"],
            " Email Address ": [" ALICE@EXAMPLE.COM ", "alice@example.com"],
            " Total Spend ": [120.5, 120.5],
        }
    )

    cleaned, report = clean_frame(frame)

    assert list(cleaned.columns) == ["customer_name", "email_address", "total_spend"]
    assert cleaned.loc[0, "customer_name"] == "Alice"
    assert cleaned.loc[0, "email_address"] == "alice@example.com"
    assert len(cleaned) == 1
    assert report.duplicates_removed == 1


def test_clean_frame_fills_missing_values() -> None:
    frame = pd.DataFrame({"Email Address": [None], "Total Spend": [None]})

    cleaned, report = clean_frame(
        frame,
        CleaningOptions(fill_missing={"email_address": "missing@example.com", "total_spend": 0}),
    )

    assert cleaned.loc[0, "email_address"] == "missing@example.com"
    assert cleaned.loc[0, "total_spend"] == 0
    assert report.missing_after == {"email_address": 0, "total_spend": 0}


def test_clean_file_writes_output_and_report(tmp_path: Path) -> None:
    input_path = Path("data/sample_customers.csv")
    output_path = tmp_path / "customers_clean.csv"
    report_path = tmp_path / "report.md"

    cleaned, report = clean_file(input_path, output_path, CleaningOptions())
    write_report(report, report_path)

    assert len(cleaned) == 4
    assert output_path.exists()
    assert "# Cleaning Report" in report_path.read_text(encoding="utf-8")
