"""Independent check of the Part 2 numbers, computed from the raw Dataset-2.xls (not from Prep)."""
import json, sys
from pathlib import Path
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
EXAM = Path(__file__).resolve().parents[2]
X = EXAM / "Data" / "Dataset-2.xls"
v = pd.read_excel(X, sheet_name="Dataset-2")
L = pd.read_excel(X, sheet_name="Video Length - Prerecorded")
v["Session"] = v["Session Name"].str.strip()
v = v.merge(L.rename(columns={"Session Name": "Session"}), on="Session", how="left")
v["Type"] = "Live lecture recording"
v.loc[v["Lecture/Exercise"].eq("Visual Analytics - exercises"), "Type"] = "Exercise recording"
v.loc[v["Video Length (Minutes)"].notna(), "Type"] = "Pre-recorded lecture"
v["Len"] = v["Video Length (Minutes)"].fillna(40)
v["Completion"] = (v["Minutes Viewed"] / v["Len"]).clip(upper=1)
v["Week"] = ((v.Timestamp.dt.normalize() - pd.Timestamp("2022-01-31")).dt.days // 7) + 1
R = {}
R["views"], R["students"], R["hours"] = len(v), v.UserName.nunique(), round(v["Minutes Viewed"].sum() / 60)
t = v.groupby("Type").agg(views=("UserName", "size"), students=("UserName", "nunique"), completion=("Completion", "mean"),
                          minutes=("Minutes Viewed", "sum"))
t["completion"] = (t.completion * 100).round(1); t["minutes"] = t.minutes.round()
R["by_type"] = t.to_dict("index")
order = ["Introduction to Data Visualization - Part 1", "Introduction to Data Visualization - Part 2", "Introduction to Data Visualization - Part 3",
         "Visual Perception - Part 1", "Visual Perception - Part 2", "Visual Perception - Part 3",
         "The Details of Information Design - Part 1", "The Details of Information Design - Part 2", "The Details of Information Design - Part 3",
         "Preattentive attributes - Part 1", "Preattentive attributes - Part 2", "Preattentive attributes - Part 3",
         "Visual Analytics and Dashboards - Part 1", "Visual Analytics and Dashboards - Part 2", "Colors (Part 1)", "Colors (Part 2)"]
p = v[v.Type.eq("Pre-recorded lecture")].groupby("Session").agg(students=("UserName", "nunique"), views=("UserName", "size"),
                                                                 completion=("Completion", "mean"), length=("Len", "first")).reindex(order)
p["completion"] = (p.completion * 100).round(1)
R["prerecorded"] = p.to_dict("index")
R["short_views"] = {"under_1_min": int((v["Minutes Viewed"] < 1).sum()), "zero": int((v["Minutes Viewed"] == 0).sum()),
                    "share_pct": round(100 * (v["Minutes Viewed"] < 1).mean(), 1)}
R["short_by_type_pct"] = (v.assign(s=v["Minutes Viewed"] < 1).groupby("Type").s.mean() * 100).round(1).to_dict()
wd = v.Timestamp.dt.day_name().value_counts()
R["weekday"] = wd.to_dict(); R["weekday_share_pct"] = (wd / len(v) * 100).round(1).to_dict()
R["weekend_share_pct"] = round(100 * v.Timestamp.dt.dayofweek.ge(5).mean(), 1)
h = v.Timestamp.dt.hour
R["hours_9_15_share_pct"] = round(100 * h.between(9, 15).mean(), 1)
R["evening_18_23_share_pct"] = round(100 * h.between(18, 23).mean(), 1)
R["night_0_6_share_pct"] = round(100 * h.between(0, 6).mean(), 1)
thu = v[v.Timestamp.dt.dayofweek.eq(3)]
R["thursday_9_12_views"] = int(thu.Timestamp.dt.hour.between(9, 12).sum())
R["week"] = v.groupby("Week").agg(views=("UserName", "size"), students=("UserName", "nunique")).to_dict("index")
pr = v.groupby("Study Program").agg(students=("UserName", "nunique"), views=("UserName", "size"), minutes=("Minutes Viewed", "sum"),
                                    prerec_share=("Type", lambda s: (s == "Pre-recorded lecture").mean()))
pr["min_per_student"] = (pr.minutes / pr.students).round(1)
pr["views_per_student"] = (pr.views / pr.students).round(1)
pr["prerec_share"] = (pr.prerec_share * 100).round(1)
R["programmes"] = pr.sort_values("min_per_student", ascending=False).drop(columns="minutes").to_dict("index")
lo = v.groupby("Location").agg(students=("UserName", "nunique"), views=("UserName", "size"), minutes=("Minutes Viewed", "sum"))
lo["min_per_student"] = (lo.minutes / lo.students).round(1)
R["location"] = lo.drop(columns="minutes").to_dict("index")
st = v.groupby("UserName").agg(minutes=("Minutes Viewed", "sum"), sessions=("Session", "nunique"))
R["students_watching_1_session_only"] = int((st.sessions == 1).sum())
R["median_minutes_per_student"] = round(float(st.minutes.median()), 1)
rep = v.groupby(["UserName", "Session"]).size()
R["repeat_pairs"] = int((rep > 1).sum()); R["repeat_share_of_pairs_pct"] = round(100 * (rep > 1).mean(), 1)
(EXAM / "2_DO_NOT_UPLOAD" / "Checks").mkdir(parents=True, exist_ok=True)
(EXAM / "2_DO_NOT_UPLOAD" / "Checks" / "insights_video.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
print(json.dumps(R, indent=1, default=str))
