# 📋 Compliance Monitor

An automated compliance reporting pipeline — demonstrating month-to-date spike detection, a multi-layer dbt pipeline, a Claude-powered stakeholder narrative, and Goose-orchestrated delivery via Slack and email.

**Author:** theotherbrandonsoto &nbsp;|&nbsp; [GitHub](https://github.com/theotherbrandonsoto) &nbsp;|&nbsp; [LinkedIn](https://www.linkedin.com/in/hirebrandonsoto/)

> **Part of a connected portfolio.** Products and issue taxonomy match the [metrics-store](https://github.com/theotherbrandonsoto/metrics-store) and [contact_transcript_analysis](https://github.com/theotherbrandonsoto/contact_transcript_analysis) projects, simulating a real multi-system analytics environment.

---

## 🧠 The Problem This Solves

Monthly compliance reports create a recurring blind spot: stakeholders only learn about spikes *after* the month closes. By then it's too late to intervene.

This pipeline solves that by running a weekly MTD monitor that compares the current month's first 7, 14, 21, and 28 days against the same window across the prior 18 months. If something is spiking, stakeholders know about it mid-month — not at month-end.

---

## 🏗️ Architecture

```
generate_reports.py     synthetic daily issue data (products × issue types)
        ↓
monitor.py              MTD spike detection (z-score vs. 18-month history)
        ↓                        + Claude API → stakeholder narrative
dbt pipeline            staging → marts → insights (DuckDB warehouse)
        ↓                    ↓
notify_slack.py         weekly Slack alert
notify_email.py         monthly HTML email report
        ↑___________________________________________↑
              orchestrated by Goose Desktop recipes
```

---

## 📐 dbt Layer Design

| Layer | Model | Purpose |
|---|---|---|
| Staging | `stg_daily_issues` | Reads raw CSV, casts types, adds month/day metadata |
| Marts | `fct_monthly_issues` | Monthly totals + MTD window buckets (day 7/14/21/28) |
| Insights | `compliance_insights` | Enriched with spike flags and 18-month historical averages |

---

## 🔍 Spike Detection Logic

For each product × issue type combination, `monitor.py`:

1. Computes the current month's issue count for each active MTD window (first 7, 14, 21, or 28 days depending on today's date)
2. Pulls the same window count for each of the prior 18 months
3. Calculates a z-score: `(current - historical_mean) / historical_std`
4. Flags any combination where `z ≥ 2.0` as a spike

| Severity | Z-Score | Meaning |
|---|---|---|
| 🔴 CRITICAL | z ≥ 5 | Extreme outlier — escalate immediately |
| 🟠 HIGH | z ≥ 3 | Significant spike — flag for stakeholder review |
| 🟡 ELEVATED | z ≥ 2 | Above normal — monitor closely through month-end |

---

## 🤖 Claude Integration

After spike detection, `monitor.py` sends flagged results to Claude, which generates a 5–7 sentence stakeholder briefing written in the voice of a senior compliance analyst. The narrative calls out each spike by name, provides historical context, and closes with a recommended action.

This is the text that lands in both the Slack post and the monthly email — no manual writing required.

---

## 🦆 Goose Desktop Integration

This project is designed to be orchestrated by [Goose Desktop](https://github.com/block/goose) — an open-source local AI agent by Block. Two saved recipes live in the `recipes/` folder:

| Recipe | Schedule | Delivers |
|---|---|---|
| `weekly_slack_monitor.md` | Every Monday | Slack post with spike flags + narrative |
| `monthly_email_report.md` | 1st of each month | HTML email report to all recipients |

To use: open Goose Desktop → load a recipe file → run on demand or set a schedule.

---

## 🛠️ Tech Stack

| Tool | Role |
|---|---|
| **Python** | Data generation, spike detection, notifications |
| **Claude API** | Stakeholder narrative generation |
| **dbt Core** | Three-layer data transformation pipeline |
| **DuckDB** | Local analytical warehouse |
| **Slack Webhooks** | Weekly MTD alert delivery |
| **Gmail / SMTP** | Monthly email report delivery |
| **Goose Desktop** | Agentic pipeline orchestration |
| **pandas / numpy** | Data manipulation and z-score calculation |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- An [Anthropic account](https://console.anthropic.com) with an API key
- A Slack workspace with [Incoming Webhooks](https://api.slack.com/messaging/webhooks) enabled
- A Gmail account with an [App Password](https://myaccount.google.com/security) configured
- [Goose Desktop](https://github.com/block/goose) installed (for recipe orchestration)

### 1. Clone the repo
```bash
git clone https://github.com/theotherbrandonsoto/compliance-monitor.git
cd compliance-monitor
```

### 2. Set up virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Add credentials
```bash
cp .env.example .env
# Fill in your ANTHROPIC_API_KEY, SLACK_WEBHOOK_URL, GMAIL_SENDER,
# GMAIL_APP_PASSWORD, and GMAIL_RECIPIENTS
```

### 4. Generate the dataset
```bash
python scripts/generate_reports.py
```

### 5. Run spike detection
```bash
python scripts/monitor.py
```

### 6. Rebuild the dbt pipeline
```bash
cd dbt_project
dbt run --profiles-dir .
dbt test --profiles-dir .
cd ..
```

### 7. Send notifications
```bash
# Weekly Slack post
python scripts/notify_slack.py

# Monthly email
python scripts/notify_email.py
```

### 8. Automate with Goose Desktop
Open Goose Desktop and load either recipe from the `recipes/` folder.
Run on demand or configure a recurring schedule.

---

## 📁 Project Structure

```
compliance-monitor/
├── data/
│   ├── daily_issues.csv          ← Generated issue data (gitignored)
│   ├── mtd_analysis.csv          ← Spike detection output (gitignored)
│   ├── spike_narrative.txt       ← Claude narrative output (gitignored)
│   └── compliance_monitor.duckdb ← DuckDB warehouse (gitignored)
├── dbt_project/
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_daily_issues.sql
│   │   │   └── schema.yml
│   │   ├── marts/
│   │   │   ├── fct_monthly_issues.sql
│   │   │   └── schema.yml
│   │   └── insights/
│   │       ├── compliance_insights.sql
│   │       └── schema.yml
│   ├── profiles.yml
│   └── dbt_project.yml
├── scripts/
│   ├── generate_reports.py       ← Synthetic data generation
│   ├── monitor.py                ← MTD spike detection + Claude narrative
│   ├── notify_slack.py           ← Weekly Slack alert
│   └── notify_email.py           ← Monthly HTML email report
├── recipes/
│   ├── weekly_slack_monitor.md   ← Goose recipe: weekly Slack post
│   └── monthly_email_report.md  ← Goose recipe: monthly email
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 💡 Why This Project?

Automated reporting is one of the highest-leverage things a data analyst can build — it turns a recurring manual task into a system that runs itself.

This project demonstrates that end-to-end:

- **Proactive over reactive** — weekly MTD monitoring means stakeholders are never surprised at month-end
- **Statistically grounded** — z-score detection against 18 months of history separates real spikes from noise
- **AI-augmented** — Claude writes the narrative so the output is immediately readable by non-technical stakeholders, no interpretation required
- **Agentic delivery** — Goose Desktop orchestrates the full pipeline on a schedule, no manual steps
- **Connected data model** — taxonomy and products link directly to metrics-store and transcript-analysis, reflecting how real multi-system environments work

---

*Synthetic issue data generated programmatically. Product and taxonomy universe drawn from the metrics-store and transcript-analysis project data models.*
