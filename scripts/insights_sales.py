"""Independent check of the Part 1 numbers from the raw DDS files (via a pickle cache) and the raw master data."""
import json, sys
from pathlib import Path
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
EXAM = Path(__file__).resolve().parents[2]
CACHE = Path(sys.argv[1])
a = pd.read_pickle(CACHE)
R = {}
# ---- duplicates: identical apart from the file they came from?
key = [c for c in a.columns if c != "FileName"]
dup_all = a.duplicated(subset=key, keep=False)
R["rows_raw"] = len(a)
R["rows_identical_except_file"] = int(a.duplicated(subset=key).sum())
d = a[dup_all]
R["dup_in_two_files_example"] = d.sort_values(key[:10]).head(2)[["Shipment Tracking Number", "ShipmentDate", "FileName", "Price_Paid"]].astype(str).to_dict("records")
a = a.drop_duplicates(subset=key)
R["rows_after_dedup"] = len(a)
R["pkk_by_product"] = a[a["Parcel/Pallet type"].eq("PKK")].Product.value_counts().to_dict()
R["pallet_types_for_L"] = a[a.Product.eq("L")]["Parcel/Pallet type"].fillna("blank").value_counts().to_dict()
names = {"I": "Innight", "G": "Groupage", "L": "Pallet", "R": "Road Freight"}
a["Product Name"] = a.Product.map(names)
a["Customer ID"] = a.Customer_ID.fillna("UNKNOWN")
a["Year"] = a.ShipmentDate.dt.year
a["JanAug"] = a.ShipmentDate.dt.month <= 8
m = pd.read_excel(EXAM / "Data" / "Master_Data" / "ADS_DDS_RF_CustomerNumbers_MasterData.xlsx", sheet_name="DDS")
a = a.merge(m[["Customer ID", "Main Customer", "Industry Level 1", "Industry Level 2"]], on="Customer ID", how="left")
a["Main Customer"] = a["Main Customer"].where(a["Customer ID"].ne("UNKNOWN"), "Unknown customer").fillna("Not in master")
a["Segment"] = a["Industry Level 1"].where(a["Customer ID"].ne("UNKNOWN"), "Unknown customer").fillna("Not in master")
rev = a.Price_Paid.sum()
R["revenue_total_mdkk"] = round(rev / 1e6, 1)
R["shipments"] = len(a)
R["main_customers"] = int(a["Main Customer"].nunique())
p = a.groupby("Product Name").agg(rev=("Price_Paid", "sum"), ship=("Price_Paid", "size"), base=("Base_Price", "sum"), freight=("Freight", "sum"))
p["share_pct"] = (100 * p.rev / rev).round(1); p["rev_per_shipment"] = (p.rev / p.ship).round(0)
p["discount_pct"] = (100 * (1 - p.rev / p.base)).round(1); p["surcharge_share_pct"] = (100 * (1 - p.freight / p.rev)).round(1)
p["rev"] = (p.rev / 1e6).round(1)
R["products"] = p.drop(columns=["base", "freight"]).to_dict("index")
ja = a[a.JanAug].pivot_table(index="Product Name", columns="Year", values="Price_Paid", aggfunc="sum") / 1e6
ja["g18"] = (100 * (ja[2018] / ja[2017] - 1)).round(1); ja["g19"] = (100 * (ja[2019] / ja[2018] - 1)).round(1)
R["janaug_by_product_mdkk"] = ja.round(1).to_dict("index")
tot = a[a.JanAug].groupby("Year").Price_Paid.sum() / 1e6
R["janaug_total_mdkk"] = tot.round(1).to_dict()
R["janaug_total_growth_pct"] = {"2018": round(100 * (tot[2018] / tot[2017] - 1), 1), "2019": round(100 * (tot[2019] / tot[2018] - 1), 1),
                                "2019_without_road_freight": round(100 * (a[a.JanAug & a.Product.ne("R") & a.Year.eq(2019)].Price_Paid.sum() / 1e6 / tot[2018] - 1), 1)}
s = a.pivot_table(index="Segment", columns="Product Name", values="Price_Paid", aggfunc="sum", fill_value=0) / 1e6
s["Total"] = s.sum(axis=1); s = s.sort_values("Total", ascending=False)
R["segment_by_product_mdkk"] = s.round(1).to_dict("index")
R["segment_share_pct"] = (100 * s.Total / s.Total.sum()).round(1).to_dict()
mix = a.pivot_table(index="Product Name", columns="Segment", values="Price_Paid", aggfunc="sum", fill_value=0)
R["product_top_segment_share_pct"] = {pn: {"segment": mix.loc[pn].idxmax(), "share": round(100 * mix.loc[pn].max() / mix.loc[pn].sum(), 1)} for pn in mix.index}
c = a.groupby("Main Customer").agg(rev=("Price_Paid", "sum"), seg=("Segment", "first"), products=("Product Name", "nunique")).sort_values("rev", ascending=False)
c["share_pct"] = (100 * c.rev / rev).round(2); c["rev"] = (c.rev / 1e6).round(2)
R["top15_customers"] = c.head(15).to_dict("index")
cc = c.rev.cumsum() / c.rev.sum()
R["concentration"] = {"top10_pct": round(100 * cc.iloc[9], 1), "top20_pct": round(100 * cc.iloc[19], 1), "top50_pct": round(100 * cc.iloc[49], 1),
                      "customers_for_80pct": int((cc < 0.8).sum() + 1), "customers": len(c)}
