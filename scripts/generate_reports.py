"""
generate_reports.py
-------------------
Generates synthetic daily compliance issue data for the compliance-monitor project.

- 20 months of daily records (18 months historical + ~2 months current)
- Products and issue taxonomy match the connected metrics-store / transcript-analysis universe
- Injects realistic spikes so the monitor has meaningful signals to detect
- Outputs: data/daily_issues.csv
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
import os

np.random.seed(42)

# ── Taxonomy (matches transcript-analysis) ────────────────────────────────────
PRODUCTS = [
    "Starter",
    "Pro",
    "Business",
    "Enterprise",
    "Add-on: Analytics",
    "Add-on: SSO",
]

ISSUE_TYPES = [
    "Billing",
    "Online Ordering",
    "Marketing / SEO",
    "Product / Feature",
    "Account Access",
    "Onboarding",
]

# ── Base daily issue rates (avg issues per day, per product/issue combo) ──────
BASE_RATES = {
    ("Starter",           "Billing"):           3.2,
    ("Starter",           "Online Ordering"):   1.5,
    ("Starter",           "Marketing / SEO"):   1.0,
    ("Starter",           "Product / Feature"): 2.8,
    ("Starter",           "Account Access"):    1.1,
    ("Starter",           "Onboarding"):        2.0,

    ("Pro",               "Billing"):           2.1,
    ("Pro",               "Online Ordering"):   1.2,
    ("Pro",               "Marketing / SEO"):   0.9,
    ("Pro",               "Product / Feature"): 1.6,
    ("Pro",               "Account Access"):    1.4,
    ("Pro",               "Onboarding"):        1.3,

    ("Business",          "Billing"):           1.4,
    ("Business",          "Online Ordering"):   0.8,
    ("Business",          "Marketing / SEO"):   0.7,
    ("Business",          "Product / Feature"): 0.9,
    ("Business",          "Account Access"):    1.8,
    ("Business",          "Onboarding"):        0.6,

    ("Enterprise",        "Billing"):           0.6,
    ("Enterprise",        "Online Ordering"):   0.4,
    ("Enterprise",        "Marketing / SEO"):   0.3,
    ("Enterprise",        "Product / Feature"): 0.5,
    ("Enterprise",        "Account Access"):    2.1,
    ("Enterprise",        "Onboarding"):        0.4,

    ("Add-on: Analytics", "Billing"):           1.8,
    ("Add-on: Analytics", "Online Ordering"):   0.5,
    ("Add-on: Analytics", "Marketing / SEO"):   0.6,
    ("Add-on: Analytics", "Product / Feature"): 2.2,
    ("Add-on: Analytics", "Account Access"):    0.7,
    ("Add-on: Analytics", "Onboarding"):        0.9,

    ("Add-on: SSO",       "Billing"):           0.9,
    ("Add-on: SSO",       "Online Ordering"):   0.3,
    ("Add-on: SSO",       "Marketing / SEO"):   0.2,
    ("Add-on: SSO",       "Product / Feature"): 1.1,
    ("Add-on: SSO",       "Account Access"):    1.6,
    ("Add-on: SSO",       "Onboarding"):        0.5,
}

# ── Spike definitions ─────────────────────────────────────────────────────────
# Each spike fires during a specific calendar month and multiplies the base rate.
# Designed so the MTD monitor would catch them partway through the month.
today = date.today()

def spike_month(months_ago):
    """Return (year, month) for N months before today."""
    m = today.month - months_ago
    y = today.year
    while m <= 0:
        m += 12
        y -= 1
    return (y, m)

SPIKES = [
    # (product, issue_type, year, month, multiplier)
    ("Pro",               "Account Access",    *spike_month(2),  3.8),  # 2 months ago
    ("Starter",           "Billing",           *spike_month(5),  2.9),  # 5 months ago
    ("Business",          "Product / Feature", *spike_month(8),  3.2),  # 8 months ago
    ("Add-on: Analytics", "Product / Feature", *spike_month(1),  4.1),  # last month — still recent
    ("Enterprise",        "Account Access",    *spike_month(11), 2.7),  # 11 months ago
    # Current month spike — this is what the MTD monitor should catch early
    ("Pro",               "Billing",           today.year, today.month, 3.5),
    ("Starter",           "Onboarding",        today.year, today.month, 2.8),
]

def get_spike_multiplier(product, issue, record_date):
    for s_product, s_issue, s_year, s_month, s_mult in SPIKES:
        if (product == s_product and issue == s_issue
                and record_date.year == s_year and record_date.month == s_month):
            return s_mult
    return 1.0

# ── Date range: 20 months ending today ───────────────────────────────────────
end_date   = today
start_date = today - timedelta(days=20 * 30)

# ── Generate rows ─────────────────────────────────────────────────────────────
rows = []
current = start_date

while current <= end_date:
    for product in PRODUCTS:
        for issue in ISSUE_TYPES:
            base       = BASE_RATES[(product, issue)]
            multiplier = get_spike_multiplier(product, issue, current)
            rate       = base * multiplier

            # Poisson-distributed daily count — realistic for issue/event data
            count = int(np.random.poisson(rate))

            rows.append({
                "date":        current.isoformat(),
                "product":     product,
                "issue_type":  issue,
                "issue_count": count,
            })

    current += timedelta(days=1)

# ── Save ──────────────────────────────────────────────────────────────────────
os.makedirs("data", exist_ok=True)
df = pd.DataFrame(rows)
df.to_csv("data/daily_issues.csv", index=False)

print(f"✅  Generated {len(df):,} rows")
print(f"    Date range : {df['date'].min()}  →  {df['date'].max()}")
print(f"    Products   : {df['product'].nunique()}")
print(f"    Issue types: {df['issue_type'].nunique()}")
print(f"\nSample:")
print(df.head(12).to_string(index=False))
