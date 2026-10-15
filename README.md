# Investor Event Outcomes: AI / BI Analytics Take-Home

**Live dashboard:** https://wvrisb.github.io/TheCarlyleGroup/ · **Readout:** [`docs/readout.pdf`](docs/readout.pdf)

**Question:** What happened following our investor events, what business outcomes are associated with them, and what should we learn for future events?

**Short answer:** Three events cost $1.2M and 78% of our investor firms attended. Meetings rose after the events: 43% of attending firms had a meeting with us in the 60 days before an event, 60% in the 60 days after. But similar firms that were not at the event rose almost as much over the same weeks (26% → 41%), so most of the rise would have happened anyway. Only the London dinner added more, and that rests on a comparison with 9 firms. We cannot yet show that events bring in new deals: attending firms opened no more new deals than firms that were not there, and those deals did not close more often. What to do: keep event spending flat and run the next events as a measured test; check deal by deal the $1.40B recorded at the investor's investment committee, where only 2 of 39 deals have gone on to commit, and verify the $650M deal (55% of committed capital); and call the 12 firms with open deals worth $707M that we have not met since their event.

## How this answers the brief

### What metrics and KPIs are most meaningful

A funnel from reach to capital, where each stage answers one question: **Reach** (did we get the right firms in the room?) → **Follow-up** (did attendance turn into conversations, quickly?) → **Deals** (did conversations become deals?) → **Outcome** (did deals become capital?) → **Efficiency** (was it worth the money?).

The headline metrics are the ones that hold up against a fair comparison:
- follow-up rate against the same firms' rate before the event (43% → 60%);
- Tier 1 firms not met within 60 days of an event (10 of 13);
- change in firms opening a new deal, against firms at other events (27% → 33% versus 32% → 44%: +6 versus +12 points);
- commit rate of deals of similar age (13% versus 19%);
- cost per firm the event added, after taking away the rise that would have happened anyway (London $23K; New York and Berlin none).

Follow-up is the leading indicator because it is the one Investor Relations controls directly. Two obvious metrics were rejected: cost per firm followed up (it counts firms we would have met anyway) and raw pipeline dollars (target sizes, not likely outcomes).
→ [`docs/metric_definitions.md`](docs/metric_definitions.md) · dashboard Methods tab

### How to measure or associate event-related outcomes

An outcome counts for an event if it happens within 60 days after an event the firm attended. The median first follow-up comes 29 days after an event, and 60 days captures 79% of them. When two events' windows overlap, the most recent event gets the credit; only 2 of 30 new deals are affected, and other credit rules change no conclusion.

Each claim is then tested against a fair comparison: the same firms before the event, similar firms that were not at the event, over the same weeks (some months are busier than others, so this shows what would have happened anyway), deals of similar age, each event's mix of investor types, and bootstrap 95% ranges. Everything is reported as association, not cause: today no meeting or deal can be tied to the event that drove it, and invited firms are pre-selected.
→ dashboard "What it led to" tab (the table "What the data can and cannot show") · Methods tab

### How the underlying data should be modeled

A star schema: dimension tables for events, firms and deals; fact tables for attendance (one row per firm per event), meetings, and deal stages (the first date each stage was reached); and one analysis table, firm × event, at 30, 60 and 90-day windows and two attendance definitions, which every chart and metric reads from. Cleaning happens once, with each decision logged. The model is written in SQL and in Python and checked to agree.

In production the SQL moves into the warehouse. Adding a "source event" field to deals and logging meetings for every firm would let the same model measure cause, not just association.
→ [`sql/`](sql/) · [`src/build_model.py`](src/build_model.py) · [`docs/data_quality.md`](docs/data_quality.md) · Methods tab data-model diagram

### How leadership should explore the information

Top-down, in the order a leader asks questions. The Summary gives the three answers and the recommendations; tabs 1 to 3 hold the evidence behind each answer; the Firm explorer shows what happened after each event for any firm.

- Every underlined number opens the firms behind it, so any figure can be traced to names.
- Every term has a hover definition.
- Filters (window, attendance definition, investor type, tier, region, the $650M deal) let a leader check whether a finding holds for the slice they care about, and the takeaways rewrite to match.
- Recommendations stay on the full data, so they do not shift with filters.

