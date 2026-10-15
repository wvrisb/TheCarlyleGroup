-- 01_staging.sql: raw CSVs -> cleaned dimension and fact tables (the star schema).
-- Dialect: standard SQL as run by SQLite 3.25+ (window functions). Runs unchanged on DuckDB
-- except date arithmetic (date(x, '+60 days') -> x + INTERVAL 60 DAY).
-- Inputs (loaded as text by src/run_sql.py): raw_events, raw_firms, raw_attendees, raw_meetings,
-- raw_stages, and params(as_of, window_days).
-- Cleaning rules match src/build_model.py; IDs refer to docs/data_quality.md.

DROP TABLE IF EXISTS dim_event;
CREATE TABLE dim_event AS
SELECT event_id, event_name, event_date, event_type, location, CAST(cost_usd AS REAL) AS cost_usd
FROM raw_events;

DROP TABLE IF EXISTS dim_firm;
CREATE TABLE dim_firm AS
SELECT firm_id, firm_name, segment, priority,
       CAST(historical_commitments_usd AS REAL) AS historical_commitments_usd, coverage_region
FROM raw_firms;

-- Attendance: drop the exact duplicate row (A0011) and the contact with no firm (A9998),
-- then roll contacts up to one row per firm per event.
DROP TABLE IF EXISTS fact_attendance;
CREATE TABLE fact_attendance AS
WITH contacts AS (
    SELECT DISTINCT attendance_id, event_id, firm_id, contact_name, contact_title, attendance_status
    FROM raw_attendees
    WHERE NULLIF(firm_id, '') IS NOT NULL
)
SELECT event_id, firm_id,
       COUNT(*)                                                         AS contacts,
       SUM(attendance_status = 'Confirmed')                             AS confirmed_contacts,
       SUM(contact_title IN ('CIO', 'Managing Director'))               AS senior_contacts,
       MAX(contact_title = 'CIO')                                       AS cio_present,
       CASE WHEN SUM(attendance_status = 'Confirmed') > 0
            THEN 'Attended (Confirmed)' ELSE 'Tentative only' END       AS attendance_group
FROM contacts
GROUP BY event_id, firm_id;

-- Meetings: all rows kept, including the same-day pair for F007.
DROP TABLE IF EXISTS fact_meeting;
CREATE TABLE fact_meeting AS
SELECT meeting_id, firm_id, meeting_date, meeting_type, internal_attendee, purpose
FROM raw_meetings;

-- Opportunity stages: drop the duplicate commitment O9999; stages dated after the as-of date are
-- forecasts, not outcomes; repeated stages keep the first date the stage was reached.
DROP TABLE IF EXISTS fact_opp_stage;
CREATE TABLE fact_opp_stage AS
SELECT opportunity_id, firm_id, fund_name, MIN(created_date) AS created_date, stage,
       MIN(stage_date) AS stage_date, MAX(CAST(opportunity_amount_usd AS REAL)) AS amount_usd,
       CASE stage WHEN 'Initial Conversation' THEN 1 WHEN 'Follow-up / VDR' THEN 2
                  WHEN 'Due Diligence' THEN 3 WHEN 'IC / Documentation' THEN 4 ELSE 5 END AS stage_ord
FROM raw_stages
WHERE opportunity_id <> 'O9999'
  AND stage_date <= (SELECT as_of FROM params)
GROUP BY opportunity_id, firm_id, fund_name, stage;

-- One row per opportunity: current stage = the latest stage reached; flags for the review cases.
DROP TABLE IF EXISTS dim_opportunity;
CREATE TABLE dim_opportunity AS
WITH ranked AS (
    SELECT s.*, ROW_NUMBER() OVER (PARTITION BY opportunity_id ORDER BY stage_date DESC, stage_ord DESC) AS rn,
           MAX(stage_ord) OVER (PARTITION BY opportunity_id)                                           AS max_stage_ord,
           MAX(stage = 'Committed') OVER (PARTITION BY opportunity_id)                                 AS has_commit,
           MAX(stage = 'Due Diligence') OVER (PARTITION BY opportunity_id)                             AS has_dd
    FROM fact_opp_stage s
)
SELECT opportunity_id, firm_id, fund_name, created_date, amount_usd, max_stage_ord,
       stage                          AS current_stage,
       stage_date                     AS current_stage_date,
       opportunity_id = 'O0017'       AS flag_outlier,          -- $650M, unverified (kept; every $ view can exclude it)
       opportunity_id = 'O9998'       AS flag_low_confidence,   -- surviving record of the duplicated pair
       has_commit = 1 AND has_dd = 0  AS flag_skipped_diligence
FROM ranked
WHERE rn = 1;
