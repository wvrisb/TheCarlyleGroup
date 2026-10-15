# Metric definitions

Every metric in the dashboard and the readout, in plain language and as computed.
Code: `src/build_model.py` (firm × event table), `src/analysis.py` (insights), the same model in SQL (`sql/`, checked against Python by `src/run_sql.py`), and the dashboard's own JavaScript (same rules, recomputed live for filters; `src/check_dashboard.py` confirms it agrees).

**Default settings:** 60-day window · attended = any contact Confirmed · all firms · $650M deal included · as of 14 Oct 2026.

## Building blocks

| Term | Definition |
|---|---|
| **Attended** | A firm attended an event if at least one of its contacts on that event's list is `Confirmed`. Firms whose contacts are all `Tentative` are a separate group ("Tentative only"). A toggle counts them as attended. |
| **Window** | The days after an event in which outcomes are linked to it: 60 by default, 30 and 90 as checks. "Before" uses the same number of days ending the day before the event. The event day itself counts as "after". |
| **Why 60 days** | Measured from each event, the median attending firm's first meeting came 29 days later; 60 days captures 79% of first follow-ups (30 days: 51%; 90 days: 96%). London and Berlin were 26 days apart, so 90 days mixes events. A typical deal commits about 53 days after it opens. |
| **Credit rule** | When an outcome falls in the windows of two events a firm attended, it is credited to the most recent one. Only 2 of 30 new deals are affected; first-touch or split credit changes no conclusion. |
| **Firms not at the event** | Similar firms we compare with. For each event: firms that attended one of the other two events but not this one, and had no event of their own within the window. Their meetings are logged (only attending firms have meeting records) and we count them over the same weeks. Some months are busier than others whatever we do, so their change shows what would have happened without the event. Firms whose own event fell inside the window are left out, because their own follow-up inflates the "before" period. Used for meetings only; the new-deal comparison uses all firms at other events. |
| **Never invited** | Firms on no attendee list for any event (10 firms). Used only for deal outcomes, since their meetings are not logged. |
| **Open deal** | A deal opened before the event date that had not committed or been declined by then. |
| **Mature deal** | A deal opened at least 120 days before 14 Oct 2026, so it has had time to commit. |
| **Deal size ($)** | A deal's target amount. Never changes over a deal's life and is not probability-weighted: scale, not expected value. |
| **Priority tier** | Investor Relations' own Tier 1–3 label. Not defined in the data, and Tier 1 firms are not larger by past commitments, so read it as Investor Relations' stated priority. |

## KPIs, from reach to capital

| Tier | Metric | Definition | Default value |
|---|---|---|---|
| Reach | Firms attended | Distinct firms with at least one attended event | 47 of 60 (78%) |
| Reach | Tier 1 firms attended | Distinct Tier 1 firms with at least one attended event | 13 |
| Follow-up | **Follow-up rate** | Attending firm-event pairs with at least one meeting within the window ÷ attending pairs | 60% (42 of 70) |
| Follow-up | Before-event baseline | Same pairs with at least one meeting in the window before the event | 43% |
| Follow-up | Average days to first meeting | Mean days from event to the firm's first meeting within the window | New York 27 · London 19 · Berlin 23 |
| Follow-up | Tier 1 firms not met in time | Distinct Tier 1 firms with at least one attended event and no meeting within the window after it | 10 of 13 (30 days: 11 · 90 days: 4) |
| Follow-up | Firms met, attending versus firms not at the event | Share of firm-event pairs with at least one meeting in the window before versus the window after: attending firms versus firms not at the event, pooled over the three events | attending 43% (before) → 60% (after) · not at the event 26% → 41% |
| Follow-up | Where follow-up went | Team meetings in the window after each event, and how many were with that event's attendees versus the attendees of an event held within the window before | New York 21 of 29 · London 31 of 51 · Berlin 11 of 31 (15 with London attendees) |
| Follow-up | Meeting growth versus firms not at the event | Meetings in the window after ÷ before, minus 1: attending firms versus firms not at the event | +54% versus +62% overall; London +158% versus +33% |
| Deals | New deals after an event | Opportunities created within the window after an event the firm attended (credited per the rule above) | 30 ($1.40B target) |
| Deals | Existing deals moved forward | Opportunities created before the event that reached a new stage (not Declined) within the window | 23 |
| Deals | Change in firms opening a deal | Share of firm-event pairs with a new opportunity, after minus before, by group. Changes are shown as the difference of the rounded percentages, so they match the shares beside them | attending 27% → 33% (+6 points) · firms at other events 32% → 44% (+12) · never invited −3 |
| Deals | Open deals moved forward | Among attending pairs with a open deal: share where a deal moved to a later stage, followed up versus not | 59% versus 50% (17 versus 14) |
| Outcome | Event-sourced deals committed | New deals after an event whose current stage is Committed (as of 14 Oct) | 3 ($250M; one is the low-confidence O9998) |
| Outcome | Commit rate, deals of similar age (headline) | Share of deals 120 to 240 days old now Committed, by origin. Deals already open before a firm's first event are older (median 237 days versus 125), so comparing similar ages keeps age from driving the gap | after an event 13% (2 of 16) · already open before 19% (3 of 16) |
| Outcome | Mature-deal commit rate | Share of deals at least 120 days old now Committed, by origin (not age-matched) | after an event 13% (2 of 16) · already open before 24% (7 of 29) |
| Efficiency | **Cost per firm the event added** (headline) | Extra firms = attending firms met after − attending firms met before. Would have happened anyway = attending firms × (share of firms not at the event met after − share met before), over the same weeks; needs at least 5 firms to compare with. Cost ÷ (extra − would have happened anyway); none if that is below 1 | London $23K (+8 firms; firms not at the event 56% → 56%, 9 firms) · New York none (+6 extra versus about 7 anyway; firms not at the event 5% → 33%, 21 firms) · Berlin none (−2 firms) |
| Efficiency | Cost per extra firm met, before allowing for what would have happened anyway | Event cost ÷ (attending firms met after − met before) | London $23K · New York $70K · Berlin none |
| Efficiency | Cost per firm followed up | Event cost ÷ attending firms met within the window after | London $10K · New York $28K · Berlin $68K |
| Efficiency | Expected follow-up from investor mix | The event's follow-up rate if each attending firm were followed up at its investor type's average rate (all events) | London 72% actual versus 62% expected · Berlin 47% versus 59% |

