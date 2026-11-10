"""Analyze Missouri State Expenditures using rolling averages.

Missouri State Expenditures - Travel Rolling Monitoring
Author: Angie Crews
Date: 2026-11

Analyze annual Missouri travel expenditures
using rolling averages.
"""

# ----------------------------------------------------
# STEP 1: IMPORT LIBRARIES AND SET FILE PATHS
# ----------------------------------------------------

from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl

# Locate the project root and data folders.
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"

# Create the artifacts folder if needed.
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# File for the final monitoring results.
OUTPUT_FILE = ARTIFACTS_DIR / "missouri_travel_rolling.csv"


# ----------------------------------------------------
# STEP 2: LOAD THE ANNUAL EXPENDITURE DATA
# ----------------------------------------------------

# Find all Missouri State Expenditures CSV files.
csv_files = sorted(DATA_DIR.glob("*State_Expenditures*.csv"))

# Store each year's data.
dataframes = []

for file in csv_files:
    df = pl.read_csv(
        file,
        infer_schema_length=0,
    )

    print(f"Loaded {file.name}: {df.height:,} records")

    dataframes.append(df)

# Combine all five years into one DataFrame.
if not dataframes:
    raise FileNotFoundError("No State Expenditures CSV files found.")

expenditures = pl.concat(dataframes)

print(f"Total expenditure records: {expenditures.height:,}")

# ----------------------------------------------------
# STEP 3: FILTER TRAVEL EXPENDITURES
# ----------------------------------------------------

# Keep only records categorized as TRAVEL.
travel = expenditures.filter(pl.col("Category Description") == "TRAVEL")

# Display the number of travel records.
print(f"Total travel expenditure records: {travel.height:,}")

# Display travel records by fiscal year.
travel_by_year = (
    travel.group_by("Fiscal Year")
    .agg(pl.len().alias("Travel Records"))
    .sort("Fiscal Year")
)

print(travel_by_year)

# ----------------------------------------------------
# STEP 4: CALCULATE ANNUAL TRAVEL EXPENDITURES
# ----------------------------------------------------

# Remove commas and convert payment amounts to numbers.
travel = travel.with_columns(
    pl.col("Payments Total")
    .str.replace_all(",", "")
    .cast(pl.Float64, strict=False)
    .alias("payment_amount")
)

# Check for payment amounts that could not be converted.
invalid_payments = travel.filter(pl.col("payment_amount").is_null()).height

print(f"Invalid or missing payment amounts: {invalid_payments:,}")

# Calculate total travel spending for each fiscal year.
annual_travel = (
    travel.group_by("Fiscal Year")
    .agg(
        pl.len().alias("travel_records"),
        pl.col("payment_amount").sum().alias("total_travel_spending"),
    )
    .sort("Fiscal Year")
)

print("\nAnnual Missouri Travel Expenditures:")
print(annual_travel)

# ----------------------------------------------------
# STEP 5: CALCULATE THREE-YEAR ROLLING AVERAGE
# ----------------------------------------------------

# Use the current year and two preceding years.
WINDOW_SIZE = 3

# Calculate the rolling average of annual travel spending.
annual_travel = annual_travel.with_columns(
    pl.col("total_travel_spending")
    .rolling_mean(window_size=WINDOW_SIZE)
    .alias("travel_rolling_mean")
)

print("\nThree-Year Rolling Travel Spending:")
print(annual_travel)

# ----------------------------------------------------
# STEP 6: SAVE ROLLING MONITORING RESULTS
# ----------------------------------------------------

# Save the annual totals and rolling averages.
annual_travel.write_csv(OUTPUT_FILE)

print(f"\nSaved monitoring results to: {OUTPUT_FILE}")
print("Missouri travel rolling monitoring completed successfully!")

# --------------------------------------------------
# STEP 7: CREATE TRAVEL SPENDING CHART
# --------------------------------------------------

# Create the images folder if needed.
IMAGES_DIR = ROOT_DIR / "docs" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Convert annual spending to millions of dollars.
years = annual_travel["Fiscal Year"].to_list()
spending = [
    value / 1_000_000 for value in annual_travel["total_travel_spending"].to_list()
]
rolling = [
    value / 1_000_000 if value is not None else float("nan")
    for value in annual_travel["travel_rolling_mean"].to_list()
]

# Create a line chart.
fig, ax = plt.subplots(figsize=(10, 6))

ax.plot(years, spending, marker="o", label="Annual Travel Spending")
ax.plot(years, rolling, marker="s", label="3-Year Rolling Average")

ax.set_title("Missouri Travel Expenditures (2022–2026)")
ax.set_xlabel("Fiscal Year")
ax.set_ylabel("Travel Spending (Millions of Dollars)")
ax.legend()
ax.grid(True, alpha=0.3)

# Save the chart in the documentation images folder.
CHART_FILE = IMAGES_DIR / "missouri_travel_rolling.png"
fig.savefig(CHART_FILE, dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"\nChart saved to: {CHART_FILE}")
