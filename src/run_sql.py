"""Run the SQL version of the model (sql/*.sql) on SQLite and check it against the Python pipeline.

Run:  python src/run_sql.py          (no extra installs: SQLite ships with Python)
Loads data/*.csv as raw tables, runs sql/01_staging.sql, 02_firm_event_outcomes.sql and 03_kpis.sql for
30, 60 and 90-day windows, writes the KPI tables to output/sql/, and compares them with the tables in
output/ and output/insights.json (run src/build_model.py and src/analysis.py first). Exits non-zero on any mismatch.
"""
import csv
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA, SQL, OUT = ROOT / "data", ROOT / "sql", ROOT / "output"
AS_OF = "2026-10-14"
RAW = {"raw_events": "events.csv", "raw_firms": "firms.csv", "raw_attendees": "event_attendees.csv",
       "raw_meetings": "meetings.csv", "raw_stages": "opportunity_stage_history.csv"}


def build(window):
    con = sqlite3.connect(":memory:")
    for table, fname in RAW.items():
        with open(DATA / fname, newline="") as fh:
            rows = list(csv.reader(fh))
        cols = ", ".join(f'"{c}" TEXT' for c in rows[0])
        con.execute(f"CREATE TABLE {table} ({cols})")
        con.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(rows[0]))})", rows[1:])
    con.execute("CREATE TABLE params (as_of TEXT, window_days INTEGER)")
    con.execute("INSERT INTO params VALUES (?, ?)", (AS_OF, window))
    for f in sorted(SQL.glob("*.sql")):
        con.executescript(f.read_text())
    return con


def q(con, sql):
    return pd.read_sql_query(sql, con)


