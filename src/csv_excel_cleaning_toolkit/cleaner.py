from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
import pandera.pandas as pa
from pydantic import BaseModel, ConfigDict, Field

COLUMN_RE = re.compile(r"[^a-zA-Z0-9]+")
EMAIL_RE = re.compile(r"email", re.IGNORECASE)
EMAIL_FULL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


class CleaningOptions(BaseModel):
    model_config = ConfigDict(frozen=True)

    normalize_headers: bool = True
    trim_text: bool = True
    normalize_emails: bool = True
    validate_emails: bool = True
    coerce_numeric: bool = True
    flag_outliers: bool = True
    drop_duplicates: bool = True
    fill_missing: dict[str, str | int | float | bool] = Field(default_factory=dict)
    numeric_columns: list[str] = Field(default_factory=list)
    outlier_iqr_multiplier: float = Field(default=1.5, gt=0)


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
    inferred_types: dict[str, str]
    invalid_email_counts: dict[str, int]
    outlier_counts: dict[str, int]
    validation_errors: list[str]
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

        lines.extend(["", "## Inferred Column Types", ""])
        for column, dtype in self.inferred_types.items():
            lines.append(f"- `{column}`: `{dtype}`")

        lines.extend(["", "## Email Validation", ""])
        if self.invalid_email_counts:
            for column, count in self.invalid_email_counts.items():
                lines.append(f"- `{column}` invalid emails: `{count}`")
        else:
            lines.append("- No email columns detected.")

        lines.extend(["", "## Numeric Outliers", ""])
        if self.outlier_counts:
            for column, count in self.outlier_counts.items():
                lines.append(f"- `{column}` outliers flagged: `{count}`")
        else:
            lines.append("- No numeric outliers flagged.")

        lines.extend(["", "## Validation", ""])
        if self.validation_errors:
            for error in self.validation_errors:
                lines.append(f"- `{error}`")
        else:
            lines.append("- Pandera validation passed.")

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

    if options.coerce_numeric:
        cleaned = _coerce_numeric_columns(cleaned, options.numeric_columns)

    invalid_email_counts: dict[str, int] = {}
    if options.validate_emails:
        cleaned, invalid_email_counts = _flag_invalid_email_columns(cleaned)

    outlier_counts: dict[str, int] = {}
    if options.flag_outliers:
        cleaned, outlier_counts = _flag_numeric_outliers(
            cleaned,
            multiplier=options.outlier_iqr_multiplier,
        )

    before_dedup = len(cleaned)
    if options.drop_duplicates:
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    duplicates_removed = before_dedup - len(cleaned)
    inferred_types = _infer_column_types(cleaned)
    validation_errors = _validate_cleaned_frame(cleaned)

    report = CleaningReport(
        input_rows=len(original),
        output_rows=len(cleaned),
        input_columns=[str(column) for column in original.columns],
        output_columns=[str(column) for column in cleaned.columns],
        renamed_columns=renamed_columns,
        duplicates_removed=duplicates_removed,
        missing_before=missing_before,
        missing_after=_missing_counts(cleaned),
        inferred_types=inferred_types,
        invalid_email_counts=invalid_email_counts,
        outlier_counts=outlier_counts,
        validation_errors=validation_errors,
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


def _flag_invalid_email_columns(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    cleaned = frame.copy()
    counts: dict[str, int] = {}
    for column in cleaned.columns:
        if not EMAIL_RE.search(str(column)) or str(column).endswith("_is_valid"):
            continue
        validity_column = f"{column}_is_valid"
        cleaned[validity_column] = cleaned[column].map(_is_valid_email)
        counts[str(column)] = int((cleaned[validity_column] == False).sum())  # noqa: E712
    return cleaned, counts


def _is_valid_email(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    return bool(EMAIL_FULL_RE.match(value.strip()))


def _coerce_numeric_columns(frame: pd.DataFrame, numeric_columns: list[str]) -> pd.DataFrame:
    cleaned = frame.copy()
    candidates = numeric_columns or [
        str(column)
        for column in cleaned.columns
        if _looks_numeric_series(cleaned[column])
    ]
    for column in candidates:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(
                cleaned[column].map(_strip_numeric_value),
                errors="coerce",
            )
    return cleaned


def _strip_numeric_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    cleaned = value.replace("$", "").replace(",", "").strip()
    return cleaned or pd.NA


def _looks_numeric_name(column: str) -> bool:
    tokens = ("amount", "price", "spend", "revenue", "total", "payment", "usage")
    return any(token in column.lower() for token in tokens)


def _looks_numeric_series(series: pd.Series) -> bool:
    if not pd.api.types.is_object_dtype(series):
        return pd.api.types.is_numeric_dtype(series)
    non_null = series.dropna()
    if non_null.empty:
        return False
    converted = pd.to_numeric(non_null.map(_strip_numeric_value), errors="coerce")
    return float(converted.notna().mean()) >= 0.8


def _flag_numeric_outliers(
    frame: pd.DataFrame,
    *,
    multiplier: float,
) -> tuple[pd.DataFrame, dict[str, int]]:
    cleaned = frame.copy()
    counts: dict[str, int] = {}
    for column in cleaned.select_dtypes(include="number").columns:
        series = cleaned[column].dropna()
        if len(series) < 4:
            continue
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr
        flag_column = f"{column}_is_outlier"
        cleaned[flag_column] = ((cleaned[column] < lower) | (cleaned[column] > upper)).fillna(False)
        counts[str(column)] = int(cleaned[flag_column].sum())
    return cleaned, counts


def _infer_column_types(frame: pd.DataFrame) -> dict[str, str]:
    inferred: dict[str, str] = {}
    for column in frame.columns:
        series = frame[column]
        if pd.api.types.is_bool_dtype(series):
            inferred[str(column)] = "boolean"
        elif pd.api.types.is_numeric_dtype(series):
            inferred[str(column)] = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(series):
            inferred[str(column)] = "datetime"
        elif EMAIL_RE.search(str(column)):
            inferred[str(column)] = "email"
        else:
            inferred[str(column)] = "datetime" if _looks_datetime_series(series) else "text"
    return inferred


def _looks_datetime_series(series: pd.Series) -> bool:
    non_null = series.dropna()
    if non_null.empty or not pd.api.types.is_object_dtype(non_null):
        return False
    sample = non_null.astype(str)
    if not sample.str.contains(r"\d{4}-\d{2}-\d{2}", regex=True).mean() >= 0.8:
        return False
    parsed_dates = pd.to_datetime(sample, errors="coerce", format="mixed")
    return bool(parsed_dates.notna().mean() >= 0.8)


def _validate_cleaned_frame(frame: pd.DataFrame) -> list[str]:
    schema = pa.DataFrameSchema(
        {
            str(column): pa.Column(nullable=True)
            for column in frame.columns
        },
        strict=True,
        coerce=False,
    )
    try:
        schema.validate(frame, lazy=True)
    except pa.errors.SchemaErrors as exc:
        return [str(error) for error in exc.failure_cases["failure_case"].head(10).tolist()]
    return []


def _missing_counts(frame: pd.DataFrame) -> dict[str, int]:
    return {str(column): int(count) for column, count in frame.isna().sum().items()}
