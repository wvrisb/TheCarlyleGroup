"""Embed the model outputs into the dashboard template.

Run:  python src/build_model.py && python src/build_dashboard.py
Reads output/*.csv and dashboard/template.html, writes dashboard/index.html
(a single self-contained file: no server, no internet, no install).
"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT, DASH = ROOT / "output", ROOT / "dashboard"

FEO_COLS = ["att_def", "window_days", "event_id", "firm_id", "attendance_group", "attended",
            "meetings_pre", "meetings_post", "days_to_first_meeting", "opps_created_pre",
            "opps_created_post", "opps_created_post_usd", "opps_created_post_usd_ex",
            "meetings_lt", "opps_created_lt", "opps_created_lt_usd", "opps_created_lt_usd_ex",
            "opps_advanced_lt", "opps_advanced_lt_usd",
            "commits_lt", "commits_lt_usd", "commits_lt_usd_ex"]

DQ_ISSUES = [
    ("High", "Opportunities", "One $650M commitment (O0017, F041) is 55% of committed capital after cleaning ($1,178M), 6.5x the firm's lifetime commitments, and skipped diligence. F041 never attended an event.", "Kept; every $ view has an include/exclude toggle; flagged for source verification."),
    ("High", "Meetings", "Meetings are logged only for firms that attended an event. The 10 never-attending firms have 0 meetings but 24 opportunities.", "Meetings used only for before/after comparisons within attending firms, never attendees versus non-attendees."),
    ("High", "Opportunities", "O9998 / O9999: identical $25M F008 commitments with no prior stages and non-standard IDs.", "One kept (flagged low-confidence), duplicate dropped."),
    ("Medium", "Opportunities", "5 stage rows dated after the 2026-10-14 as-of date, incl. two 'Committed'.", "Treated as forecasts: only stages on or before the as-of date count."),
    ("Medium", "Meetings", "Some meetings are not logged: 4 of 37 attending firms whose deals moved past the first stage have no meeting logged at all (F045's deal reached investment committee with none).", "No meeting logged is treated as a gap to confirm in the client database, not proof that we did not meet."),
    ("Medium", "Attendance", "34 contact rows are 'Tentative'; 9 firm-event pairs are Tentative-only.", "Firm attended = any contact Confirmed. Toggle includes Tentative."),
    ("Medium", "Opportunities", "8 deals jump from Follow-up / data room straight to Committed.", "Kept and flagged (possible re-ups / fast-track)."),
    ("Low", "Opportunities", "13 deals log the investment committee stage ('IC / Documentation') twice.", "First date each stage was reached is used."),
    ("Low", "Attendance", "Exact duplicate row A0011; one contact (A9998) with no firm.", "Duplicate dropped; unmapped contact excluded from firm metrics."),
    ("Low", "Meetings", "Two meetings for F007 on the same day (different purpose and channel).", "Both kept as distinct touchpoints."),
    ("Low", "Opportunities", "$1.5M / $2.5M amounts stored as floats; amount never changes over a deal's life.", "Cast to one numeric type; pipeline $ = target size, not probability-weighted."),
]


def records(df, date_cols=()):
    df = df.copy()
    for c in date_cols:
        df[c] = pd.to_datetime(df[c]).dt.strftime("%Y-%m-%d")
    return json.loads(df.to_json(orient="records"))


def main():
    r = lambda n: pd.read_csv(OUT / f"{n}.csv")
    feo = r("firm_event_outcomes")[FEO_COLS]
    data = dict(
        as_of="2026-10-14",
        events=records(r("dim_event"), ["event_date"]),
        firms=records(r("dim_firm")),
        attendance=records(r("fact_attendance")),
        meetings=records(r("fact_meeting")[["meeting_id", "firm_id", "meeting_date", "meeting_type",
                                             "internal_attendee", "purpose"]], ["meeting_date"]),
        opps=records(r("dim_opportunity"), ["created_date", "current_stage_date"]),
        stages=records(r("fact_opp_stage")[["opportunity_id", "stage", "stage_date", "stage_ord"]],
                       ["stage_date"]),
        feo=records(feo),
        dq=[dict(severity=s, table=t, issue=i, decision=d) for s, t, i, d in DQ_ISSUES],
        # bootstrap 95% ranges from src/analysis.py (full data, default settings only)
        ci={k: json.loads((OUT / "insights.json").read_text())["60"][k] for k in ("ci_meeting_growth_gap", "ci_new_deal_gap")},
    )
    html = (DASH / "template.html").read_text()
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    (DASH / "index.html").write_text(html.replace("/*__DATA__*/null", payload))
    print(f"Wrote dashboard/index.html ({(DASH / 'index.html').stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
