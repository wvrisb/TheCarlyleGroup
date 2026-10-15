-- 03_kpis.sql: the headline metrics, as tables. Each matches a figure in output/insights.json
-- (checked by src/run_sql.py) and in the dashboard. Window and as-of date come from params.

-- Follow-up: share of attending firm-event pairs with a meeting after vs before the event
DROP TABLE IF EXISTS kpi_followup;
CREATE TABLE kpi_followup AS
SELECT COUNT(*)                                        AS attendances,
       COUNT(DISTINCT firm_id)                         AS firms_attended,
       (SELECT COUNT(*) FROM dim_firm)                 AS firms_in_book,
       (SELECT SUM(cost_usd) FROM dim_event)           AS spend_usd,
       AVG(meetings_pre > 0)                           AS baseline_rate,
       AVG(meetings_post > 0)                          AS followup_rate
FROM firm_event_outcomes WHERE attended;

-- Tier 1 firms not met within the window after at least one event they attended
DROP TABLE IF EXISTS kpi_tier1;
CREATE TABLE kpi_tier1 AS
SELECT COUNT(DISTINCT o.firm_id)                                         AS tier1_firms,
       COUNT(DISTINCT CASE WHEN o.meetings_post = 0 THEN o.firm_id END)  AS tier1_firms_missed
FROM firm_event_outcomes o JOIN dim_firm f USING (firm_id)
WHERE o.attended AND f.priority = 'Tier 1';

-- Seasonality check. Comparison group for event X = firms that attended a different event and had
-- no attended event of their own within the window of X (their own follow-up would inflate "before").
DROP TABLE IF EXISTS comparison_pairs;
CREATE TABLE comparison_pairs AS
SELECT o.event_id, o.firm_id, o.meetings_pre, o.meetings_post,
       CASE WHEN o.attended THEN 'attended'
            WHEN NOT EXISTS (SELECT 1 FROM attended a JOIN dim_event e ON e.event_id = o.event_id
                              WHERE a.firm_id = o.firm_id
                                AND ABS(julianday(a.event_date) - julianday(e.event_date)) <= (SELECT window_days FROM params))
            THEN 'comparison' ELSE 'overlap' END AS grp
FROM firm_event_outcomes o
WHERE o.firm_id IN (SELECT firm_id FROM attended);

DROP TABLE IF EXISTS kpi_comparison;
CREATE TABLE kpi_comparison AS
SELECT grp, COUNT(*) AS pairs, SUM(meetings_pre) AS meetings_before, SUM(meetings_post) AS meetings_after,
       AVG(meetings_pre > 0) AS share_met_before, AVG(meetings_post > 0) AS share_met_after
FROM comparison_pairs GROUP BY grp;

-- New deals: share of firm-event pairs opening a deal before vs after, by group
DROP TABLE IF EXISTS kpi_new_deal_groups;
CREATE TABLE kpi_new_deal_groups AS
SELECT CASE WHEN o.attended THEN 'attended'
            WHEN o.firm_id IN (SELECT firm_id FROM attended) THEN 'other_event'
            WHEN o.firm_id NOT IN (SELECT firm_id FROM fact_attendance) THEN 'never_invited'
            ELSE 'tentative_only' END                       AS grp,
       COUNT(*) AS pairs, AVG(opps_created_pre > 0) AS share_before, AVG(opps_created_post > 0) AS share_after
FROM firm_event_outcomes o GROUP BY 1;

-- Event scorecard, including extra firms met beyond the season (needs >= 5 comparison firms)
DROP TABLE IF EXISTS kpi_event_scorecard;
CREATE TABLE kpi_event_scorecard AS
WITH a AS (
    SELECT event_id, COUNT(*) AS firms, SUM(meetings_post > 0) AS met_after, SUM(meetings_pre > 0) AS met_before
    FROM firm_event_outcomes WHERE attended GROUP BY event_id),
c AS (
    SELECT event_id, COUNT(*) AS cmp_firms, AVG(meetings_pre > 0) AS cmp_before, AVG(meetings_post > 0) AS cmp_after
    FROM comparison_pairs WHERE grp = 'comparison' GROUP BY event_id),
