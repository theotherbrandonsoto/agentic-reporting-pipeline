"""
notify_email.py
---------------
Sends a formatted monthly compliance report via Gmail.

Reads monitor.py output and sends an HTML email with:
- Spike summary table
- Full AI-generated stakeholder narrative
- Month-over-month context

Requires in .env:
    GMAIL_SENDER=your_address@gmail.com
    GMAIL_APP_PASSWORD=your_16_char_app_password
    GMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com

How to get a Gmail App Password:
    1. Go to myaccount.google.com/security
    2. Enable 2-Step Verification if not already on
    3. Search "App Passwords" → create one for "Mail"
    4. Paste the 16-character password into your .env
"""

import os
import smtplib
import pandas as pd
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

GMAIL_SENDER     = os.environ.get("GMAIL_SENDER")
GMAIL_APP_PW     = os.environ.get("GMAIL_APP_PASSWORD")
GMAIL_RECIPIENTS = os.environ.get("GMAIL_RECIPIENTS", "")
NARRATIVE_PATH   = "data/spike_narrative.txt"
ANALYSIS_PATH    = "data/mtd_analysis.csv"

def load_narrative():
    if not os.path.exists(NARRATIVE_PATH):
        return "No narrative found — run monitor.py first."
    with open(NARRATIVE_PATH) as f:
        content = f.read()
    lines = content.split("\n")
    narrative_lines = []
    for line in lines:
        if line.startswith("── Raw Spike Data"):
            break
        if not line.startswith("Compliance MTD") and not line.startswith("="):
            narrative_lines.append(line)
    return "\n".join(narrative_lines).strip()

def load_analysis():
    if not os.path.exists(ANALYSIS_PATH):
        return pd.DataFrame(), pd.DataFrame()
    df     = pd.read_csv(ANALYSIS_PATH)
    spikes = df[df["is_spike"] == True].sort_values("z_score", ascending=False)
    clean  = df[df["is_spike"] == False].sort_values("current_count", ascending=False).head(6)
    return spikes, clean

def severity_color(z_score):
    if z_score >= 5: return "#dc2626"   # red
    if z_score >= 3: return "#ea580c"   # orange
    return "#ca8a04"                     # yellow

def severity_label(z_score):
    if z_score >= 5: return "CRITICAL"
    if z_score >= 3: return "HIGH"
    return "ELEVATED"

