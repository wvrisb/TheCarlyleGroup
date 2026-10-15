-- 02_firm_event_outcomes.sql: the analysis table, one row per firm x event for the window in params.
-- "Before" = the window_days before the event date; "after" = the event date through window_days after.
-- Attended = at least one contact Confirmed. Matches output/firm_event_outcomes.csv (att_def = 'confirmed').

DROP TABLE IF EXISTS attended;
CREATE TABLE attended AS
SELECT a.event_id, a.firm_id, e.event_date
FROM fact_attendance a JOIN dim_event e USING (event_id)
WHERE a.confirmed_contacts > 0;

DROP TABLE IF EXISTS firm_event;
CREATE TABLE firm_event AS
SELECT e.event_id, e.event_date, f.firm_id,
       date(e.event_date, '-' || p.window_days || ' days') AS before_start,
       date(e.event_date, '+' || p.window_days || ' days') AS after_end
FROM dim_event e CROSS JOIN dim_firm f CROSS JOIN params p;

DROP TABLE IF EXISTS firm_event_outcomes;
CREATE TABLE firm_event_outcomes AS
SELECT fe.event_id, fe.firm_id,
       EXISTS (SELECT 1 FROM attended a WHERE a.event_id = fe.event_id AND a.firm_id = fe.firm_id)       AS attended,
       COALESCE((SELECT attendance_group FROM fact_attendance x
                 WHERE x.event_id = fe.event_id AND x.firm_id = fe.firm_id), 'Not on list')            AS attendance_group,
       (SELECT COUNT(*) FROM fact_meeting m
         WHERE m.firm_id = fe.firm_id AND m.meeting_date >= fe.before_start AND m.meeting_date < fe.event_date) AS meetings_pre,
       (SELECT COUNT(*) FROM fact_meeting m
         WHERE m.firm_id = fe.firm_id AND m.meeting_date >= fe.event_date AND m.meeting_date <= fe.after_end)   AS meetings_post,
       (SELECT CAST(julianday(MIN(m.meeting_date)) - julianday(fe.event_date) AS INTEGER) FROM fact_meeting m
         WHERE m.firm_id = fe.firm_id AND m.meeting_date >= fe.event_date AND m.meeting_date <= fe.after_end)   AS days_to_first_meeting,
       (SELECT COUNT(*) FROM dim_opportunity o
         WHERE o.firm_id = fe.firm_id AND o.created_date >= fe.before_start AND o.created_date < fe.event_date) AS opps_created_pre,
       (SELECT COUNT(*) FROM dim_opportunity o
         WHERE o.firm_id = fe.firm_id AND o.created_date >= fe.event_date AND o.created_date <= fe.after_end)   AS opps_created_post,
       -- existing deals (opened before the event) that reached a later stage in the window
       (SELECT COUNT(DISTINCT s.opportunity_id) FROM fact_opp_stage s JOIN dim_opportunity o USING (opportunity_id)
         WHERE o.firm_id = fe.firm_id AND o.created_date < fe.event_date AND s.stage_ord >= 2 AND s.stage <> 'Declined'
           AND s.stage_date >= fe.event_date AND s.stage_date <= fe.after_end)                                 AS opps_advanced_post
FROM firm_event fe;

-- Credit rule: a new deal is credited to the most recent attended event whose window contains its open date.
DROP TABLE IF EXISTS opp_credit;
CREATE TABLE opp_credit AS
SELECT o.opportunity_id, o.firm_id, o.created_date, o.amount_usd, o.current_stage,
       (SELECT a.event_id FROM attended a
         WHERE a.firm_id = o.firm_id
           AND o.created_date >= a.event_date
           AND o.created_date <= date(a.event_date, '+' || (SELECT window_days FROM params) || ' days')
         ORDER BY a.event_date DESC LIMIT 1)                                                                   AS credited_event
FROM dim_opportunity o;
