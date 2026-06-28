#set page(margin: 42pt)
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

= CSV / Excel Cleaning Report

#text(fill: muted)[
  Data cleaning summary for a CRM, spreadsheet, dashboard, or analytics import.
  The report focuses on what changed and which fields still need review.
]

#grid(columns: (1fr, 1fr, 1fr, 1fr), gutter: 8pt)[
  #stat("Quality score", "87.5/100", color: warn)
][
  #stat("Rows", "6 -> 5")
][
  #stat("Duplicates", "1", color: warn)
][
  #stat("Validation", "passed")
]

== Cleaning Summary

#grid(columns: (1fr, 1fr), gutter: 12pt)[
  === Warnings
  - 1 duplicate rows were removed.
- email_address has 1 invalid email values.
- total_spend has 1 numeric outlier values.
- total_spend still has 1 missing values.
][
  === Output
  - Cleaned file: `outputs/sample_report/customers_clean.csv`
  - Email flags: `1`
  - Outlier flags: `1`
]

== Renamed Columns

#table(
  columns: (1fr, 1fr),
  inset: 5pt,
  stroke: rgb("#d0d5dd"),
  [*Before*], [*After*],
  [ Customer Name ], [customer_name],
  [ Email Address ], [email_address],
  [ Signup Date ], [signup_date],
  [ Total Spend ], [total_spend],
  [ Orders ], [orders],
  [ Segment ], [segment],
  [ Status], [status],
)

== Column Types and Missing Values

#table(
  columns: (1.2fr, .8fr, .7fr),
  inset: 5pt,
  stroke: rgb("#d0d5dd"),
  [*Column*], [*Type*], [*Missing*],
  [customer_name], [text], [0],
  [email_address], [email], [0],
  [signup_date], [datetime], [0],
  [total_spend], [numeric], [1],
  [orders], [numeric], [0],
  [segment], [text], [0],
  [status], [text], [0],
  [email_address_is_valid], [boolean], [0],
  [total_spend_is_outlier], [boolean], [0],
  [orders_is_outlier], [boolean], [0],
)

== Cleaned Sample

#table(
  columns: (1.2fr, 1.5fr, 1fr, 1fr),
  inset: 5pt,
  stroke: rgb("#d0d5dd"),
  [*Customer*], [*Email*], [*Spend*], [*Segment*],
  [Alice Johnson], [alice\@example.com], [120.5], [Retail],
  [Bob Smith], [bob\@example.com], [80.0], [Retail],
  [Carla Reyes], [bad-email], [], [Wholesale],
  [Diego Martins], [diego\@example.com], [210.75], [Wholesale],
  [Nora Lee], [nora\@example.com], [9999.0], [Enterprise],
)
