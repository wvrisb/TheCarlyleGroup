# Metric definitions

Every metric in the dashboard and the readout, in plain language and as computed.
Code: `src/build_model.py` (firm × event table), `src/analysis.py` (insights), and the dashboard's own JavaScript (same rules, recomputed live for filters; `src/check_dashboard.py` confirms both agree).

**Default settings:** 60-day window · attended = any contact Confirmed · all firms · $650M deal included · as of 14 Oct 2026.

## Building blocks

| Term | Definition |
|---|---|
| **Attended** | A firm attended an event if at least one of its contacts on that event's list is `Confirmed`. Firms whose contacts are all `Tentative` are a separate group ("Tentative only"). A toggle counts them as attended. |
| **Window** | The days after an event in which outcomes are linked to it: 60 by default, 30 and 90 as checks. "Before" uses the same number of days ending the day before the event. The event day itself counts as "after". |
| **Why 60 days** | Measured from each event, the median attending firm's first meeting came 29 days later; 60 days captures 79% of first follow-ups (30 days: 51%; 90 days: 96%). London and Berlin were 26 days apart, so 90 days mixes events. A typical deal commits about 53 days after it opens. |
| **Credit rule** | When an outcome falls in the windows of two events a firm attended, it is credited to the most recent one. Only 2 of 30 new deals are affected; first-touch or split credit changes no conclusion. |
| **Comparison group** | For each event: firms that attended one of the other two events but not this one, and had no event of their own within the window. Their meetings are logged (only attending firms have meeting records) and they are measured over the same dates, so they show what the time of year alone does. Firms whose own event fell inside the window are left out, because their own follow-up inflates the "before" period. Used for meetings only; the new-deal comparison uses all firms at other events. |
| **Never invited** | Firms on no attendee list for any event (10 firms). Used only for deal outcomes, since their meetings are not logged. |
| **Live deal** | A deal opened before the event date that had not committed or been declined by then. |
| **Mature deal** | A deal opened at least 120 days before 14 Oct 2026, so it has had time to commit. |
| **Pipeline $** | An opportunity's target amount. Never changes over a deal's life and is not probability-weighted: scale, not expected value. |
| **Priority tier** | IR's own Tier 1–3 label. Not defined in the data, and Tier 1 firms are not larger by past commitments, so read it as IR's stated priority. |

## KPIs, from reach to capital

| Tier | Metric | Definition | Default value |
|---|---|---|---|
| Reach | Firms attended | Distinct firms with at least one attended event | 47 of 60 (78%) |
| Reach | Tier 1 firms attended | Distinct Tier 1 firms with at least one attended event | 13 |
| Follow-up | **Follow-up rate** | Attending firm-event pairs with at least one meeting within the window ÷ attending pairs | 60% (42 of 70) |
| Follow-up | Before-event baseline | Same pairs with at least one meeting in the window before the event | 43% |
| Follow-up | Average days to first meeting | Mean days from event to the firm's first meeting within the window | NY 27 · London 19 · Berlin 23 |
| Follow-up | Tier 1 firms not met in time | Distinct Tier 1 firms with at least one attended event and no meeting within the window after it | 10 of 13 (30 days: 11 · 90 days: 4) |
| Follow-up | Meeting growth vs comparison group | Meetings in the window after ÷ before, minus 1: attending firms vs comparison group | +54% vs +62% overall; London +158% vs +33% |
| Pipeline | New deals after an event | Opportunities created within the window after an event the firm attended (credited per the rule above) | 30 ($1.40B target) |
| Pipeline | Existing deals moved forward | Opportunities created before the event that reached a new stage (not Declined) within the window | 23 |
| Pipeline | Change in firms opening a deal | Share of firm-event pairs with a new opportunity, after minus before, by group | attending +6 pts · firms at other events +11 · never invited −3 |
| Pipeline | Live deals moved forward | Among attending pairs with a live deal: share where a deal moved to a later stage, followed up vs not | 59% vs 50% (17 vs 14) |
| Outcome | Event-sourced deals committed | New deals after an event whose current stage is Committed (as of 14 Oct) | 3 ($250M; one is the low-confidence O9998) |
| Outcome | Mature-deal commit rate | Share of mature deals now Committed, by origin | after an event 13% (2 of 16) · already open before 24% (7 of 29) |
| Efficiency | **Cost per extra firm met, beyond the season** (headline) | Extra firms = attending firms met after − attending firms met before. Seasonal expectation = attending firms × (share of comparison-group firms met after − share met before), over the same dates; needs at least 5 comparison firms. Cost ÷ (extra − expected); none if that is below 1 | London $23K (+8 firms; comparison 56% → 56%, 9 firms) · NY none (+6 extra vs about 7 expected; comparison 5% → 33%, 21 firms) · Berlin none (−2 firms) |
| Efficiency | Cost per extra firm met, before season adjustment | Event cost ÷ (attending firms met after − met before) | London $23K · NY $70K · Berlin none |
| Efficiency | Cost per firm followed up | Event cost ÷ attending firms met within the window after | London $10K · NY $28K · Berlin $68K |
| Efficiency | Expected follow-up from investor mix | The event's follow-up rate if each attending firm were followed up at its investor type's average rate (all events) | London 72% actual vs 62% expected · Berlin 47% vs 59% |

## How certain

Bootstrap 95% ranges (5,000 resamples of firm-event pairs, `src/analysis.py`):

| Comparison | Estimate | 95% range |
|---|---|---|
| Meeting growth: attending minus comparison group | −8 pts | −195 to +106 pts |
| Change in firms opening a deal: attending minus firms at other events | −6 pts | −27 to +16 pts |

Both ranges include zero. The firm order is fixed before resampling, so the ranges are identical on every run. With three events, every finding is directional: enough to decide what to test and measure next, not to prove what events cause.

## Priority call list

Attending firms with no meeting within the window after an event they attended, one row per firm (24 firms at default). Firms with **no meeting logged since** their most recent missed event, as of 14 Oct, come first (14 firms; 12 with live deals worth $707M, 4 of them Tier 1): these are the calls. Firms met later than the window follow (10 firms): slow follow-up, no call needed now. Within each group:
**P1** live deal in due diligence or IC · **P2** earlier-stage live deal, or a Tier 1 firm · **P3** no live deal; then by tier, then live deal size. Investor type is shown but not used to rank, since foundations and insurers commit less often but are also followed up less.

Check against the CRM before calling: 4 of 37 attending firms whose deals moved past the first stage have no meeting logged at all.

## Follow-up speed and outcomes (association)

| Group | Attendances | Opened a new deal within the window | Moved an existing deal forward |
|---|---|---|---|
| Met within 30 days | 27 | 33% | 26% |
| Met later or not at all | 43 | 33% | 26% |

No difference, so the 30-day standard is a service level to test, not a proven driver of pipeline.
