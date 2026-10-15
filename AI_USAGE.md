# How I used AI

## In brief

- **Time spent:** about a day and a half, within the two-day guide. AI wrote most of the code, which made it affordable to spend much of that time on checking the work.
- **Where AI helped:** profiling the data, proposing options for metrics and linking outcomes to events, writing the Python and SQL model, building the dashboard, drafting the readout, and writing the automated checks.
- **How it sped things up:** AI wrote most of the code, so a day and a half covered the analysis, an interactive dashboard, a SQL version of the model and the automated checks. The table below shows where it saved the most time.
- **How I checked it:** every number is computed in three independent ways (Python, SQL and the dashboard's own code) and automated checks confirm they agree; every sentence on the dashboard is tested against the numbers beside it under all 1,344 filter combinations; I recomputed the headline figures from the raw files myself; and I ran mock reviews as an interviewer and as the Head of Investor Relations.
- **Where I corrected or challenged it:** 20 documented cases below. Two examples: an early recommendation to follow up Tier 1 firms within 30 days was downgraded to a service standard to test, because firms met within 30 days opened new deals no more often than firms met later (row 14); and "deals opened after events closed less often, 13% versus 24%" was corrected to 13% versus 19% once deals of similar age were compared (row 16).

---

I used Claude (Anthropic) throughout, as a pair analyst: it proposed options, wrote code and drafts, and ran checks; I made the decisions, challenged its output, and set the bar for what counted as validated.

## Where AI helped, and how it sped things up

| Area | What AI did | Rough time saved |
|---|---|---|
| Data profiling | Wrote `src/profile_data.py` and surfaced 16 data-quality issues with evidence for each | Half a day → under an hour |
| Options and decisions | Proposed alternatives for format, attribution, KPIs and data model, each with a recommendation, so I could decide quickly and explicitly (decisions logged in `docs/`) | Faster, better-documented choices |
| Data model and analysis | Wrote the pipeline (`build_model.py`, `analysis.py`) and the stress tests (comparison group, before/after by group, bootstrap ranges, investor-mix adjustment) | About a day of coding → a few hours |
| Dashboard | Built a self-contained HTML dashboard with drill-downs, hover definitions and filter-aware text | The largest saving: an interactive build in hours |
| Readout | Drafted three structures; I chose a mix and the AI built the deck | Most of the layout work |
| SQL version of the model | Translated the Python model into SQL (`sql/`) and wrote `src/run_sql.py` to prove both give the same answer | The model in the language a BI team would run, at little extra cost |
| Validation tooling | Wrote the automated test suites described below | Tests I would not otherwise have had time to write |

## How I validated the output

1. **Two independent code paths for every number.** The dashboard recomputes every figure in JavaScript; `src/check_dashboard.py` compares 30 groups of figures against the Python pipeline. All match. A third path, the SQL model, is checked by `src/run_sql.py`: the firm × event table matches Python cell by cell at 30, 60 and 90 days, and every headline KPI matches (28 checks in all). I also broke a cleaning rule on purpose to confirm the check fails when it should.
2. **Every sentence tested under every filter.** Takeaways and titles are generated from the numbers on screen. `src/check_narrative.py` renders all 6 tabs in all 1,344 filter combinations, plus every firm's detail view, and checks that the words agree with the numbers next to them (for example, "beat" only when the first number is higher). Final run: 0 issues across 8,064 rendered tabs.
3. **Data quality is reproducible.** `src/profile_data.py` re-derives every issue in `docs/data_quality.md`.
4. **Stress-testing claims, not just code.** For each headline claim I asked how it could be wrong and had it tested: a comparison group for seasonality, before/after per group instead of raw comparisons, deal age, investor mix, attribution rule, window length, and bootstrap ranges.
5. **Mock reviews.** I had the work reviewed from the point of view of an interviewer and the Head of IR, several times, and acted on what they found.
6. **Hand review of anything tests cannot judge.** I read the recommendations and the readout myself against the numbers.

## Where I changed, corrected or challenged AI-generated work

| # | What the first draft said | Who challenged it | What testing showed | What changed |
|---|---|---|---|---|
| 1 | Compare attendees vs non-attendees on meetings | AI, on profiling | Meetings are only logged for firms that attended an event | Meetings used only within attending firms and against firms at other events |
| 2 | "London's follow-up rate is highest at every window" | AI self-check | At 90 days New York's rate is higher | Claim narrowed to efficiency at the default window (later qualified again, row 13) |
| 3 | Tier 1 = "our most valuable relationships" | Me ("what is the difference between tiers?") | Tier 1 firms are not larger by commitments or pipeline | Tier described as IR's stated priority, definition flagged as missing |
| 4 | "Space events at least 60 days apart" | Me ("why 60 days?") | Berlin's weak follow-up was not explained by its closeness to London | Recommendation dropped |
| 5 | "Attendees opened deals less often than never-invited firms (33% vs 47%)" | Mock interviewer review | Never-invited firms were already far more active before the events | Replaced with each group's change from its own baseline |
| 6 | "13 of 21 Tier 1 attendances got no follow-up" | Mock review | Falls to 4 of 13 firms by 90 days | Reframed as slow follow-up, which strengthened the 30-day recommendation |
| 7 | "Foundations, insurers and pensions are followed up least at every tier" | AI self-review | False at Tier 3; Tier 1 pension funds were mostly met | Narrowed to Tier 1 foundations and insurers |
| 8 | Takeaways written as fixed sentences | Me (toggled to 30 days and saw a contradiction) | The automated test found five more errors under other filters, incl. a recommendation contradicting its own numbers | All text computed from the screen; recommendations pinned to full data; test suite added |
| 9 | Cost per firm followed up as the efficiency headline | Mock interviewer review | It counts firms we would have met anyway | Headline changed to cost per extra firm met (later adjusted for the season, row 12) |
| 10 | "Contact rose beyond the season" | Mock interviewer review | Some of the firms used for comparison had an event of their own in the same weeks, which inflated their "before" count. Using only firms with no event of their own in the window, the overall difference disappears, while London's lift remains | Comparison limited to similar firms with no event of their own in the window; headline changed to "only London added more meetings than at firms not at the event"; the original comparison is kept in the Methods tab |
| 11 | Slide 3: "Call these Tier 1 firms we have not met since their event" | Mock Head of IR review ("we met Firm 06 in May") | 4 of the 5 named firms had been met, just after 60 days | Call list split: 14 firms with no meeting logged since their event (4 Tier 1 with live deals) are the calls; 10 met late are evidence of slow follow-up |
| 12 | "London $23K vs New York $70K per extra firm met" | Mock interviewer review | Over New York's dates, similar firms not at the event went from 5% to 33% met, so New York's 6 extra firms are about what would have happened anyway | Cost per firm now counts only firms beyond the rise seen at firms not at the event ("cost per firm the event added"); New York added none |
| 13 | "London was the most efficient event" | Robustness check across windows | London's season-adjusted lead holds at 60 days only, on 9 comparison firms; Berlin's drop holds at every window, also for Berlin attendees who skipped London | Decision 3 reordered: review Berlin first, treat dinners as a format to test |
| 14 | "Follow up Tier 1 within 30 days" as a pipeline lever | Mock interviewer ("what is the evidence?") | Firms met within 30 days opened new deals at the same rate as those met later (33% vs 33%) | Framed as a service standard to test, not a proven driver |
| 15 | Bootstrap ranges reported to the point | My re-run of the pipeline | The ranges moved between runs: firm order came from a Python set, so the seeded resampling was not reproducible | Order fixed; ranges are now identical on every run |
| 16 | "Deals opened after events closed less often: 13% vs 24%" | Mock interviewer review | Deals already open before a firm's first event are older (median 237 vs 125 days) and had longer to close; at similar age (120 to 240 days) it is 13% vs 19% | Similar-age comparison is now the headline; the wider gap is shown only as context |
| 17 | "Berlin was followed by less contact", read as a verdict on the event | Mock Head of IR review ("is it Berlin or us?") | In the 60 days after Berlin only 11 of the team's 31 meetings were with Berlin attendees; 15 were with London attendees from 26 days earlier | Recommendation 3 now reviews Berlin and its follow-up, and asks for named follow-up owners when events are close together |
| 18 | Readout wording such as "beat the season on contact" and "new pipeline did not rise" | Me, reading it as the Head of IR would | The shorthand needed a second read, and "did not rise" was wrong: attending firms did open more deals (+6 points), just no more than firms at other events. The review also found "+11 points (32% → 44%)": the change came from unrounded figures, so it did not match the rounded shares beside it | Readout rewritten in plain words (meetings, deals, open deal, margin of error); every change in points is now the difference of the rounded shares shown, on the slides and the dashboard |
| 19 | "Most of the rise was seasonal" and "comparison group" | Me ("would a reader understand this without my context?") | "Seasonal" stated a cause we have not proven: there is one year of data, so we only know that similar firms not at the event rose almost as much. "Comparison group" is analyst shorthand | Readout, dashboard and docs now say what was measured, in plain words: "similar firms that were not at the event" and "would have happened anyway"; the 43% → 60% card now says which is before and which is after |
| 20 | The three recommendations (measure events; 30-day Tier 1 follow-up; review Berlin and try dinners) | Me ("are these the strongest recommendations?"), then two simulated Head of Investor Relations reviews | Deeper exploration found stronger evidence elsewhere: family offices commit far more often (6 of 14 versus 6 of 57), and only 2 of 39 deals that reached the investor's investment committee committed. It also killed one idea: follow-ups with a Senior Partner were followed by deal movement less often, not more. The reviews then corrected my framing: we cannot "clear" an investor's committee, and the family-office gap could be chance | Recommendations rebuilt: keep spending flat and test (with family offices, Berlin and dinners as things to try); check the late-stage pipeline deal by deal; call firms with open deals. New `docs/assumptions.md` sets out the evidence, assumptions and what would change each one |

## What I kept for my own judgment

The decisions that shape the conclusions were mine: how to treat the $650M deal, Confirmed vs Tentative attendance, the 60-day window and credit rule, which comparison is fair, what goes in five minutes with the Head of IR, and the ranking of the recommendations.

## What the AI was weakest at

Its first drafts tended to state findings more confidently than the data supports, and to write fixed sentences around live numbers. Every correction above came from asking "how could this be wrong?" and making it check, rather than from accepting fluent output.
