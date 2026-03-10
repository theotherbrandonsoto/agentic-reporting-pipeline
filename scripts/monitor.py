"""
monitor.py
----------
Month-to-date compliance spike monitor.

For each product × issue_type combination:
  - Computes issue counts for the first 7 / 14 / 21 / 28 days of the current month
  - Compares against the same window across the prior 18 months
  - Flags spikes using a z-score threshold (default: z >= 2.0)
  - Sends flagged results to Claude for a stakeholder-ready narrative
  - Outputs: data/mtd_analysis.csv, data/spike_narrative.txt
"""

import pandas as pd
import numpy as np
from datetime import date
import anthropic
import os
import json
from dotenv import load_dotenv
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
HISTORY_MONTHS  = 18
Z_THRESHOLD     = 2.0          # flag if current window is 2+ std devs above mean
DATA_PATH       = "data/daily_issues.csv"
ANALYSIS_OUT    = "data/mtd_analysis.csv"
NARRATIVE_OUT   = "data/spike_narrative.txt"

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH, parse_dates=["date"])

today          = date.today()
current_year   = today.year
current_month  = today.month
current_day    = today.day

# MTD windows we care about (cap at current day so we don't look at future days)
WINDOWS = [w for w in [7, 14, 21, 28] if w <= current_day]
if not WINDOWS:
    WINDOWS = [current_day]   # early in the month — use whatever days we have

print(f"📅  Today: {today}  |  Day {current_day} of month")
print(f"📊  Active MTD windows:\n")

for window in WINDOWS:
    print(f"  Day 1–{window} comparisons:")
    # Current month
    print(f"    Current : {today.strftime('%B')} 1–{window}")
    # Historical months
    hist_labels = []
    for i in range(1, HISTORY_MONTHS + 1):
        m = current_month - i
        y = current_year
        while m <= 0:
            m += 12
            y -= 1
        from datetime import date as d
        label = d(y, m, 1).strftime("%B %Y")
        hist_labels.append(f"{label} 1–{window}")
    print(f"    History : {', '.join(hist_labels)}\n")

# ── Helper: sum issues in first N days of a given year/month ──────────────────
def window_sum(data, year, month, window_days):
    mask = (
        (data["date"].dt.year  == year)  &
        (data["date"].dt.month == month) &
        (data["date"].dt.day   <= window_days)
    )
    return data.loc[mask, "issue_count"].sum()

# ── Build historical window matrix ────────────────────────────────────────────
# For each (product, issue_type, window) → list of counts from past 18 months
combos = df[["product", "issue_type"]].drop_duplicates().values.tolist()

records = []

for product, issue in combos:
    subset = df[(df["product"] == product) & (df["issue_type"] == issue)]

    for window in WINDOWS:
        # Current MTD count
        current_count = window_sum(subset, current_year, current_month, window)

        # Historical counts for same window across last 18 months
        hist_counts = []
        for i in range(1, HISTORY_MONTHS + 1):
            m = current_month - i
            y = current_year
            while m <= 0:
                m += 12
                y -= 1
            hist_counts.append(window_sum(subset, y, m, window))

        hist_mean = np.mean(hist_counts)
        hist_std  = np.std(hist_counts, ddof=1) if len(hist_counts) > 1 else 0

        # Z-score (how many std devs above historical mean is this month?)
        if hist_std > 0:
            z_score = (current_count - hist_mean) / hist_std
        else:
            z_score = 0.0

        pct_above_mean = ((current_count - hist_mean) / hist_mean * 100) if hist_mean > 0 else 0

        records.append({
            "product":         product,
            "issue_type":      issue,
            "window_days":     window,
            "current_count":   current_count,
            "hist_mean":       round(hist_mean, 2),
            "hist_std":        round(hist_std, 2),
            "z_score":         round(z_score, 2),
            "pct_above_mean":  round(pct_above_mean, 1),
            "is_spike":        z_score >= Z_THRESHOLD,
        })

results = pd.DataFrame(records)
results.to_csv(ANALYSIS_OUT, index=False)
print(f"✅  MTD analysis written → {ANALYSIS_OUT}")

# ── Surface the spikes ────────────────────────────────────────────────────────
spikes = results[results["is_spike"]].sort_values("z_score", ascending=False)

if spikes.empty:
    print("\n✅  No spikes detected across any window.")
else:
    print(f"\n🚨  {len(spikes)} spike(s) detected (z ≥ {Z_THRESHOLD}):\n")
    print(spikes[["product","issue_type","window_days","current_count",
                  "hist_mean","z_score","pct_above_mean"]].to_string(index=False))

# ── Claude narrative ───────────────────────────────────────────────────────────
print("\n🤖  Generating stakeholder narrative via Claude...\n")

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Summarise spikes for the prompt
if spikes.empty:
    spike_summary = "No statistically significant spikes detected this month."
else:
    spike_lines = []
    for _, row in spikes.iterrows():
        spike_lines.append(
            f"- {row['product']} / {row['issue_type']}: "
            f"{int(row['current_count'])} issues in first {int(row['window_days'])} days "
            f"vs. 18-month avg of {row['hist_mean']} "
            f"(z={row['z_score']}, {row['pct_above_mean']}% above mean)"
        )
    spike_summary = "\n".join(spike_lines)

# Also include top 5 non-spike combos for context
top_normal = (
    results[~results["is_spike"]]
    .sort_values("current_count", ascending=False)
    .head(5)
)
normal_lines = []
for _, row in top_normal.iterrows():
    normal_lines.append(
        f"- {row['product']} / {row['issue_type']}: "
        f"{int(row['current_count'])} issues in first {int(max(WINDOWS))} days (within normal range)"
    )
normal_summary = "\n".join(normal_lines)

prompt = f"""You are a senior compliance analyst preparing a month-to-date briefing for a SaaS company's stakeholders.

Today is {today}. We are {current_day} days into the month.

The following compliance issues have been flagged as statistically significant spikes
(current month-to-date count is 2+ standard deviations above the 18-month historical average
for the same point in the month):

SPIKES DETECTED:
{spike_summary}

FOR CONTEXT — top-volume categories currently within normal range:
{normal_summary}

Write a concise stakeholder briefing (5–7 sentences) that:
1. Opens with the overall MTD compliance picture
2. Calls out each spike clearly — product, issue type, and how abnormal it is
3. Notes what is within normal range for reassurance
4. Closes with a recommended action or watch item for the team

Write in the voice of a senior operator presenting to a VP of Customer Success or Chief Compliance Officer.
Be direct but measured — avoid alarming or inflammatory language. Use specific numbers."""

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=600,
    messages=[{"role": "user", "content": prompt}]
)

narrative = message.content[0].text

print("── Stakeholder Narrative ──────────────────────────────────────────────")
print(narrative)
print("───────────────────────────────────────────────────────────────────────\n")

os.makedirs("data", exist_ok=True)
with open(NARRATIVE_OUT, "w") as f:
    f.write(f"Compliance MTD Monitor — {today}\n")
    f.write("=" * 60 + "\n\n")
    f.write(narrative)
    f.write("\n\n")
    f.write("── Raw Spike Data ──\n")
    f.write(spikes.to_string(index=False) if not spikes.empty else "No spikes detected.")

print(f"✅  Narrative saved → {NARRATIVE_OUT}")
