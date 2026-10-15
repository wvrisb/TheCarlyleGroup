# Assumptions and how sure we are

This page lists, for each recommendation, the evidence behind it, the assumptions it depends on, and what would change it. It then lists the assumptions behind the analysis as a whole. Every number comes from `output/insights.json` (Python) and is checked against the SQL version (`src/run_sql.py`) and the dashboard (`src/check_dashboard.py`).

Default settings: data as of 14 October 2026; results over the 60 days after each event; a firm attended if at least one of its people confirmed.

## Recommendation 1: keep event spending flat and run the next events as a measured test

**Evidence.** None of four checks shows that events changed deals:

| Check | Attending firms | Comparison | Where |
|---|---|---|---|
| Meetings, 60 days before to 60 days after | +54% | +62% for similar firms not at the event | Dashboard tab 1 |
| Share of firms opening a new deal | 27% → 33% (+6 points) | 32% → 44% (+12 points) for firms at other events | Dashboard tab 2 |
| Deals already open that moved to a later stage | 50% (24 of 48) | 55% (48 of 87) for firms not at the event | Dashboard tab 2 |
| Deals 120 to 240 days old that committed | 13% (2 of 16) opened after an event | 19% (3 of 16) already open before | Dashboard tab 2 |

Statistical ranges (bootstrap, 5,000 resamples) for the first two checks both include zero.

**Assumptions.**
- Similar firms not at the event are a fair benchmark. They are firms we also invite to events, but they were invited, not picked at random, and we can only compare firms whose meetings are logged.
- 60 days is long enough to see an effect on meetings and early deal activity. It is not long enough to see whether events build relationships that pay off over years; that is why the test follows firms for 6 to 12 months.
- With three events, "no measurable effect" means unproven, not disproven. That is why the recommendation is to hold spending flat and test, not to cut.

**What would change it.** A next round of events where attending firms open or advance clearly more deals than similar firms left out only because places ran out.

**The three changes to try inside the test, and their evidence.**
- *More places for family offices.* 6 of 14 family-office deals at least 120 days old committed, against 6 of 57 for every other type of investor. Leaving out fast commitments that skipped due diligence (possible re-ups): 3 of 11 against 2 of 53. Family offices had 23% of event places (16 of 70) and gave 70% of committed capital ($370M of $528M). *Assumptions:* one year of data; this was found by comparing about 15 groups, so a gap of this size could appear by chance in one of them; the unverified $650M deal is from a foundation and is left out. This is a pattern to test, not a rule.
- *Redesign or skip Berlin.* It cost $610K and we met fewer of its attending firms after it than before (11 → 9 firms), at the 30, 60 and 90-day windows, including attendees who did not go to London (11 → 6 meetings). In the 60 days after Berlin, 11 of the team's 31 meetings were with Berlin attendees and 15 with London attendees. *Assumption:* the drop is partly our follow-up, not only the event; the data cannot separate the two.
- *Two more dinners.* London had the highest follow-up rate (72%) at the lowest cost, and is the only event whose meetings rose more than at similar firms not at it (+158% against +33%). *Assumption:* this rests on one dinner and 9 comparison firms, and holds at 60 days only.

## Recommendation 2: check the late-stage pipeline deal by deal, and verify the $650M deal

**Evidence.** 34 deals worth $1.40B (28 firms) are recorded at the investor's investment committee, the last stage before a commitment. Of the 39 deals that ever reached that stage, 2 committed and 3 were declined. 9 of 14 commitments skipped the due diligence stage (7 of 12 without the two flagged records), and 4 of 37 attending firms whose deals moved forward have no meeting logged at all. One $650M commitment that we have not verified is 55% of all committed capital.

**Assumptions.**
- The stage records are the only view of the pipeline we have. Two explanations fit and the data cannot separate them: the deals are stuck at the investors' committees, or the records are out of date. Skipped stages and unlogged meetings point to the second.
- Deals in the data were opened between January and August 2026. Institutional committees can take many months, so a deal that has not yet committed may still commit.

**What would change it.** If deal owners confirm most of the $1.40B is live and moving, the pipeline is healthier than the records suggest, and the check has still done its job.

## Recommendation 3: call the firms with open deals and no meeting since their event

**Evidence.** 14 firms have had no logged meeting since their event; 12 of them have open deals worth $707M, 4 of them Tier 1. Tier 1 firms are followed up most slowly: 10 of 13 were not met within 60 days of an event they attended (4 of 13 still not met by 90 days).

**Assumptions.**
- No logged meeting does not always mean we did not meet: some meetings are not logged, so the list should be checked against the client database before calling.
- Firms met within 30 days opened new deals at about the same rate as firms met later (33% against 33%). Faster follow-up is therefore a service standard for our most important investors, not a proven way to win deals.

## Assumptions behind the whole analysis

| Assumption | Why | Effect if wrong |
|---|---|---|
| Data as of 14 October 2026; stages dated later are forecasts | They had not happened yet | Two $20M commitments would count as committed |
| A firm attended if at least one of its people confirmed | Confirmed is the best available signal; actual attendance is not recorded | The dashboard has a setting to include Tentative firms |
| Outcomes count if they happen within 60 days after an event the firm attended; overlaps go to the most recent event | 79% of first follow-ups happen within 60 days; only 2 of 30 new deals fall in two windows | Checked at 30 and 90 days in the Methods tab |
| Meetings are logged only for firms that attended an event, and the log ends on 7 September 2026 | That is how the data was provided | Firms never invited cannot be compared on meetings; "no meeting since" is measured to 7 September |
| Invited firms were chosen, not random | Invitations follow Investor Relations' priorities | Differences between attending and other firms may reflect who was invited |
| Deal size means the deal's target size, not a probability-weighted amount | The amount never changes over a deal's life | Pipeline dollar totals overstate expected capital |
| The $650M deal (O0017) is kept but flagged, and left out of the investor-type comparison | It is 6.5 times the firm's lifetime commitments and skipped due diligence | If it is real, foundations are this year's largest committers |
| Many groups were compared | Exploration across event, tier, investor type, seniority, follow-up type | Any single pattern could appear by chance; patterns are presented as things to test |
| One year, three events | That is the data provided | Every event comparison is directional |

Data-quality issues and the decision taken on each are in [`data_quality.md`](data_quality.md); metric definitions are in [`metric_definitions.md`](metric_definitions.md).
