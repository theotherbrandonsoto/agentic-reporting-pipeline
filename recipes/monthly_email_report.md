---
title: Monthly Compliance Report — Email
schedule: 1st of each month at 7:00 AM
---

# Monthly Full Compliance Report

Runs the full compliance pipeline and sends a formatted HTML email
with the complete month's spike analysis and AI-generated narrative
to all configured recipients.

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

**6. Send the monthly email**
```
python scripts/notify_email.py
```
