"""Data profiling and data-quality checks for the IR events take-home.

Run:  python src/profile_data.py
Prints every check documented in docs/data_quality.md so the findings are reproducible.
"""
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
AS_OF = pd.Timestamp("2026-10-14")  # analysis date; anything later is future-dated

STAGE_ORDER = {
    "Initial Conversation": 1, "Follow-up / VDR": 2, "Due Diligence": 3,
    "IC / Documentation": 4, "Committed": 5, "Declined": 5,
}


def load():
    return dict(
        events=pd.read_csv(DATA / "events.csv", parse_dates=["event_date"]),
        firms=pd.read_csv(DATA / "firms.csv"),
        att=pd.read_csv(DATA / "event_attendees.csv"),
        meet=pd.read_csv(DATA / "meetings.csv", parse_dates=["meeting_date"]),
        opp=pd.read_csv(DATA / "opportunity_stage_history.csv",
                        parse_dates=["created_date", "stage_date"]),
    )


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def main():
    d = load()
    att, meet, opp, firms = d["att"], d["meet"], d["opp"], d["firms"]

    section("Row counts and nulls")
    for name, df in d.items():
        print(f"{name:8s} rows={len(df):4d} exact_dup_rows={df.duplicated().sum()} "
              f"nulls={df.isna().sum()[lambda s: s > 0].to_dict()}")

    section("Attendance")
    print("Exact duplicate rows:\n", att[att.duplicated(keep=False)])
    print("Missing firm_id:\n", att[att.firm_id.isna()])
    fe = (att.dropna(subset=["firm_id"]).drop_duplicates()
          .groupby(["event_id", "firm_id"]).attendance_status
          .agg(lambda s: "Confirmed" if (s == "Confirmed").any() else "Tentative only"))
    print("Firm-event pairs by best status:\n", fe.groupby(level=0).value_counts().unstack())
    never = sorted(set(firms.firm_id) - set(att.firm_id.dropna()))
    print(f"Firms never on an attendee list ({len(never)}):", never)

    section("Meetings")
    print("Date range:", meet.meeting_date.min().date(), "->", meet.meeting_date.max().date())
    print("Same firm, same date:\n", meet[meet.duplicated(["firm_id", "meeting_date"], keep=False)])
    print("Meetings logged for never-attending firms:", meet.firm_id.isin(never).sum())

    section("Opportunities")
    print("Future-dated stage rows (after", AS_OF.date(), "):\n", opp[opp.stage_date > AS_OF])
    seq = opp.sort_values(["opportunity_id", "stage_date"]).groupby("opportunity_id").stage.agg(list)
    print("Repeated stage:", [o for o, s in seq.items() if len(s) != len(set(s))])
    print("Does not start at Initial Conversation:", [o for o, s in seq.items() if s[0] != "Initial Conversation"])
    print("Committed without Due Diligence:", [o for o, s in seq.items() if "Committed" in s and "Due Diligence" not in s])
    print("Non-standard IDs:\n", opp[~opp.opportunity_id.str.match(r"^O0\d{3}$")])
    amt = opp.drop_duplicates("opportunity_id").opportunity_amount_usd
    print("Amount distribution ($M):", (amt / 1e6).value_counts().sort_index().to_dict())
    last = opp.sort_values("stage_date").groupby("opportunity_id").last()
    committed = last[last.stage == "Committed"].opportunity_amount_usd
    print(f"Committed total ${committed.sum()/1e6:,.0f}M; largest single "
          f"${committed.max()/1e6:,.0f}M ({committed.max()/committed.sum():.0%} of total)")
    print("Opportunities by firms that never attended:", opp[opp.firm_id.isin(never)].opportunity_id.nunique())


if __name__ == "__main__":
    main()