## How certain

Bootstrap 95% ranges (5,000 resamples of firm-event pairs, `src/analysis.py`):

| Comparison | Estimate | 95% range |
|---|---|---|
| Meeting growth: attending minus firms not at the event | −8 points | −195 to +106 points |
| Change in firms opening a deal: attending minus firms at other events | −6 points | −27 to +16 points |

Both ranges include zero. The firm order is fixed before resampling, so the ranges are identical on every run. With three events, every finding is directional: enough to decide what to test and measure next, not to prove what events cause.

## Priority call list

Attending firms with no meeting within the window after an event they attended, one row per firm (24 firms at default). Firms with **no meeting logged since** their most recent missed event, as of 14 Oct, come first (14 firms; 12 with open deals worth $707M, 4 of them Tier 1): these are the calls. Firms met later than the window follow (10 firms): slow follow-up, no call needed now. Within each group:
**Priority 1** open deal in due diligence or at investment committee · **Priority 2** earlier-stage open deal, or a Tier 1 firm · **Priority 3** no open deal; then by tier, then open deal size. Investor type is shown but not used to rank, since foundations and insurers commit less often but are also followed up less.

Check against the client database before calling: 4 of 37 attending firms whose deals moved past the first stage have no meeting logged at all.

## Follow-up speed and outcomes (association)

| Group | Attendances | Opened a new deal within the window | Moved an existing deal forward |
|---|---|---|---|
| Met within 30 days | 27 | 33% | 26% |
| Met later or not at all | 43 | 33% | 26% |

No difference, so the 30-day standard is a service level to test, not a proven way to win deals.

## Evidence behind the recommendations (added after the second review)

| Metric | Definition | Default value |
|---|---|---|
| **Investment committee** | The investor's own committee that approves a commitment, with the legal documents; the last stage before a deal commits. Recorded in the data as "IC / Documentation". | – |
| Deals already open that moved forward | Deals open on the event date (opened before it, not committed or declined): share that reached a later stage within the window. Firms that attended versus firms not at the event (Tentative-only firms left out) | 50% (24 of 48) versus 55% (48 of 87) |
| Who commits | Deals at least 120 days old that are now Committed, family offices versus all other investor types; the unverified $650M deal left out. Also shown without commitments that skipped due diligence (possible fast re-ups) | 6 of 14 versus 6 of 57; without fast commitments 3 of 11 versus 2 of 53 |
| Event places and committed capital by investor type | Attending firm-event pairs, and committed dollars (unverified $650M deal left out) | Family offices: 16 of 70 places, $370M of $528M |
| Late-stage pipeline | Deals that ever reached the investment committee stage, how many committed or were declined, and deals recorded there today | 39 reached; 2 committed, 3 declined; 34 recorded today ($1.40B, 28 firms) |
| Commitments that skipped due diligence | Committed deals with no Due Diligence stage recorded | 9 of 14 (7 of 12 without the two flagged records) |

Assumptions behind each of these, and what would change the recommendations, are in [`assumptions.md`](assumptions.md). SQL versions: `kpi_who_commits` and `kpi_late_stage` in `sql/03_kpis.sql`.
