# How I used AI

I used Claude (Anthropic) throughout, as a pair analyst: it proposed options, wrote code and drafts, and ran checks; I made the decisions, challenged its output, and set the bar for what counted as validated.

## Where AI helped, and how it sped things up

| Area | What AI did | Rough time saved |
|---|---|---|
| Data profiling | Wrote `src/profile_data.py` and surfaced 16 data-quality issues with evidence for each | Half a day → under an hour |
| Options and decisions | Proposed alternatives for format, attribution, KPIs and data model, each with a recommendation, so I could decide quickly and explicitly (decisions logged in `docs/`) | Faster, better-documented choices |
| Data model and analysis | Wrote the pipeline (`build_model.py`, `analysis.py`) and the stress tests (comparison group, before/after by group, bootstrap ranges, investor-mix adjustment) | About a day of coding → a few hours |
| Dashboard | Built a self-contained HTML dashboard with drill-downs, hover definitions and filter-aware text | The largest saving: an interactive build in hours |
| Readout | Drafted three structures; I chose a mix and the AI built the deck | Most of the layout work |
| Validation tooling | Wrote the two automated test suites described below | Tests I would not otherwise have had time to write |

## How I validated the output

1. **Two independent code paths for every number.** The dashboard recomputes every figure in JavaScript; `src/check_dashboard.py` compares 18 groups of figures against the Python pipeline. All match.
2. **Every sentence tested under every filter.** Takeaways and titles are generated from the numbers on screen. `src/check_narrative.py` renders all 6 tabs in all 1,344 filter combinations, plus every firm's detail view, and checks that the words agree with the numbers next to them (for example, "beat" only when the first number is higher). Final run: 0 issues across 8,064 rendered tabs.
3. **Data quality is reproducible.** `src/profile_data.py` re-derives every issue in `docs/data_quality.md`.
4. **Stress-testing claims, not just code.** For each headline claim I asked how it could be wrong and had it tested: a comparison group for seasonality, before/after per group instead of raw comparisons, deal age, investor mix, attribution rule, window length, and bootstrap ranges.
5. **Mock reviews.** I had the work reviewed from the point of view of an interviewer and the Head of IR, several times, and acted on what they found.
6. **Hand review of anything tests cannot judge.** I read the recommendations and the readout myself against the numbers.

## Where I changed, corrected or challenged AI-generated work

| # | What the first draft said | Who challenged it | What testing showed | What changed |
|---|---|---|---|---|
| 1 | Compare attendees vs non-attendees on meetings | AI, on profiling | Meetings are only logged for firms that attended an event | Meetings used only within attending firms and against firms at other events |
| 2 | "London's follow-up rate is highest at every window" | AI self-check | At 90 days New York's rate is higher | Claim limited to efficiency, which does hold |
| 3 | Tier 1 = "our most valuable relationships" | Me ("what is the difference between tiers?") | Tier 1 firms are not larger by commitments or pipeline | Tier described as IR's stated priority, definition flagged as missing |
| 4 | "Space events at least 60 days apart" | Me ("why 60 days?") | Berlin's weak follow-up was not explained by its closeness to London | Recommendation dropped |
| 5 | "Attendees opened deals less often than never-invited firms (33% vs 47%)" | Mock interviewer review | Never-invited firms were already far more active before the events | Replaced with each group's change from its own baseline |
| 6 | "13 of 21 Tier 1 attendances got no follow-up" | Mock review | Falls to 4 of 13 firms by 90 days | Reframed as slow follow-up, which strengthened the 30-day recommendation |
| 7 | "Foundations, insurers and pensions are followed up least at every tier" | AI self-review | False at Tier 3; Tier 1 pension funds were mostly met | Narrowed to Tier 1 foundations and insurers |
| 8 | Takeaways written as fixed sentences | Me (toggled to 30 days and saw a contradiction) | The automated test found five more errors under other filters, incl. a recommendation contradicting its own numbers | All text computed from the screen; recommendations pinned to full data; test suite added |
| 9 | Cost per firm followed up as the efficiency headline | Mock interviewer review | It counts firms we would have met anyway | Headline changed to cost per extra firm met (London $23K, New York $70K, Berlin none) |
| 10 | "Contact rose beyond the season" | Mock interviewer review | Some comparison-group firms were in their own post-event period; using only firms with no event within 60 days, the overall difference disappears, while London's lift remains | [Decision: state as kept / revised — see README limitations] |

## What I kept for my own judgment

The decisions that shape the conclusions were mine: how to treat the $650M deal, Confirmed vs Tentative attendance, the 60-day window and credit rule, which comparison is fair, what goes in five minutes with the Head of IR, and the ranking of the recommendations.

## What the AI was weakest at

Its first drafts tended to state findings more confidently than the data supports, and to write fixed sentences around live numbers. Every correction above came from asking "how could this be wrong?" and making it check, rather than from accepting fluent output.
