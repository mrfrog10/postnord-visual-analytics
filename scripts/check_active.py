"""Check the P4 customer counts with the dashboard definition (any shipment in Jan-Aug) vs net revenue > 0."""
import sys
from pathlib import Path
import pandas as pd
from tableauhyperapi import HyperProcess, Telemetry, Connection
sys.stdout.reconfigure(encoding="utf-8")
EXAM = Path(__file__).resolve().parents[2]
P = EXAM / "Data" / "Prep_Output" / "DVA_PostNord_Sales.hyper"
with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(hp.endpoint, str(P)) as c:
        rows = c.execute_list_query('SELECT "Month","Main Customer Name","Revenue DKK" FROM "Extract"."Extract"')
d = pd.DataFrame(rows, columns=["Month", "Cust", "Rev"])
d["Month"] = pd.to_datetime(d.Month.astype(str)); d = d[d.Month.dt.month <= 8]; d["Y"] = d.Month.dt.year
print("unknown present:", (d.Cust == "Unknown customer").any(), "null names:", d.Cust.isna().sum())
for excl in (False, True):
    x = d[d.Cust.ne("Unknown customer")] if excl else d
    any_ = x.groupby("Y").Cust.nunique().to_dict()
    pos = x.groupby(["Y", "Cust"]).Rev.sum().gt(0).groupby("Y").sum().to_dict()
    print("excl unknown" if excl else "all", "any shipment:", any_, "net revenue>0:", pos)
s = d.groupby(["Cust", "Y"]).size().unstack(fill_value=0)
print("lost/retained/new (any shipment):", int(((s[2018] > 0) & (s[2019] == 0)).sum()), int(((s[2018] > 0) & (s[2019] > 0)).sum()), int(((s[2018] == 0) & (s[2019] > 0)).sum()))