def build_spike_rows(spikes):
    if spikes.empty:
        return """
        <tr>
            <td colspan="5" style="padding:16px;text-align:center;color:#16a34a;font-weight:600;">
                ✅ No spikes detected — all categories within normal range
            </td>
        </tr>"""
    rows = ""
    for _, row in spikes.iterrows():
        color = severity_color(row["z_score"])
        label = severity_label(row["z_score"])
        rows += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
            <td style="padding:12px 16px;font-weight:600;">{row['product']}</td>
            <td style="padding:12px 16px;">{row['issue_type']}</td>
            <td style="padding:12px 16px;text-align:center;">{int(row['current_count'])}</td>
            <td style="padding:12px 16px;text-align:center;">{row['hist_mean']}</td>
            <td style="padding:12px 16px;text-align:center;">
                <span style="background:{color};color:white;padding:3px 10px;
                             border-radius:12px;font-size:11px;font-weight:700;">
                    {label} z={row['z_score']}
                </span>
            </td>
        </tr>"""
    return rows

def build_html(narrative, spikes, clean):
    today        = date.today()
    month_label  = today.strftime("%B %Y")
    spike_count  = len(spikes)
    status_color = "#dc2626" if spike_count > 0 else "#16a34a"
    status_text  = f"{spike_count} spike(s) detected" if spike_count > 0 else "All clear"
    spike_rows   = build_spike_rows(spikes)

    # Narrative — preserve paragraph breaks
    narrative_html = "".join(
        f"<p style='margin:0 0 12px;line-height:1.7;color:#374151;'>{p.strip()}</p>"
        for p in narrative.split("\n") if p.strip()
    )

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:'Helvetica Neue',Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 0;">
    <tr><td align="center">
      <table width="640" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;overflow:hidden;
                    box-shadow:0 1px 3px rgba(0,0,0,0.1);">

        <!-- Header -->
        <tr>
          <td style="background:#1e293b;padding:28px 32px;">
            <p style="margin:0;color:#94a3b8;font-size:12px;text-transform:uppercase;
                      letter-spacing:1px;">Monthly Compliance Report</p>
            <h1 style="margin:6px 0 0;color:#ffffff;font-size:22px;font-weight:700;">
              {month_label}
            </h1>
          </td>
        </tr>

        <!-- Status banner -->
        <tr>
          <td style="background:{status_color};padding:12px 32px;">
            <p style="margin:0;color:#ffffff;font-size:14px;font-weight:600;">
              {status_text}
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px;">

            <!-- Analyst briefing -->
            <h2 style="margin:0 0 16px;font-size:15px;font-weight:700;
                        color:#1e293b;text-transform:uppercase;letter-spacing:0.5px;">
              Analyst Briefing
            </h2>
            <div style="background:#f8fafc;border-left:4px solid #3b82f6;
                        padding:20px 24px;border-radius:0 6px 6px 0;margin-bottom:32px;">
              {narrative_html}
            </div>

            <!-- Spike table -->
            <h2 style="margin:0 0 16px;font-size:15px;font-weight:700;
                        color:#1e293b;text-transform:uppercase;letter-spacing:0.5px;">
              Spike Detection Results
            </h2>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;
                           margin-bottom:32px;font-size:13px;">
              <thead>
                <tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb;">
                  <th style="padding:12px 16px;text-align:left;color:#6b7280;font-weight:600;">Product</th>
                  <th style="padding:12px 16px;text-align:left;color:#6b7280;font-weight:600;">Issue Type</th>
                  <th style="padding:12px 16px;text-align:center;color:#6b7280;font-weight:600;">MTD Count</th>
                  <th style="padding:12px 16px;text-align:center;color:#6b7280;font-weight:600;">Hist. Avg</th>
                  <th style="padding:12px 16px;text-align:center;color:#6b7280;font-weight:600;">Severity</th>
                </tr>
              </thead>
              <tbody>{spike_rows}</tbody>
            </table>

          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;padding:20px 32px;border-top:1px solid #e5e7eb;">
            <p style="margin:0;font-size:12px;color:#9ca3af;">
              Generated by compliance-monitor · Claude API · {today.isoformat()}
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>"""

def send_email(subject, html_body, recipients):
    if not GMAIL_SENDER or not GMAIL_APP_PW:
        raise ValueError(
            "GMAIL_SENDER or GMAIL_APP_PASSWORD not set in .env\n"
            "See script header for setup instructions."
        )
    if not recipients:
        raise ValueError("GMAIL_RECIPIENTS not set in .env")

    recipient_list = [r.strip() for r in recipients.split(",")]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = ", ".join(recipient_list)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_SENDER, GMAIL_APP_PW)
        server.sendmail(GMAIL_SENDER, recipient_list, msg.as_string())

    return recipient_list

if __name__ == "__main__":
    today       = date.today()
    month_label = today.strftime("%B %Y")

    print("📧  Loading report data...")
    narrative        = load_narrative()
    spikes, clean    = load_analysis()
    print(f"    Spikes : {len(spikes)}  |  Clean categories : {len(clean)}")

    print("📝  Building HTML email...")
    html = build_html(narrative, spikes, clean)

    subject = f"Compliance Monthly Report — {month_label} | {len(spikes)} spike(s) detected"

    print("🚀  Sending via Gmail...")
    try:
        sent_to = send_email(subject, html, GMAIL_RECIPIENTS)
        print(f"✅  Email sent to: {', '.join(sent_to)}")
    except ValueError as e:
        print(f"⚠️   Config error: {e}")
    except Exception as e:
        print(f"❌  Send failed: {e}")