d AS (SELECT credited_event AS event_id, COUNT(*) AS new_deals FROM opp_credit WHERE credited_event IS NOT NULL GROUP BY 1),
s AS (
    SELECT e.event_id, e.cost_usd, a.firms, a.met_after, a.met_before, a.met_after - a.met_before AS extra_firms,
           COALESCE(c.cmp_firms, 0) AS cmp_firms, c.cmp_before, c.cmp_after, COALESCE(d.new_deals, 0) AS new_deals,
           CASE WHEN c.cmp_firms >= 5 THEN a.firms * (c.cmp_after - c.cmp_before) END AS seasonal_expected
    FROM dim_event e JOIN a USING (event_id) LEFT JOIN c USING (event_id) LEFT JOIN d USING (event_id))
SELECT s.*, extra_firms - seasonal_expected AS extra_beyond_season,
       CASE WHEN extra_firms - seasonal_expected >= 1 THEN cost_usd / (extra_firms - seasonal_expected) END AS cost_per_extra_beyond_season
FROM s;

-- Where deals came from, and whether they closed; deals of similar age (120-240 days) compared too
DROP TABLE IF EXISTS deal_origin;
CREATE TABLE deal_origin AS
SELECT o.opportunity_id, o.current_stage = 'Committed' AS committed,
       CAST(julianday((SELECT as_of FROM params)) - julianday(o.created_date) AS INTEGER) AS age_days,
       CASE WHEN EXISTS (SELECT 1 FROM attended a WHERE a.firm_id = o.firm_id AND o.created_date >= a.event_date
                           AND o.created_date <= date(a.event_date, '+' || (SELECT window_days FROM params) || ' days')) THEN 'event'
            WHEN o.firm_id NOT IN (SELECT firm_id FROM attended) THEN 'did_not_attend'
            WHEN o.created_date < (SELECT MIN(event_date) FROM attended a WHERE a.firm_id = o.firm_id) THEN 'existing_before'
            ELSE 'later_unlinked' END AS grp
FROM dim_opportunity o;

DROP TABLE IF EXISTS kpi_deal_origin;
CREATE TABLE kpi_deal_origin AS
SELECT grp, COUNT(*) AS deals, SUM(committed) AS committed,
       SUM(age_days >= 120) AS mature_deals, AVG(CASE WHEN age_days >= 120 THEN committed END) AS mature_commit_rate,
       SUM(age_days BETWEEN 120 AND 240) AS similar_age_deals, SUM(CASE WHEN age_days BETWEEN 120 AND 240 THEN committed END) AS similar_age_committed
FROM deal_origin GROUP BY grp;

-- Priority call list: attending firms not met within the window after an event; whether met since (as of)
DROP TABLE IF EXISTS kpi_call_list;
CREATE TABLE kpi_call_list AS
WITH gap AS (
    SELECT o.firm_id, MAX(e.event_date) AS last_missed_event
    FROM firm_event_outcomes o JOIN dim_event e USING (event_id)
    WHERE o.attended AND o.meetings_post = 0 GROUP BY o.firm_id)
SELECT g.firm_id, f.priority, f.segment,
       (SELECT COUNT(*) FROM dim_opportunity d WHERE d.firm_id = g.firm_id AND d.current_stage NOT IN ('Committed', 'Declined')) AS live_deals,
       (SELECT COALESCE(SUM(amount_usd), 0) FROM dim_opportunity d WHERE d.firm_id = g.firm_id AND d.current_stage NOT IN ('Committed', 'Declined')) AS live_usd,
       (SELECT MIN(meeting_date) FROM fact_meeting m WHERE m.firm_id = g.firm_id AND m.meeting_date > g.last_missed_event) AS met_since,
       (SELECT MAX(meeting_date) FROM fact_meeting m WHERE m.firm_id = g.firm_id) AS last_meeting
FROM gap g JOIN dim_firm f USING (firm_id)
ORDER BY met_since IS NOT NULL, live_usd DESC;
