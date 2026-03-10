"""
notify.py
---------
Reads the spike narrative and MTD analysis from monitor.py output,
then posts a formatted compliance alert to a Slack webhook.

Usage:
    python scripts/notify.py

Requires:
    SLACK_WEBHOOK_URL in .env
"""

import os
import json
import urllib.request
import urllib.error
import pandas as pd
from datetime import date
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
NARRATIVE_PATH    = "data/spike_narrative.txt"
ANALYSIS_PATH     = "data/mtd_analysis.csv"

def load_narrative():
    if not os.path.exists(NARRATIVE_PATH):
        return "No narrative found — run monitor.py first."
    with open(NARRATIVE_PATH) as f:
        content = f.read()
    # Strip the header and raw spike data — just the narrative paragraph
    lines = content.split("\n")
    narrative_lines = []
    for line in lines:
        if line.startswith("── Raw Spike Data"):
            break
        if not line.startswith("Compliance MTD") and not line.startswith("="):
            narrative_lines.append(line)
    return "\n".join(narrative_lines).strip()

def load_spikes():
    if not os.path.exists(ANALYSIS_PATH):
        return pd.DataFrame()
    df = pd.read_csv(ANALYSIS_PATH)
    return df[df["is_spike"] == True].sort_values("z_score", ascending=False)

def severity_emoji(z_score):
    if z_score >= 5:  return "🔴"
    if z_score >= 3:  return "🟠"
    return "🟡"

def build_slack_payload(narrative, spikes):
    today     = date.today()
    day_of_mo = today.day

    # ── Header block ──────────────────────────────────────────────────────────
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📋 Compliance MTD Monitor — {today.strftime('%B %d, %Y')}",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Day *{day_of_mo}* of month  |  Automated report via compliance-monitor"
                }
            ]
        },
        {"type": "divider"},
    ]

    # ── Spike summary ─────────────────────────────────────────────────────────
    if spikes.empty:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅  *No spikes detected.* All product/issue combinations are within normal historical ranges."
            }
        })
    else:
        spike_lines = [f"*{len(spikes)} spike(s) detected this month:*\n"]
        for _, row in spikes.iterrows():
            emoji = severity_emoji(row["z_score"])
            spike_lines.append(
                f"{emoji}  *{row['product']}  /  {row['issue_type']}*\n"
                f"       {int(row['current_count'])} issues in first {int(row['window_days'])} days  "
                f"vs. {row['hist_mean']} historical avg  "
                f"(z={row['z_score']},  {row['pct_above_mean']}% above mean)"
            )

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(spike_lines)}
        })

    # ── Narrative ─────────────────────────────────────────────────────────────
    blocks += [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Analyst Briefing:*\n{narrative}"
            }
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "🔴 z ≥ 5  |  🟠 z ≥ 3  |  🟡 z ≥ 2   |   Powered by compliance-monitor + Claude API"
                }
            ]
        }
    ]

    return {"blocks": blocks}

def send_to_slack(payload):
    if not SLACK_WEBHOOK_URL:
        raise ValueError(
            "SLACK_WEBHOOK_URL not set. Add it to your .env file.\n"
            "Get one at: https://api.slack.com/messaging/webhooks"
        )

    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")

if __name__ == "__main__":
    print("📤  Loading report data...")
    narrative = load_narrative()
    spikes    = load_spikes()

    print(f"    Spikes found : {len(spikes)}")
    print(f"    Narrative    : {narrative[:80]}...")

    print("\n📦  Building Slack payload...")
    payload = build_slack_payload(narrative, spikes)

    print("🚀  Sending to Slack...")
    try:
        result = send_to_slack(payload)
        print(f"✅  Slack notified successfully ({result})")
    except ValueError as e:
        print(f"⚠️   Config error: {e}")
    except urllib.error.HTTPError as e:
        print(f"❌  Slack returned error {e.code}: {e.read().decode()}")
