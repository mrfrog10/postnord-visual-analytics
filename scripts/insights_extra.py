"""Extra Part 1 checks: customer churn and acquisition, surcharges, pallet mix (from the Prep output, cross-checked totals)."""
import json, sys
from pathlib import Path
import pandas as pd
from tableauhyperapi import HyperProcess, Telemetry, Connection
sys.stdout.reconfigure(encoding="utf-8")
EXAM = Path(__file__).resolve().parents[2]
P = EXAM / "Data" / "Prep_Output" / "DVA_PostNord_Sales.hyper"
with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(hp.endpoint, str(P)) as c:
        rows = c.execute_list_query('SELECT "Month","Product Name","Pallet Type","Main Customer Name","Segment","Shipments","Revenue DKK","Freight DKK","Surcharges DKK","List Price DKK","Route (region)" FROM "Extract"."Extract"')
d = pd.DataFrame(rows, columns=["Month", "Product", "Pallet", "Cust", "Seg", "Ship", "Rev", "Freight", "Sur", "List", "Route"])
d["Month"] = pd.to_datetime(d.Month.astype(str)); d["Y"] = d.Month.dt.year; d["JA"] = d.Month.dt.month <= 8
R = {"total_rev": round(d.Rev.sum() / 1e6, 2)}
s = d.groupby("Product")[["Rev", "Freight", "Sur"]].sum()
s["sur_pct"] = (100 * s.Sur / s.Rev).round(1); R["surcharge_by_product"] = s.assign(Rev=(s.Rev / 1e6).round(1), Sur=(s.Sur / 1e6).round(1)).drop(columns="Freight").to_dict("index")
R["surcharge_total_mdkk"] = round(d.Sur.sum() / 1e6, 1); R["surcharge_total_pct"] = round(100 * d.Sur.sum() / d.Rev.sum(), 1)
sy = d[d.JA].groupby("Y")[["Sur", "Rev"]].sum(); R["surcharge_pct_by_year_janaug"] = (100 * sy.Sur / sy.Rev).round(1).to_dict()
pal = d[d.Product.eq("Pallet")].groupby("Pallet")[["Ship", "Rev"]].sum()
pal["rev_per_ship"] = (pal.Rev / pal.Ship).round(0); pal["ship_share"] = (100 * pal.Ship / pal.Ship.sum()).round(1); pal["Rev"] = (pal.Rev / 1e6).round(1)
R["pallet_mix"] = pal.to_dict("index")
py = d[d.Product.eq("Pallet") & d.JA].pivot_table(index="Pallet", columns="Y", values="Ship", aggfunc="sum")
R["pallet_ship_share_by_year_janaug"] = (100 * py / py.sum()).round(1).to_dict()
# customers active Jan-Aug each year
act = d[d.JA & d.Cust.ne("Unknown customer")].groupby(["Cust", "Y"]).Rev.sum().unstack(fill_value=0)
R["active_customers_janaug"] = {int(y): int((act[y] > 0).sum()) for y in act.columns}
lost19 = act[(act[2018] > 0) & (act[2019] == 0)]; new19 = act[(act[2018] == 0) & (act[2019] > 0)]
lost18 = act[(act[2017] > 0) & (act[2018] == 0)]; new18 = act[(act[2017] == 0) & (act[2018] > 0)]
R["lost_2019"] = {"n": len(lost19), "rev2018_mdkk": round(lost19[2018].sum() / 1e6, 2)}
R["new_2019"] = {"n": len(new19), "rev2019_mdkk": round(new19[2019].sum() / 1e6, 2)}
R["lost_2018"] = {"n": len(lost18), "rev2017_mdkk": round(lost18[2017].sum() / 1e6, 2)}
R["new_2018"] = {"n": len(new18), "rev2018_mdkk": round(new18[2018].sum() / 1e6, 2)}
both = act[(act[2018] > 0) & (act[2019] > 0)]
R["retained_2019"] = {"n": len(both), "rev2018_mdkk": round(both[2018].sum() / 1e6, 2), "rev2019_mdkk": round(both[2019].sum() / 1e6, 2)}
R["bridge_2018_to_2019_janaug_mdkk"] = {"2018": round(act[2018].sum() / 1e6, 2), "lost": round(-lost19[2018].sum() / 1e6, 2),
                                        "retained_change": round((both[2019].sum() - both[2018].sum()) / 1e6, 2),
                                        "new": round(new19[2019].sum() / 1e6, 2), "2019": round(act[2019].sum() / 1e6, 2)}
segy = d[d.JA].pivot_table(index="Seg", columns="Y", values="Rev", aggfunc="sum") / 1e6
segy["g19"] = (100 * (segy[2019] / segy[2018] - 1)).round(1)
R["segment_janaug_mdkk"] = segy.round(1).sort_values(2019, ascending=False).head(6).to_dict("index")
out = EXAM / "2_DO_NOT_UPLOAD" / "Checks" / "insights_extra.json"
out.write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
print(json.dumps(R, indent=1, default=str))
