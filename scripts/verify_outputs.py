"""Checks every Prep output against the raw files. Run after the flows: python verify_outputs.py [names...]"""
import sys
from pathlib import Path
from tableauhyperapi import HyperProcess, Telemetry, Connection, TableName
sys.stdout.reconfigure(encoding="utf-8")
O = Path(__file__).resolve().parents[2] / "Data" / "Prep_Output"
T = '"Extract"."Extract"'
CHECKS = {
    "DVA_Master_Customers": [
        f'SELECT COUNT(*), COUNT(DISTINCT "Customer ID"), COUNT(DISTINCT "Main Customer") FROM {T}',
        f'SELECT "Industry Segment", COUNT(*) FROM {T} GROUP BY 1 ORDER BY 2 DESC'],
    "DVA_Master_PostCodes_DK": [
        f'SELECT COUNT(*), COUNT(DISTINCT "Postal Code") FROM {T}',
        f'SELECT "Region", COUNT(*) FROM {T} GROUP BY 1 ORDER BY 1',
        f"SELECT \"Postal Code\", \"City\", \"Municipality\" FROM {T} WHERE \"Municipality\" LIKE '%ø%' LIMIT 3",
        f"SELECT COUNT(*) FROM {T} WHERE \"City\" LIKE '%Ã%' OR \"Municipality\" LIKE '%Ã%' OR \"Region\" LIKE '%Ã%'"],
    "DVA_Video_Views": [
        f'SELECT COUNT(*), MIN("Course Week"), MAX("Course Week"), SUM("Minutes Viewed"), COUNT(DISTINCT "UserName") FROM {T}',
        f'SELECT "Session Type", COUNT(*), COUNT(DISTINCT "Session"), AVG("Completion") FROM {T} GROUP BY 1',
        f'SELECT "Weekday", "Weekday Nr", COUNT(*) FROM {T} GROUP BY 1,2 ORDER BY 2',
        f'SELECT "Course Week", MIN("View Date"), MAX("View Date"), COUNT(*) FROM {T} GROUP BY 1 ORDER BY 1'],
    "DVA_DDS_Shipments": [
        f'SELECT COUNT(*), SUM("Price_Paid"), COUNT(DISTINCT "Customer ID"), MIN("ShipmentDate"), MAX("ShipmentDate") FROM {T}',
        f'SELECT "Product Name", COUNT(*), SUM("Price_Paid") FROM {T} GROUP BY 1 ORDER BY 3 DESC',
        f'SELECT "Pallet Type", COUNT(*) FROM {T} GROUP BY 1 ORDER BY 2 DESC',
        f'SELECT COUNT(*) - COUNT(DISTINCT "Shipment Tracking Number") FROM {T}'],
    "DVA_PostNord_Sales": [
        f'SELECT COUNT(*), SUM("Shipments"), SUM("Revenue DKK"), COUNT(DISTINCT "Main Customer Name") FROM {T}',
        f'SELECT "Segment", SUM("Revenue DKK") FROM {T} GROUP BY 1 ORDER BY 2 DESC',
        f'SELECT "Origin Region", SUM("Revenue DKK") FROM {T} GROUP BY 1 ORDER BY 2 DESC',
        f'SELECT "Destination Region", SUM("Revenue DKK") FROM {T} GROUP BY 1 ORDER BY 2 DESC',
        f"SELECT SUM(\"Revenue DKK\") FROM {T} WHERE \"Main Customer Name\" IN ('Unknown customer','Not in master')"],
}
names = sys.argv[1:] or list(CHECKS)
with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    for n in names:
        p = O / f"{n}.hyper"
        if not p.exists():
            print("missing", n); continue
        with Connection(hp.endpoint, str(p)) as c:
            print(f"===== {n}  ({p.stat().st_size/1e6:.1f} MB)")
            print("   cols:", [str(x.name).strip('"') for x in c.catalog.get_table_definition(TableName("Extract", "Extract")).columns])
            for q in CHECKS[n]:
                for r in c.execute_list_query(q):
                    print("  ", r)
