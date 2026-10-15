# Data Profiling & Data-Quality Log

All checks are reproducible with `python src/profile_data.py`. Metric definitions are in [`metric_definitions.md`](metric_definitions.md).
Analysis "as-of" date: **2026-10-14** (submission week). Anything dated later is treated as future-dated.

## 1. What the data looks like

| Table | Rows | Grain | Coverage |
|---|---|---|---|
| events | 3 | one event | E001 Global Alternatives Summit (NY, 2026-03-12, $420K) · E002 Investor Leadership Dinner (London, 2026-05-21, $185K) · E003 Private Markets Forum (Berlin, 2026-06-16, $610K). Total spend $1.215M |
| firms | 60 | one firm | 6 segments, Tier 1/2/3 (17/28/15), 3 regions |
| event_attendees | 131 | one contact at one event | 50 distinct firms; 79 firm–event pairs |
| meetings | 112 | one meeting | 44 firms; 2025-12-27 → 2026-09-07 |
| opportunity_stage_history | 358 | one stage change | 107 opportunities across 50 firms; created 2026-01-02 → 2026-08-12 |

All `firm_id` values join cleanly to `firms`. No orphan keys apart from the one blank row below.

## 2. Issues found, and how each is handled

Severity: **High** = changes a headline number; **Medium** = changes a metric at the margin; **Low** = hygiene.

### Attendance

