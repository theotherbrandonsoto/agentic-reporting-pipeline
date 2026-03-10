-- fct_monthly_issues.sql
-- One row per product / issue_type / year / month
-- Aggregates daily counts into monthly totals and MTD window buckets

WITH daily AS (
    SELECT * FROM {{ ref('stg_daily_issues') }}
),

monthly AS (
    SELECT
        issue_year,
        issue_month,
        product,
        issue_type,

        -- Full month total
        SUM(issue_count) AS total_issues,

        -- MTD window buckets (first N days of month)
        SUM(CASE WHEN issue_day <=  7 THEN issue_count ELSE 0 END) AS issues_day_01_07,
        SUM(CASE WHEN issue_day <= 14 THEN issue_count ELSE 0 END) AS issues_day_01_14,
        SUM(CASE WHEN issue_day <= 21 THEN issue_count ELSE 0 END) AS issues_day_01_21,
        SUM(CASE WHEN issue_day <= 28 THEN issue_count ELSE 0 END) AS issues_day_01_28,

        MIN(issue_date) AS month_start,
        MAX(issue_date) AS month_end_observed
    FROM daily
    GROUP BY 1, 2, 3, 4
)

SELECT
    issue_year,
    issue_month,
    -- Readable month label for charts
    STRFTIME(DATE_TRUNC('month', MAKE_DATE(issue_year::INT, issue_month::INT, 1)), '%b %Y') AS month_label,
    product,
    issue_type,
    total_issues,
    issues_day_01_07,
    issues_day_01_14,
    issues_day_01_21,
    issues_day_01_28,
    month_start,
    month_end_observed
FROM monthly
