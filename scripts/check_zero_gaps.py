"""Lester's feedback check: where would a chart show a gap (no rows) that really means zero?"""
import sys
from pathlib import Path
import pandas as pd
from tableauhyperapi import HyperProcess, Telemetry, Connection
sys.stdout.reconfigure(encoding="utf-8")
EXAM = Path(__file__).resolve().parents[2]
D = EXAM / "Data" / "Prep_Output"
with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(hp.endpoint, str(D / "DVA_Video_Views.hyper")) as c:
        v = pd.DataFrame(c.execute_list_query('SELECT "Course Week","Session Type","Weekday","Hour" FROM "Extract"."Extract"'),
                         columns=["Week", "Type", "Day", "Hour"])
    with Connection(hp.endpoint, str(D / "DVA_PostNord_Sales.hyper")) as c:
        s = pd.DataFrame(c.execute_list_query('SELECT "Segment","Product Name","Month",SUM("Revenue DKK") FROM "Extract"."Extract" GROUP BY 1,2,3'),
                         columns=["Seg", "Prod", "Month", "Rev"])
wk = v.groupby(["Week", "Type"]).size().unstack(fill_value=0)
print("V2 weekly views (0 = week with no views -> gap in a line chart):\n", wk.to_string())
hm = v.groupby(["Day", "Hour"]).size().unstack(fill_value=0)
print("V2 heatmap empty cells:", int((hm == 0).sum().sum()), "of", hm.size)
sp = s.groupby(["Seg", "Prod"]).Rev.sum().unstack()
print("P1 segment x product combinations with no rows (blank cells):", int(sp.isna().sum().sum()), "of", sp.size)
s["Month"] = pd.to_datetime(s.Month.astype(str))
pm = s.groupby(["Prod", "Month"]).Rev.sum().unstack(0)
print("P1 monthly revenue: months with no rows per product:", pm.isna().sum().to_dict())
