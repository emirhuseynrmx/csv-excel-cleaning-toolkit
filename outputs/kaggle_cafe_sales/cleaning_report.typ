#set page(margin: 34pt)
#set text(font: "Arial", size: 8.8pt)
#set heading(numbering: none)

#let accent = rgb("#1457d9")
#let good = rgb("#11845b")
#let warn = rgb("#b86b00")
#let bad = rgb("#b42318")
#let muted = rgb("#667085")
#let panel = rgb("#f6f8fb")

#let stat(label, value, color: accent) = block[
  #rect(fill: panel, radius: 5pt, inset: 8pt, width: 100%)[
    #text(size: 7pt, fill: muted, weight: "bold")[#upper(label)]
    #linebreak()
    #text(size: 15pt, fill: color, weight: "bold")[#value]
  ]
]

= Kaggle Cafe Sales Dirty Data Cleaning Report

#text(fill: muted)[
  Kaggle dirty sales data cleaned into analysis-ready CSV. The report focuses on
  normalized fields, invalid tokens, missing values, and review flags.
]

#grid(columns: (1fr, 1fr, 1fr, 1fr), gutter: 7pt)[
  #stat("Quality score", "85.9/100", color: warn)
][
  #stat("Rows", "10000 -> 10000")
][
  #stat("Duplicates", "0", color: warn)
][
  #stat("Validation", "passed")
]

== Cleaning Summary

#grid(columns: (1fr, 1fr), gutter: 12pt)[
  === Warnings
  - total_spent has 259 numeric outlier values.
- item still has 969 missing values.
- quantity still has 479 missing values.
- price_per_unit still has 533 missing values.
- total_spent still has 502 missing values.
- payment_method still has 3178 missing values.
- location still has 3961 missing values.
][
  === Output
  - Cleaned file: `outputs/kaggle_cafe_sales/cleaned_data.csv`
  - Email flags: `0`
  - Outlier flags: `259`
]

== Renamed Columns

#table(
  columns: (1fr, 1fr),
  inset: 5pt,
  stroke: rgb("#d0d5dd"),
  [*Before*], [*After*],
  [Transaction ID], [transaction_id],
  [Item], [item],
  [Quantity], [quantity],
  [Price Per Unit], [price_per_unit],
  [Total Spent], [total_spent],
  [Payment Method], [payment_method],
  [Location], [location],
  [Transaction Date], [transaction_date],
)

== Column Types and Missing Values

#table(
  columns: (1.2fr, .8fr, .7fr),
  inset: 5pt,
  stroke: rgb("#d0d5dd"),
  [*Column*], [*Type*], [*Missing*],
  [transaction_id], [text], [0],
  [item], [text], [969],
  [quantity], [numeric], [479],
  [price_per_unit], [numeric], [533],
  [total_spent], [numeric], [502],
  [payment_method], [text], [3178],
  [location], [text], [3961],
  [transaction_date], [datetime], [460],
  [quantity_is_outlier], [boolean], [0],
)

== Cleaned Sample

#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  inset: 5pt,
  stroke: rgb("#d0d5dd"),
  [*transaction_id*],  [*item*],  [*quantity*],  [*total_spent*],
  [TXN_1961373],  [Coffee],  [2.0],  [4.0],
  [TXN_4977031],  [Cake],  [4.0],  [12.0],
  [TXN_7034554],  [Salad],  [2.0],  [10.0],
  [TXN_3160411],  [Coffee],  [2.0],  [4.0],
)