For a five-minute conversation, the three-slide readout carries the same story.
→ [`dashboard/index.html`](dashboard/index.html) · [How to review](#how-to-review-no-install)

### What insights and actions can be derived

- Meetings rose after the events, but almost as much at similar firms that were not there; only London added more, and that rests on a comparison with 9 firms.
- None of four checks shows that events changed deals: new deals (+6 points against +12 for firms at other events), deals already open (50% moved forward against 55%), and commitments (13% against 19% for deals of similar age).
- Family offices commit far more often: 6 of 14 of their deals at least 120 days old committed, against 6 of 57 for all other investors. They had 23% of event places and gave 70% of committed capital. This is the clearest pattern in the data, but it is one year and one of many comparisons, so it is something to test.
- 34 deals worth $1.40B are recorded at the investor's investment committee, but only 2 of the 39 deals that reached that stage committed. The deals are stuck or the records are out of date; 9 of 14 commitments skipped due diligence, which points to loose records.
- Tier 1 follow-up is slow (10 of 13 not met within 60 days), but faster follow-up shows no effect on deals (33% against 33%).
- We met fewer of Berlin's firms after it than before, although it was the most expensive event; partly because the team's follow-up went to London attendees.
- One unverified $650M deal is 55% of committed capital.

**Actions:**
1. Keep event spending flat and run the next events as a measured test: record which event each deal came from, log meetings for every invited firm, compare with similar firms left out only because places ran out, and follow firms for 6 to 12 months. Use the test to try more places for family offices, a redesigned or skipped Berlin, and two more dinners.
2. Check the late-stage pipeline deal by deal with each deal owner, close deals that are no longer live, and verify the $650M deal before quoting any total.
3. Call the firms with open deals and no meeting since their event, Tier 1 first, after checking the client database.

Every recommendation, the evidence behind it and the assumptions it depends on are set out in [`docs/assumptions.md`](docs/assumptions.md).

→ [`docs/readout.pdf`](docs/readout.pdf) · dashboard Summary tab · call list on the "What to learn" tab

## Deliverables

| | Where | What it is |
|---|---|---|
| 1. Interactive analytics | [`dashboard/index.html`](dashboard/index.html) · [live page](https://wvrisb.github.io/TheCarlyleGroup/dashboard/) · [screenshots](docs/screenshots/) | Six tabs organised around the three questions: Summary, What happened, What it led to, What to learn, Firm explorer, Methods and data. Filters for window, attendance definition, segment, tier, region and the $650M deal |
| 2. Analysis and data model | [`src/`](src/) · [`sql/`](sql/) · [`output/`](output/) · [`docs/metric_definitions.md`](docs/metric_definitions.md) · [`docs/data_quality.md`](docs/data_quality.md) | Python pipeline; the same model and KPIs in SQL (staging → firm × event table → KPI tables), checked against Python; model tables as CSV; every metric definition and data-quality decision |
| 3. Executive readout | [`docs/readout.pdf`](docs/readout.pdf) · [speaker notes](docs/readout_notes.md) | Three slides: the answer and three decisions, the evidence, and what to do this week and before the next event. The notes hold the talking points and backup answers to likely questions |
| 4. AI usage | [`AI_USAGE.md`](AI_USAGE.md) | Where AI helped, how output was validated, and twenty documented corrections |

### Analysis and data model: where each piece lives

| Asked for | Where |
|---|---|
| SQL | [`sql/01_staging.sql`](sql/01_staging.sql) cleaning and star schema · [`sql/02_firm_event_outcomes.sql`](sql/02_firm_event_outcomes.sql) the analysis table · [`sql/03_kpis.sql`](sql/03_kpis.sql) the headline metrics. Run with `python src/run_sql.py` (SQLite, built into Python) |
| Python | [`src/profile_data.py`](src/profile_data.py) profiling · [`src/build_model.py`](src/build_model.py) model · [`src/analysis.py`](src/analysis.py) insights · [`src/build_dashboard.py`](src/build_dashboard.py) dashboard build |
| Transformations | Raw CSVs → cleaned dimension and fact tables → firm × event table, in both SQL and Python; every table saved in [`output/`](output/) |
| Calculations | [`sql/03_kpis.sql`](sql/03_kpis.sql) → `output/sql/`; [`src/analysis.py`](src/analysis.py) → `output/insights.json` (30, 60 and 90-day windows) |
| Assumptions | [`docs/assumptions.md`](docs/assumptions.md): each recommendation's evidence, assumptions and what would change it; [Key assumptions](#key-assumptions) below; structural limits in [`docs/data_quality.md`](docs/data_quality.md) section 3 |
| Metric definitions | [`docs/metric_definitions.md`](docs/metric_definitions.md); also in the dashboard's Methods tab and as hover definitions |
| Data-quality decisions | [`docs/data_quality.md`](docs/data_quality.md): every issue, its evidence, severity and decision; summarised in the Methods tab |
| Validation | `src/run_sql.py` (SQL = Python), `src/check_dashboard.py` (dashboard = Python), `src/check_narrative.py` (text under every filter) |

The pipeline is plain scripts rather than notebooks, so it reruns end to end from the raw data with one command per step.

## How to review (no install)

Open `dashboard/index.html` in any browser (it is one self-contained file and works offline), or use the live page. Suggested path, about 10 minutes:

1. **Summary**: the three answers and the recommendations. Underlined numbers open the firms behind them.
2. **What it led to**: the table "What the data can and cannot show" tests each claimed benefit against a fair comparison.
3. **What to learn**: event scorecard, the follow-up gap by tier and investor type, and the priority call list.
4. **Firm explorer**: pick any firm to see what happened after each event it attended.
5. **Methods and data**: definitions, why a 60-day window, how robust the findings are, the data model and the data-quality log.

Hover any dotted-underlined term for its definition. Changing a filter updates every number, chart title and takeaway; the recommendations stay on the full data.

## How to run

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python src/profile_data.py     # data-quality checks behind docs/data_quality.md
python src/build_model.py      # cleaned dimension and fact tables + firm x event outcomes -> output/
python src/analysis.py         # insights at 30/60/90 days -> output/insights.json
python src/build_dashboard.py  # embeds the data into dashboard/template.html -> dashboard/index.html
python src/run_sql.py          # runs sql/*.sql on SQLite (built into Python) and checks every KPI against the Python output

# validation (needs: playwright install chromium)
python src/check_dashboard.py  # dashboard figures == Python figures (26 checks)
python src/check_narrative.py  # every tab's text under all 1,344 filter combinations
python src/capture_screenshots.py  # optional: refresh docs/screenshots/
```

## Approach

**Why a self-contained HTML page.** The reviewer needs to explore the data without installing anything or holding a BI licence, so the dashboard is one file that opens in any browser, works offline and renders on GitHub Pages. Every number on it is recomputed from the embedded data and tested against the Python pipeline, which a BI tool would not let me do in a take-home. In production the same model would feed the firm's BI tool (see below).

**Data model.** Raw CSVs → cleaned tables (firms, events, firm-level attendance, meetings, deals with first date each stage was reached) → one analysis table, `firm_event_outcomes`: for every firm × event × window (30/60/90) × attendance definition, what happened before and after. All cleaning happens once, so every number uses the same rules. The model is written twice: in Python (`src/build_model.py`, `src/analysis.py`) and in SQL (`sql/01_staging.sql`, `02_firm_event_outcomes.sql`, `03_kpis.sql`), and `src/run_sql.py` confirms they agree row by row and KPI by KPI at 30, 60 and 90 days.

**Linking outcomes to events (association, not cause).** An outcome counts for an event if it happens within the window after an event the firm attended; overlaps are credited to the most recent event. Each claim is then tested against a fair comparison: the same firms before the event, firms that attended a different event over the same dates, and deals old enough to have closed. With three events these comparisons are directional; bootstrap 95% ranges are reported.

**KPIs, from reach to capital.** Reach (firms attended) → Follow-up (follow-up rate versus before-event baseline, days to first meeting, Tier 1 firms not met) → Deals (new deals, existing deals moved forward, change versus firms not at the event) → Outcome (event-sourced commitments, commit rate of deals of similar age) → Efficiency (cost per firm the event added). Full definitions: [`docs/metric_definitions.md`](docs/metric_definitions.md).

## Key assumptions

- As-of date 14 Oct 2026. Stages dated later are treated as forecasts, not outcomes.
- A firm attended if any of its contacts is Confirmed (toggle to include Tentative).
- The $650M deal (O0017) is kept but unverified; every dollar view can exclude it.
- O9998/O9999 are one duplicated, low-confidence commitment; one is kept and flagged.
- Deal size ($) is the deal's target size, not probability-weighted.
- Priority tiers are Investor Relations' own labels; the data does not define them.

Full log with evidence: [`docs/data_quality.md`](docs/data_quality.md).

## Limitations

- Three events: every event comparison is directional, and both key bootstrap ranges include zero.
- Meetings are logged only for firms that attended an event, so firms never invited cannot be compared on meetings, and "no meeting logged" may not mean "no contact".
- "Firms not at the event" are similar firms we also invite, which went to a different event and had no event of their own in the same weeks. Firms whose own event fell in those weeks were removed because their own follow-up inflated their "before" count, which made our events look better. With them removed, the overall rise in meetings is about what happened at firms not at the event (+54% versus +62%); only London is clearly higher (+158% versus +33%), and that rests on 9 firms, so read it as directional.
- Event efficiency is a signal, not a ranking: few firms not at each event are available to compare with (9 for London and Berlin), so the cost per firm the event added changes with the window. Berlin's drop in meetings is the one event finding that holds at every window.
- Meetings are under-logged: 4 of 37 attending firms whose deals moved past the first stage have no meeting logged at all, so the call list should be checked against the client database.
- Meetings and deals share only a firm ID, so a meeting cannot be tied to the deal it drove.

## Taking this to production

- **Source data:** add a "source event" field to opportunities, log meetings for all firms, and record actual attendance at the door.
- **Pipeline:** move the `sql/` model into the warehouse (it is standard SQL; only date arithmetic differs by engine), schedule it after each refresh of the CRM (client database), and keep `run_sql.py`, `check_dashboard.py` and `check_narrative.py` as CI tests.
- **Front end:** the static HTML suits a take-home and offline review. In production the same model would feed the firm's BI tool, with row-level security for coverage teams.
- **Measurement design:** before the next event, set up a comparison of invited firms with similar firms not invited (matched by tier, segment and region), so next year's readout can speak to cause.

## Repository

```
data/        raw CSVs as provided
src/         profiling, model, analysis, dashboard build, validation
sql/         the same model and KPIs in SQL (staging, firm x event table, KPI tables)
output/      model tables (CSV), insights.json, and output/sql/ KPI tables from the SQL run
dashboard/   template.html (source) and index.html (built, self-contained)
docs/        metric definitions, data-quality log, readout PDF, screenshots
AI_USAGE.md  how AI was used and validated
```
