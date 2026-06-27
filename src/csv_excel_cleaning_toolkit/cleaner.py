from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

COLUMN_RE = re.compile(r"[^a-zA-Z0-9]+")
EMAIL_RE = re.compile(r"email", re.IGNORECASE)


class CleaningOptions(BaseModel):
    model_config = ConfigDict(frozen=True)

    normalize_headers: bool = True
    trim_text: bool = True
    normalize_emails: bool = True
    drop_duplicates: bool = True
    fill_missing: dict[str, str | int | float | bool] = Field(default_factory=dict)


class CleaningReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_rows: int
    output_rows: int
    input_columns: list[str]
    output_columns: list[str]
    renamed_columns: dict[str, str]
    duplicates_removed: int
    missing_before: dict[str, int]
    missing_after: dict[str, int]
    output_path: Path | None = None

    def to_markdown(self) -> str:
        lines = [
            "# Cleaning Report",
            "",
            f"- Input rows: `{self.input_rows}`",
            f"- Output rows: `{self.output_rows}`",
            f"- Duplicates removed: `{self.duplicates_removed}`",
        ]
        if self.output_path:
            lines.append(f"- Output file: `{self.output_path}`")

        lines.extend(["", "## Renamed Columns", ""])
        if self.renamed_columns:
            for source, target in self.renamed_columns.items():
                lines.append(f"- `{source}` -> `{target}`")
        else:
            lines.append("- No columns renamed.")

        lines.extend(["", "## Missing Values After Cleaning", ""])
        for column, count in self.missing_after.items():
            lines.append(f"- `{column}`: `{count}`")

        return "\n".join(lines) + "\n"


def normalize_column_name(column: str) -> str:
    normalized = COLUMN_RE.sub("_", column.strip().lower()).strip("_")
    return normalized or "unnamed_column"


def load_options(profile_path: Path | None) -> CleaningOptions:
    if profile_path is None:
        return CleaningOptions()
    return CleaningOptions.model_validate_json(profile_path.read_text(encoding="utf-8"))


def load_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported input file: {path}")


def save_table(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame.to_csv(path, index=False)
    elif suffix in {".xlsx", ".xls"}:
        frame.to_excel(path, index=False, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported output file: {path}")
    return path


def clean_frame(
    frame: pd.DataFrame,
    options: CleaningOptions | None = None,
) -> tuple[pd.DataFrame, CleaningReport]:
    options = options or CleaningOptions()
    original = frame.copy()
    cleaned = frame.copy()
    renamed_columns: dict[str, str] = {}
    missing_before = _missing_counts(cleaned)

    if options.normalize_headers:
        new_columns = [normalize_column_name(column) for column in cleaned.columns]
        renamed_columns = {
            str(source): target
            for source, target in zip(cleaned.columns, new_columns, strict=True)
            if str(source) != target
        }
        cleaned.columns = new_columns

    if options.trim_text:
        cleaned = _trim_text_columns(cleaned)

    if options.normalize_emails:
        cleaned = _normalize_email_columns(cleaned)

    if options.fill_missing:
        with pd.option_context("future.no_silent_downcasting", True):
            cleaned = cleaned.fillna(options.fill_missing).infer_objects(copy=False)

    before_dedup = len(cleaned)
    if options.drop_duplicates:
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    duplicates_removed = before_dedup - len(cleaned)

    report = CleaningReport(
        input_rows=len(original),
        output_rows=len(cleaned),
        input_columns=[str(column) for column in original.columns],
        output_columns=[str(column) for column in cleaned.columns],
        renamed_columns=renamed_columns,
        duplicates_removed=duplicates_removed,
        missing_before=missing_before,
        missing_after=_missing_counts(cleaned),
    )
    return cleaned, report


def clean_file(
    input_path: Path,
    output_path: Path,
    options: CleaningOptions,
) -> tuple[pd.DataFrame, CleaningReport]:
    cleaned, report = clean_frame(load_table(input_path), options)
    save_table(cleaned, output_path)
    return cleaned, report.model_copy(update={"output_path": output_path})


def write_report(report: CleaningReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_markdown(), encoding="utf-8")
    return path


def _trim_text_columns(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    for column in cleaned.select_dtypes(include="object").columns:
        cleaned[column] = cleaned[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
    return cleaned


def _normalize_email_columns(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    for column in cleaned.columns:
        if EMAIL_RE.search(str(column)):
            cleaned[column] = cleaned[column].map(_normalize_email_value)
    return cleaned


def _normalize_email_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.strip().lower()
    return normalized or pd.NA


def _missing_counts(frame: pd.DataFrame) -> dict[str, int]:
    return {str(column): int(count) for column, count in frame.isna().sum().items()}
