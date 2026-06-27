# CSV Excel Cleaning Toolkit

[![CI](https://github.com/emirhuseynrmx/csv-excel-cleaning-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/emirhuseynrmx/csv-excel-cleaning-toolkit/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

Reusable Python toolkit for cleaning messy CSV and Excel files into analysis-ready outputs.

Built for practical data automation work: normalize headers, trim messy strings, standardize emails, remove duplicates, fill missing values, and generate a clear cleaning report.

## What It Does

- reads `.csv`, `.xlsx`, and `.xls`
- normalizes column names to `snake_case`
- trims whitespace in text columns
- normalizes email columns
- validates email columns and adds `*_is_valid` quality flags
- coerces numeric-looking columns such as spend, price, amount, orders, and revenue
- flags numeric outliers with IQR-based `*_is_outlier` columns
- infers basic column types for the report
- removes duplicate rows
- fills missing values from a JSON profile
- validates the final table shape with Pandera
- exports clean CSV or Excel
- writes a Markdown report with row counts, duplicate counts, missing values, and changed columns

## Demo

```bash
pip install -e ".[dev]"
clean-data data/sample_customers.csv --out outputs/customers_clean.csv --report outputs/report.md
```

Use a cleaning profile:

```bash
clean-data \
  data/sample_customers.csv \
  --profile examples/customer_profile.json \
  --out outputs/customers_clean.xlsx \
  --report outputs/report.md
```

## Example Output

Input columns like:

```text
 Customer Name , Email Address , Signup Date , Total Spend 
```

become:

```text
customer_name,email_address,signup_date,total_spend
```

The report includes:

- input rows and output rows
- duplicates removed
- missing values before and after cleaning
- renamed columns
- inferred column types
- invalid email counts
- numeric outlier counts
- Pandera validation status
- exported file path

## Run Tests

```bash
ruff check .
pytest
```

## Use Cases

- messy customer CSV cleanup
- Excel file preparation for dashboards
- email list normalization
- CRM import preparation
- deduplication before outreach
- repeatable small-business data workflows

## Scope

This toolkit cleans tabular files. It does not guess business rules automatically; those rules should be provided through a profile or reviewed with the final report.
