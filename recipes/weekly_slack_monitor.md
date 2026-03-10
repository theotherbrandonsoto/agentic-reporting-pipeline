---
title: Weekly Compliance Monitor — Slack Alert
schedule: Every Monday at 8:00 AM
---

# Weekly MTD Spike Monitor

Runs the compliance pipeline and posts a Slack alert flagging any
issue spikes detected month-to-date. Stakeholders see problems
early — before the monthly report lands.

## Steps

**1. Go to the project folder**
```
cd ~/projects/compliance-monitor
```

**2. Activate the environment**
```
source venv/bin/activate
```

**3. Generate fresh issue data**
```
python scripts/generate_reports.py
```

**4. Run spike detection**
```
python scripts/monitor.py
```

**5. Rebuild the data pipeline**
```
cd dbt_project && dbt run --profiles-dir . && cd ..
```

**6. Post to Slack**
```
python scripts/notify_slack.py
```