R["single_product_customers_pct_of_revenue"] = round(100 * c[c.products == 1].rev.sum() / c.rev.sum(), 1)
R["customers_by_products"] = c.products.value_counts().sort_index().to_dict()
cy = a[a.JanAug].pivot_table(index="Main Customer", columns="Year", values="Price_Paid", aggfunc="sum", fill_value=0) / 1e6
cy["chg"] = cy[2019] - cy[2018]
R["top_decliners_2018_2019_janaug_mdkk"] = cy.sort_values("chg").head(8).round(2).to_dict("index")
R["top_growers_2018_2019_janaug_mdkk"] = cy.sort_values("chg", ascending=False).head(8).round(2).to_dict("index")
R["lost_customers_2019"] = {"count": int(((cy[2018] > 0) & (cy[2019] == 0)).sum()), "rev_2018_mdkk": round(cy[(cy[2018] > 0) & (cy[2019] == 0)][2018].sum(), 2)}
R["destination_country_pct"] = (100 * a.groupby("ConsigneeCountryCode").Price_Paid.sum() / rev).round(1).to_dict()
R["destination_country_rev_per_shipment"] = (a.groupby("ConsigneeCountryCode").Price_Paid.sum() / a.groupby("ConsigneeCountryCode").size()).round(0).to_dict()
g = pd.read_excel(EXAM / "Data" / "Master_Data" / "New_PostCodes_Data_DK" / "DK_Geonames.xlsx")
g = g.groupby("Postal Code").agg(Region=("Column4", "first"), City=("Column3", "first")).reset_index()
fix = lambda s: s.str.replace("Ã¸", "ø").str.replace("Ã¦", "æ").str.replace("Ã¥", "å").str.replace("Ã˜", "Ø").str.replace("Region ", "")
g["Region"] = fix(g.Region); g["City"] = fix(g.City)
a = a.merge(g.rename(columns={"Postal Code": "Consignor Location Nr", "Region": "O_Region", "City": "O_City"}), on="Consignor Location Nr", how="left")
dk = a.ConsigneeCountryCode.eq("DK")
a = a.merge(g.rename(columns={"Postal Code": "Consignee Location Nr", "Region": "D_Region0", "City": "D_City0"}), on="Consignee Location Nr", how="left")
a["D_Region"] = a.D_Region0.where(dk, a.ConsigneeCountryCode.map({"SE": "Sweden", "NO": "Norway"}))
R["origin_postcode_match_pct"] = round(100 * a.O_Region.notna().mean(), 2)
R["dest_dk_postcode_match_pct"] = round(100 * a[dk].D_Region0.notna().mean(), 2)
R["origin_region_pct"] = (100 * a.groupby(a.O_Region.fillna("Unknown")).Price_Paid.sum() / rev).round(1).to_dict()
R["dest_region_pct"] = (100 * a.groupby(a.D_Region.fillna("Unknown")).Price_Paid.sum() / rev).round(1).to_dict()
a["Route"] = a.O_Region.fillna("Unknown") + " to " + a.D_Region.fillna("Unknown")
rt = a.groupby("Route").agg(rev=("Price_Paid", "sum"), ship=("Price_Paid", "size"))
rt["share_pct"] = (100 * rt.rev / rev).round(1); rt["rev"] = (rt.rev / 1e6).round(1)
R["top_routes"] = rt.sort_values("rev", ascending=False).head(12).to_dict("index")
R["top_origin_cities"] = (a.groupby("O_City").Price_Paid.sum().sort_values(ascending=False).head(8) / 1e6).round(1).to_dict()
mon = a.groupby(a.ShipmentDate.dt.month).Price_Paid.sum()
R["month_index_avg100"] = (100 * mon / mon.mean()).round(0).to_dict()
R["zero_price_by_product"] = a[a.Price_Paid.eq(0)]["Product Name"].value_counts().to_dict()
seg_disc = a.groupby("Segment").agg(rev=("Price_Paid", "sum"), base=("Base_Price", "sum"))
R["discount_by_segment_pct"] = (100 * (1 - seg_disc.rev / seg_disc.base)).round(1).sort_values().to_dict()
R["road_freight_monthly_mdkk"] = (a[a.Product.eq("R")].groupby(a.ShipmentDate.dt.month).Price_Paid.sum() / 1e6).round(2).to_dict()
R["road_freight_rev_per_shipment"] = round(a[a.Product.eq("R")].Price_Paid.mean())
R["road_freight_dest_pct"] = (100 * a[a.Product.eq("R")].groupby("D_Region").Price_Paid.sum() / a[a.Product.eq("R")].Price_Paid.sum()).round(1).to_dict()
out = EXAM / "2_DO_NOT_UPLOAD" / "Checks" / "insights_sales.json"
out.write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
print(json.dumps(R, indent=1, default=str))