def main():
    fails, checks = [], []
    ins = json.loads((OUT / "insights.json").read_text())
    feo_py = pd.read_csv(OUT / "firm_event_outcomes.csv")
    (OUT / "sql").mkdir(exist_ok=True)

    def check(name, got, want):
        ok = json.loads(json.dumps(got, default=float), parse_float=lambda x: round(float(x), 4)) == \
             json.loads(json.dumps(want, default=float), parse_float=lambda x: round(float(x), 4))
        checks.append(name)
        print(("OK   " if ok else "FAIL ") + name, "" if ok else f"\n     sql={got}\n     python={want}")
        if not ok:
            fails.append(name)

    for w in (30, 60, 90):
        con = build(w)
        # row-level: the firm x event table must match the Python model exactly
        py = feo_py[(feo_py.window_days == w) & (feo_py.att_def == "confirmed")]
        cols = ["meetings_pre", "meetings_post", "days_to_first_meeting", "opps_created_pre", "opps_created_post", "opps_advanced_post"]
        s = q(con, "SELECT event_id, firm_id, attended, " + ", ".join(cols) + " FROM firm_event_outcomes")
        m = py.merge(s, on=["event_id", "firm_id"], suffixes=("_py", "_sql"))
        bad = sum((~((m[c + "_py"] == m[c + "_sql"]) | (m[c + "_py"].isna() & m[c + "_sql"].isna()))).sum() for c in cols)
        bad += int((m.attended_py.astype(bool) != m.attended_sql.astype(bool)).sum())
        check(f"[{w}d] firm x event table: {len(m)} rows, mismatched cells", bad, 0)

        d = ins[str(w)]
        f = q(con, "SELECT * FROM kpi_followup").iloc[0]
        check(f"[{w}d] follow-up rate and baseline", [f.followup_rate, f.baseline_rate], [d["followup_rate"], d["baseline_meeting_rate"]])
        t = q(con, "SELECT * FROM kpi_tier1").iloc[0]
        check(f"[{w}d] Tier 1 firms not met", [int(t.tier1_firms_missed), int(t.tier1_firms)], [d["tier1"]["missed_firms"], d["tier1"]["firms"]])
        c = q(con, "SELECT * FROM kpi_comparison").set_index("grp")
        check(f"[{w}d] meetings before/after: attending and comparison group",
              [int(c.loc["attended", "meetings_before"]), int(c.loc["attended", "meetings_after"]), int(c.loc["comparison", "meetings_before"]), int(c.loc["comparison", "meetings_after"])],
              [d["placebo_total"]["attended"]["pre"], d["placebo_total"]["attended"]["post"], d["placebo_total"]["clean"]["pre"], d["placebo_total"]["clean"]["post"]])
        g = q(con, "SELECT * FROM kpi_new_deal_groups").set_index("grp")
        pyg = {r["group"]: r for r in d["new_deal_did"]}
        check(f"[{w}d] new-deal share before/after by group", {k: [g.loc[k, "share_before"], g.loc[k, "share_after"]] for k in pyg},
              {k: [v["pre"], v["post"]] for k, v in pyg.items()})
        sc = q(con, "SELECT * FROM kpi_event_scorecard").set_index("event_id")
        check(f"[{w}d] extra firms met, beyond the season, cost per extra", {e: [int(sc.loc[e, "extra_firms"]), None if pd.isna(sc.loc[e, "extra_beyond_season"]) else sc.loc[e, "extra_beyond_season"],
                                                         None if pd.isna(sc.loc[e, "cost_per_extra_beyond_season"]) else sc.loc[e, "cost_per_extra_beyond_season"]] for e in sc.index},
              {e: [v["extra_firms"], v["extra_beyond_season"], v["cost_per_extra_beyond_season"]] for e, v in d["incremental_followup"].items()})
        o = q(con, "SELECT * FROM kpi_deal_origin").set_index("grp")
        check(f"[{w}d] mature-deal commit rate and similar-age deals, by origin",
              {k: [o.loc[k, "mature_commit_rate"], int(o.loc[k, "similar_age_deals"]), int(o.loc[k, "similar_age_committed"] or 0)] for k in o.index},
              {r["group"]: [r["mature_commit_rate"], d["age_matched_commit"][r["group"]]["n"], d["age_matched_commit"][r["group"]]["committed"]] for r in d["funnel_groups"]})
        cl = q(con, "SELECT * FROM kpi_call_list")
        ns = cl[cl.met_since.isna()]
        check(f"[{w}d] call list: firms, not met since, with live deals, $", [len(cl), len(ns), int((ns.live_deals > 0).sum()), float(ns.live_usd.sum())],
              [d["call_list_summary"][k] for k in ("firms", "not_met_since", "not_met_since_live", "not_met_since_live_usd")])
        if w == 60:
            for name in ("kpi_followup", "kpi_tier1", "kpi_comparison", "kpi_new_deal_groups", "kpi_event_scorecard", "kpi_deal_origin", "kpi_call_list"):
                q(con, f"SELECT * FROM {name}").to_csv(OUT / "sql" / f"{name}.csv", index=False)
            # staging tables must match the Python cleaned tables
            do = q(con, "SELECT opportunity_id, current_stage, max_stage_ord, amount_usd FROM dim_opportunity ORDER BY 1")
            dp = pd.read_csv(OUT / "dim_opportunity.csv")[["opportunity_id", "current_stage", "max_stage_ord", "amount_usd"]].sort_values("opportunity_id")
            check("staging: dim_opportunity (rows, current stage, furthest stage, amount)", do.values.tolist(), dp.values.tolist())
            fa = q(con, "SELECT event_id, firm_id, contacts, confirmed_contacts FROM fact_attendance ORDER BY 1, 2")
            fp = pd.read_csv(OUT / "fact_attendance.csv")[["event_id", "firm_id", "contacts", "confirmed_contacts"]].sort_values(["event_id", "firm_id"])
            check("staging: fact_attendance (rows and contact counts)", fa.values.tolist(), fp.values.tolist())
        con.close()

    print(f"\n{len(checks) - len(fails)} of {len(checks)} checks match. KPI tables written to output/sql/.")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