| # | Issue | Evidence | Severity | Decision |
|---|---|---|---|---|
| A1 | Exact duplicate row | `A0011` (E001, F002, Contact 011) appears twice | Low | Drop the duplicate. Contact count for E001 goes from 54 to 53 |
| A2 | Attendee with no firm | `A9998`, "Unmapped Contact", E003, firm_id blank | Low | Exclude from firm-level analysis (listed in the dashboard's data-quality log). Non-standard ID suggests a manual/test entry |
| A3 | "Tentative" status is ambiguous | 34 of 131 rows are Tentative. We cannot tell if they showed up. At firm level, 9 firm–event pairs are Tentative only | Medium | Firm counts as **attended** if any contact is Confirmed. Tentative-only firms form a separate group; a dashboard toggle counts them as attended instead, as a sensitivity check |
| A4 | Attendance is contact-level, outcomes are firm-level | Several contacts per firm per event | Design | Roll up to one row per firm–event, keeping contact count and seniority (e.g. CIO present) as attributes |

### Meetings

| # | Issue | Evidence | Severity | Decision |
|---|---|---|---|---|
| M1 | **Meetings are only logged for firms that attended an event** | All 44 meeting firms are on an attendee list; the 10 never-attending firms have 0 meetings but 24 opportunities | **High** | Meeting data cannot be used to compare attendees vs. non-attendees: the absence of meetings is a logging gap, not an outcome. Meetings are used for **before/after comparisons within attending firms**, and against **similar firms not at the event**: firms that attended a *different* event (the only other firms whose meetings are logged), measured over the same weeks |
| M2 | Two meetings, same firm, same day | F007 on 2026-05-30 (M0054 Due diligence, M0056 Fundraising) | Low | Keep both: different purpose and channel, plausibly two real touchpoints. Follow-up is measured as "at least one meeting", so the pair does not inflate any rate |
| M3 | Meetings stop early | Last meeting 2026-09-07, while opportunity stages run to November | Medium | Post-event meeting windows are capped at 90 days, so the latest window (E003 + 90 days = 2026-09-14) is almost fully covered |
| M4 | **Some meetings are not logged** | 4 of 37 attending firms whose deals moved past the first stage have no meeting logged at all (F016, F045, F056, F060); F045's deal reached investment committee with none | Medium | "No meeting logged" is treated as a gap to confirm, not proof of no contact: the call list says to check the client database first. Reproduce: `logging_gap` in `output/insights.json` |

### Opportunities

| # | Issue | Evidence | Severity | Decision |
|---|---|---|---|---|
| O1 | **One deal dominates committed capital** | `O0017`, F041, $650M Credit Strategy, committed 2026-05-16. This is 53% of the raw $1,223M committed (55% of the $1,178M after cleaning), 6.5× the firm's lifetime commitments ($100M), and it skipped Due Diligence. **F041 never attended an event** | **High** | Keep it (it is not provably wrong), but report every $ metric **with and without O0017** (dashboard toggle) and flag it for source verification. It has no event association either way |
| O2 | Test/duplicate committed records | `O9998` and `O9999`: identical F008 Fund Beta, $25M, created 2026-06-18, a single "Committed" row with no prior stages, non-standard IDs. F008's lifetime commitments are $20M | **High** | Treat as one duplicated, low-confidence record: keep one and flag it (marked * wherever it is counted). Without this, F008 (an E002 attendee) would be credited with $50M post-event |
| O3 | Future-dated stage changes | 5 rows dated after 2026-10-14 (O0037, O0048 "Committed"; O0072 IC rows to 2026-11-19) | Medium | Treat as **planned, not achieved**. Stages are counted only if stage_date ≤ as-of date. O0037 and O0048 drop from Committed to their last real stage |
| O4 | Repeated stage entries | 13 opportunities log "IC / Documentation" twice on different dates | Low | Treat as a status refresh. Use the **first** date a stage was reached for progression timing |
| O5 | Stages skipped | 8 opportunities go Follow-up/VDR → Committed with no Due Diligence or IC (O0002, O0003, O0006, O0017, O0023, O0040, O0070, O0098) | Medium | Keep: could be re-ups or fast-track. Flag them; "furthest stage reached" logic handles them without error |
| O6 | Small-ticket amounts stored differently | All $1.5M and $2.5M amounts are stored as floats (`1500000.0`), every other amount as integers. This hints at a different source or manual entry | Low | Values are plausible, so keep them as-is and cast all amounts to a single numeric type |
| O7 | Amount never changes over an opportunity's life | No opportunity has more than one amount | Design | "Pipeline $" = opportunity amount (it is a target size, not probability-weighted). Note: we cannot see deals growing or shrinking |
| O8 | Multiple opportunities per firm–fund | 16 firm–fund pairs have 2–3 opportunities (e.g. F041 Credit Strategy ×3) | Low | Treat as distinct opportunities (e.g. separate tranches); IDs and dates differ |
| O9 | `created_date` precedes first stage by 5–30 days | Every opportunity | Design | Use `created_date` as "opportunity opened" for event attribution; use stage dates for progression |

### Firms

| # | Issue | Evidence | Severity | Decision |
|---|---|---|---|---|
| F1 | Zero historical commitments | F007, F055 at $0 | Low | Valid: treat as new relationships. Useful for a "new-logo" cut |
| F2 | `historical_commitments_usd` is a bucketed number | Only 10 distinct values ($0–$250M) | Low | Use it as a relationship-size band, not a precise figure |

## 3. Structural limits on what the data can prove

These are not errors, but they shape what the analysis can honestly claim:

1. **Three events, 47 attending firms (50 counting Tentative-only).** Every event-level comparison is n=3. Differences between events are directional, not statistically significant.
2. **Attendance is not random.** Invited firms differ from non-invited ones. Here the never-invited firms were already far more active before each event (50% opened a deal in the prior 60 days vs 27% of attendees), so raw attendee-vs-non-attendee comparisons mislead; the analysis compares each group's change from its own baseline instead.
3. **Firms attend more than one event.** 21 firms attended more than one event (19 attended two, 2 attended all three; 24 counting Tentative RSVPs). Their outcomes overlap in time, so the same opportunity could be "associated" with more than one event. The model assigns each outcome to the **most recent prior event attended**. Only 2 of 30 new deals fall in two windows, and first-touch or split credit changes no conclusion (Methods tab of the dashboard).
4. **Comparisons are limited by logging.** Because of M1, opportunities are the only outcome observed for never-invited firms; for meetings, the comparison is with similar firms not at the event: firms that attended a different event and had no event of their own within the window (firms in their own post-event period are left out, because their follow-up inflates the "before" period). That leaves a small group (13 → 21 meetings at 60 days).
5. **No meeting-to-opportunity link.** Meetings and opportunities share only firm_id, so we cannot tell which meeting drove which deal.

## 4. Impact on headline numbers

| Metric | Raw | After cleaning | Without O0017 |
|---|---|---|---|
| Opportunities | 107 | 106 (O9998/9 merged) | 105 |
| Committed opportunities | 17 | 14 (−1 duplicate, −2 future-dated) | 13 |
| Committed $ | $1,223M | $1,178M | $528M |

The committed-dollar headline moves by more than half depending on how one unverified record is treated. That is the single most important caveat for leadership.
