# Investor Event Outcomes: AI / BI Analytics Take-Home

**Question:** What happened following our investor events, what business outcomes are associated with them, and what should we learn for future events?

**Short answer:** Three events cost $1.2M and reached 78% of our investor firms. Contact with attending firms rose after the events, but only after the London dinner did it clearly beat the usual seasonal rise. We cannot detect that the events created new pipeline, and today's data cannot show it either way. The levers we control are event format (London bought the most extra contact per dollar) and the speed of follow-up with Tier 1 firms (10 of 13 were not met within 60 days of an event). One unverified $650M deal is 55% of committed capital.

## Deliverables

| | Where | What it is |
|---|---|---|
| 1. Interactive analytics | [`dashboard/index.html`](dashboard/index.html) · [live page](https://<your-username>.github.io/<repo>/dashboard/) · [screenshots](docs/screenshots/) | Six tabs organised around the three questions: Summary, What happened, What it led to, What to learn, Firm explorer, Methods and data. Filters for window, attendance definition, segment, tier, region and the $650M deal |
| 2. Analysis and data model | [`src/`](src/) · [`output/`](output/) · [`docs/metric_definitions.md`](docs/metric_definitions.md) · [`docs/data_quality.md`](docs/data_quality.md) | Python pipeline, model tables as CSV, every metric definition, and every data-quality decision |
| 3. Executive readout | [`docs/readout.pdf`](docs/readout.pdf) | Three slides: the answer and three decisions, the evidence, and what to do this week and before the next event. Speaker notes included |
| 4. AI usage | [`AI_USAGE.md`](AI_USAGE.md) | Where AI helped, how output was validated, and ten documented corrections |

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

# validation (needs: playwright install chromium)
python src/check_dashboard.py  # dashboard figures == Python figures (19 checks)
python src/check_narrative.py  # every tab's text under all 1,344 filter combinations
python src/capture_screenshots.py  # optional: refresh docs/screenshots/
```

## Approach

**Data model.** Raw CSVs → cleaned tables (firms, events, firm-level attendance, meetings, deals with first date each stage was reached) → one analysis table, `firm_event_outcomes`: for every firm × event × window (30/60/90) × attendance definition, what happened before and after. All cleaning happens once, so every number uses the same rules.

**Linking outcomes to events (association, not cause).** An outcome counts for an event if it happens within the window after an event the firm attended; overlaps are credited to the most recent event. Each claim is then tested against a fair comparison: the same firms before the event, firms that attended a different event over the same dates, and deals old enough to have closed. With three events these comparisons are directional; bootstrap 95% ranges are reported.

**KPIs, from reach to capital.** Reach (firms attended) → Follow-up (follow-up rate vs before-event baseline, days to first meeting, Tier 1 firms not met) → Pipeline (new deals, existing deals moved forward, change vs comparison group) → Outcome (event-sourced commitments, mature-deal commit rate) → Efficiency (cost per extra firm met). Full definitions: [`docs/metric_definitions.md`](docs/metric_definitions.md).

## Key assumptions

- As-of date 14 Oct 2026. Stages dated later are treated as forecasts, not outcomes.
- A firm attended if any of its contacts is Confirmed (toggle to include Tentative).
- The $650M deal (O0017) is kept but unverified; every dollar view can exclude it.
- O9998/O9999 are one duplicated, low-confidence commitment; one is kept and flagged.
- Pipeline $ is the opportunity's target size, not probability-weighted.
- Priority tiers are IR's own labels; the data does not define them.

Full log with evidence: [`docs/data_quality.md`](docs/data_quality.md).

## Limitations

- Three events: every event comparison is directional, and both key bootstrap ranges include zero.
- Meetings are logged only for firms that attended an event, so firms never invited cannot be compared on meetings, and "no meeting logged" may not mean "no contact".
- The meetings comparison group is firms that attended a different event and had no event of their own within the window. Firms in their own post-event period were removed because their "before" meetings were inflated by follow-up, which made our events look better. With them removed, the overall rise in meetings matches the season (+54% vs +62%); only London clearly beats it (+158% vs +33%). The comparison group is small (13 → 21 meetings), so read it as directional.
- Meetings and deals share only a firm ID, so a meeting cannot be tied to the deal it drove.

## Taking this to production

- **Source data:** add a "source event" field to opportunities, log meetings for all firms, and record actual attendance at the door.
- **Pipeline:** schedule the Python steps (or move them to SQL in the warehouse) after each CRM refresh; keep `check_dashboard.py` and `check_narrative.py` as CI tests.
- **Front end:** the static HTML suits a take-home and offline review. In production the same model would feed the firm's BI tool, with row-level security for coverage teams.
- **Measurement design:** before the next event, set up a comparison of invited firms with similar firms not invited (matched by tier, segment and region), so next year's readout can speak to cause.

## Repository

```
data/        raw CSVs as provided
src/         profiling, model, analysis, dashboard build, validation
output/      model tables (CSV) and insights.json
dashboard/   template.html (source) and index.html (built, self-contained)
docs/        metric definitions, data-quality log, readout PDF, screenshots
AI_USAGE.md  how AI was used and validated
```
