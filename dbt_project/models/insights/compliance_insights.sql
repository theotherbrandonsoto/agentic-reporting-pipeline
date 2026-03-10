-- compliance_insights.sql
-- Joins MTD analysis results (from monitor.py) back to the monthly facts
-- to produce a dashboard-ready insights layer with spike flags and historical context

WITH monthly AS (
    SELECT * FROM {{ ref('fct_monthly_issues') }}
),

-- Pull in spike detection results from monitor.py output
mtd_analysis AS (
    SELECT
        product,
        issue_type,
        window_days,
        current_count,
        hist_mean,
        hist_std,
        z_score,
        pct_above_mean,
        is_spike
    FROM read_csv_auto('../data/mtd_analysis.csv')
),

-- 18-month historical averages per product/issue for trending charts
hist_averages AS (
    SELECT
        product,
        issue_type,
        ROUND(AVG(total_issues), 2)       AS avg_monthly_issues,
        ROUND(STDDEV(total_issues), 2)    AS stddev_monthly_issues,
        MAX(total_issues)                  AS max_monthly_issues,
        MIN(total_issues)                  AS min_monthly_issues
    FROM monthly
    -- Exclude current month from historical baseline
    WHERE NOT (issue_year = EXTRACT(year FROM CURRENT_DATE)
               AND issue_month = EXTRACT(month FROM CURRENT_DATE))
    GROUP BY 1, 2
)

SELECT
    m.issue_year,
    m.issue_month,
    m.month_label,
    m.product,
    m.issue_type,
    m.total_issues,
    m.issues_day_01_07,
    m.issues_day_01_14,
    m.issues_day_01_21,
    m.issues_day_01_28,

    -- Historical context
    h.avg_monthly_issues,
    h.stddev_monthly_issues,
    h.max_monthly_issues,
    h.min_monthly_issues,

    -- Spike flags from MTD monitor (joined on best available window)
    mtd.z_score,
    mtd.pct_above_mean,
    COALESCE(mtd.is_spike, FALSE) AS is_current_spike,

    -- Derived: is this month above historical average?
    CASE
        WHEN m.total_issues > h.avg_monthly_issues + h.stddev_monthly_issues THEN TRUE
        ELSE FALSE
    END AS is_above_1std

FROM monthly m
LEFT JOIN hist_averages h
    ON m.product = h.product AND m.issue_type = h.issue_type
LEFT JOIN mtd_analysis mtd
    ON m.product = mtd.product
    AND m.issue_type = mtd.issue_type
    AND m.issue_year  = EXTRACT(year  FROM CURRENT_DATE)
    AND m.issue_month = EXTRACT(month FROM CURRENT_DATE)

ORDER BY m.issue_year DESC, m.issue_month DESC, m.product, m.issue_type
