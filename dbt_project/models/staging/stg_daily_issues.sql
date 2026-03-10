-- stg_daily_issues.sql
-- Reads raw CSV, casts types, adds month/day metadata columns
-- Seeds the rest of the pipeline

SELECT
    CAST(date AS DATE)        AS issue_date,
    EXTRACT(year  FROM CAST(date AS DATE)) AS issue_year,
    EXTRACT(month FROM CAST(date AS DATE)) AS issue_month,
    EXTRACT(day   FROM CAST(date AS DATE)) AS issue_day,
    product,
    issue_type,
    CAST(issue_count AS INTEGER) AS issue_count
FROM read_csv_auto('{{ env_var("DBT_DATA_PATH", "../data/daily_issues.csv") }}')
