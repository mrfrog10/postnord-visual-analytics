"""Part 1 workbook: DVA_PostNord_Dashboard.twbx (four dashboards for the sales / product manager)."""
import sys
import zipfile
from pathlib import Path
from tableauhyperapi import HyperProcess, Telemetry, Connection, TableName
from twb import Workbook, CB, E

EXAM = Path(__file__).resolve().parents[2]
HYPER = EXAM / "Data" / "Prep_Output" / "DVA_PostNord_Sales.hyper"
OUT = EXAM / "1_UPLOAD_TO_WISEFLOW" / "DVA_PostNord_Dashboard.twbx"

# read the real column names and types from the Prep output
TYPES = {"TEXT": "string", "DATE": "date", "DOUBLE": "real", "BIG_INT": "integer", "INT": "integer", "TIMESTAMP": "datetime"}
with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(hp.endpoint, str(HYPER)) as c:
        FIELDS = [(str(x.name).strip('"'), TYPES[str(x.type).split("(")[0]]) for x in c.catalog.get_table_definition(TableName("Extract", "Extract")).columns]

JA = "MONTH([Month]) <= 8"
R18, R19 = f"IF YEAR([Month]) = 2018 AND {JA} THEN [Revenue DKK] END", f"IF YEAR([Month]) = 2019 AND {JA} THEN [Revenue DKK] END"
CALCS = [
    ("Revenue (M DKK)", "real", "measure", "quantitative", "[Revenue DKK] / 1000000", "n#,##0.0"),
    # Lester's feedback: a segment that buys nothing of a product has revenue 0, not a blank. LOOKUP fills the missing cells, ZN makes them 0.
    ("Revenue incl zero (M DKK)", "real", "measure", "quantitative", "ZN(LOOKUP(SUM([Revenue (M DKK)]), 0))", "n#,##0.0"),
    ("Year", "string", "dimension", "nominal", "STR(YEAR([Month]))"),
    ("Customers", "integer", "measure", "quantitative", "COUNTD([Main Customer Name])", "n#,##0"),
    # KPI: named customer groups only, without the "Unknown customer" and "Not in master" placeholder groups
    ("Named customers", "integer", "measure", "quantitative", "COUNTD(IF STARTSWITH([Main Customer Name], 'Customer ') THEN [Main Customer Name] END)", "n#,##0"),
    ("Revenue per Shipment", "real", "measure", "quantitative", "SUM([Revenue DKK]) / SUM([Shipments])", "n#,##0"),
    ("Discount vs List Price", "real", "measure", "quantitative", "SUM([Discount DKK]) / SUM([List Price DKK])", "p0%"),
    ("Growth 2019 vs 2018 (Jan-Aug)", "real", "measure", "quantitative", f"SUM({R19}) / SUM({R18}) - 1", "p0%"),
    ("Change 2019 vs 2018 Jan-Aug (M DKK)", "real", "measure", "quantitative", f"(ZN(SUM({R19})) - ZN(SUM({R18}))) / 1000000", "n#,##0.0"),
    ("Customer Status 2019", "string", "dimension", "nominal",
     f"IF [Main Customer Name] = 'Unknown customer' THEN '5. Unknown customer' "
     f"ELSEIF {{ FIXED [Main Customer Name] : SUM({R18}) }} > 0 AND {{ FIXED [Main Customer Name] : SUM({R19}) }} > 0 THEN '2. Retained' "
     f"ELSEIF {{ FIXED [Main Customer Name] : SUM({R18}) }} > 0 THEN '1. Lost in 2019' "
     f"ELSEIF {{ FIXED [Main Customer Name] : SUM({R19}) }} > 0 THEN '3. New in 2019' ELSE '4. Not active Jan-Aug 2018/19' END"),
    ("Customers Jan-Aug", "integer", "measure", "quantitative", (f"COUNTD(IF {JA} AND [Main Customer Name] <> 'Unknown customer' AND "
                                                                         f"{{ FIXED [Main Customer Name], YEAR([Month]) : SUM(IF {JA} THEN [Revenue DKK] END) }} > 0 THEN [Main Customer Name] END)"), "n#,##0"),
    ("Surcharge Share", "real", "measure", "quantitative", "SUM([Surcharges DKK]) / SUM([Revenue DKK])", "p0%"),
    ("Customer Size", "string", "dimension", "nominal",
     "IF { FIXED [Main Customer Name] : SUM([Revenue DKK]) } >= 10000000 THEN '1. 10M DKK or more' "
     "ELSEIF { FIXED [Main Customer Name] : SUM([Revenue DKK]) } >= 1000000 THEN '2. 1-10M DKK' "
     "ELSEIF { FIXED [Main Customer Name] : SUM([Revenue DKK]) } >= 100000 THEN '3. 0.1-1M DKK' ELSE '4. Under 0.1M DKK' END"),
]
w = Workbook("PostNord Sales", "DVA_PostNord_Sales.hyper", FIELDS, CALCS, geo=["Origin Lat", "Origin Long", "Destination Lat", "Destination Long"])
r, inst = w.ref, w.inst
PRODUCTS = [("Pallet", CB["blue"]), ("Groupage", CB["orange"]), ("Innight", CB["lightblue"]), ("Road Freight", CB["darkorange"])]
SEGCOL = [("Wholesaler", CB["blue"]), ("Transport", CB["orange"]), ("Retail", CB["lightblue"]), ("Publisher", CB["darkorange"]),
          ("Service & Consulting", CB["grey"]), ("Missing SNI", CB["lightgrey"]), ("Financial", CB["paleblue"]), ("Public Sector", CB["lightorange"]),
          ("Industry", CB["darkgrey"]), ("Not in master", "#d3d3d3"), ("Unknown customer", "#d3d3d3"), ("Utilities", "#d3d3d3"), ("Others", "#d3d3d3")]
P, S, Y = "none:Product Name:nk", "none:Segment:nk", "none:Year:nk"
I_P, I_S, I_Y = inst("Product Name", "None", P, "nominal"), inst("Segment", "None", S, "nominal"), inst("Year", "None", Y, "nominal")
F_P, F_S, F_Y = w.all_filter(r(P), P, 1), w.all_filter(r(S), S, 2), w.all_filter(r(Y), Y, 3)
RTF, MCF = "none:Route (region):nk", "none:Main Customer Name:nk"
F_RT, F_MC = w.all_filter(r(RTF), RTF, 4), w.all_filter(r(MCF), MCF, 5)
I_RT, I_MC = inst("Route (region)", "None", RTF, "nominal"), inst("Main Customer Name", "None", MCF, "nominal")
U_ = lambda n: inst(n, "User", f"usr:{n}:qk", "quantitative")
SUMR = inst("Revenue (M DKK)", "Sum", "sum:Revenue (M DKK):qk", "quantitative")
REV = r("sum:Revenue (M DKK):qk")
RZ = r("usr:Revenue incl zero (M DKK):qk")
pcol, scol = w.color_map(r(P), PRODUCTS), w.color_map(r(S), SEGCOL)
ax = lambda f, label, scope="cols": f'<style-rule element="axis">{w.axis_title(f, label, scope)}</style-rule>'
hide_hdr = lambda f: f'<style-rule element="header"><format attr="height" field="{f}" value="0" /></style-rule>'


def kpi(name, title, measure_inst, measure_ref, fmt_note):
    w.sheet(name, title, fmt_note, [I_P, I_S, I_Y, measure_inst], rows="", cols="", mark="Text",
            encodings=f'<text column="{measure_ref}" />', filters=F_P + F_S + F_Y,
            pane_style='<format attr="mark-labels-show" value="true" />',
            style=f'<style-rule element="cell"><format attr="font-size" value="20" /><format attr="font-weight" value="bold" />'
                  f'<format attr="color" value="{CB["blue"]}" /><format attr="text-align" value="center" /></style-rule>')
    # one title line ("Revenue (million DKK, price paid)") instead of title + subtitle, so the number has room in the tile
    x = w.sheets[-1]
    i, j = x.find("<title>"), x.find("</title>")
    w.sheets[-1] = (x[:i] + f'<title><formatted-text><run bold="true" fontsize="11">{E(title)}</run>'
                    f'<run fontcolor="#555555" fontsize="9"> ({E(fmt_note)})</run></formatted-text>' + x[j:])


# ================================================================ P1 products and segments
kpi("P1 KPI revenue", "Revenue", SUMR, REV, "million DKK, price paid")
kpi("P1 KPI shipments", "Shipments", inst("Shipments", "Sum", "sum:Shipments:qk", "quantitative"), r("sum:Shipments:qk"), "invoiced shipments")
kpi("P1 KPI customers", "Main customers", U_("Named customers"), r("usr:Named customers:qk"), "customer groups")
kpi("P1 KPI per shipment", "Revenue per shipment", U_("Revenue per Shipment"), r("usr:Revenue per Shipment:qk"), "DKK, average")

w.sheet("P1 Segment by product", "Wholesalers bring half of all revenue; Transport leads Groupage and Road Freight",
        "Revenue (million DKK) by segment and product; 0.0 = under 0.05 million, including none. Darker = more revenue.",
        [I_P, I_S, I_Y, SUMR, '<column-instance column="[Revenue incl zero (M DKK)]" derivation="User" name="[usr:Revenue incl zero (M DKK):qk]" '
                              'pivot="key" type="quantitative"><table-calc ordering-type="Columns" /></column-instance>'],
        rows=r(S), cols=r(P), mark="Square",
        encodings=f'<color column="{RZ}" /><text column="{RZ}" />', filters=F_P + F_S + F_Y,
        sorts=w.computed_sort(r(S), REV) + w.manual_sort(r(P), [p for p, _ in PRODUCTS]),
        style=f'<style-rule element="mark"><encoding attr="color" field="{RZ}" palette="blue_10_0" type="interpolated" /></style-rule>' + w.header_width(r(S), 150),
        show_labels=True)

mon = "tmn:Month:qk"
w.sheet("P1 Monthly revenue", "Pallet and Groupage grow; all products dip every December",
        "Monthly revenue (million DKK) by product, Jan 2017 to Aug 2019. Road Freight data starts in May 2019.",
        [I_P, I_S, inst("Month", "Month-Trunc", mon, "quantitative"), SUMR], rows=REV, cols=r(mon), mark="Line",
        encodings=f'<color column="{r(P)}" />', filters=F_P + F_S,
        style=ax(REV, "Revenue (million DKK)", "rows") + pcol + f'<style-rule element="axis">{w.axis_title(r(mon), "Month", "cols")}</style-rule>')

G = "usr:Growth 2019 vs 2018 (Jan-Aug):qk"
w.sheet("P1 Growth by product", "Innight fell 18% while Groupage grew 24%",
        "Revenue growth, January-August 2019 vs January-August 2018 (same months, so seasonality is removed). Road Freight has no 2018 data.",
        [I_P, I_S, U_("Growth 2019 vs 2018 (Jan-Aug)")], rows=r(P), cols=r(G), mark="Bar",
        encodings=f'<color column="{r(P)}" />', filters=F_P + F_S + w.member_filter(r(P), P, ["Pallet", "Groupage", "Innight"]),
        sorts=w.manual_sort(r(P), [p for p, _ in PRODUCTS]), style=ax(r(G), "Growth, Jan-Aug 2019 vs 2018") + pcol + w.header_width(r(P), 110), show_labels=True)

# ================================================================ P2 customers and geography
MC = "none:Main Customer Name:nk"
w.sheet("P2 Top customers", "The top 10 customers bring 48% of revenue",
        "Revenue (million DKK) of the 15 largest main customers (customer IDs grouped by the master data), coloured by segment.",
        [I_P, I_S, I_Y, inst("Main Customer Name", "None", MC, "nominal"), SUMR], rows=r(MC), cols=REV, mark="Bar",
        encodings=f'<color column="{r(S)}" />',
        filters=F_P + F_S + F_Y + w.top_n(r(MC), MC, 15, "SUM([Revenue (M DKK)])"),
        sorts=w.computed_sort(r(MC), REV), style=ax(REV, "Revenue (million DKK)") + scol + w.header_width(r(MC), 150), show_labels=True)

CS = "none:Customer Size:nk"
w.sheet("P2 Customer size", "60 customers make up 80% of revenue",
        "Revenue (million DKK) by customer size band; labels show the number of main customers in each band.",
        [I_P, I_S, I_Y, inst("Customer Size", "None", CS, "nominal"), SUMR, U_("Customers")], rows=r(CS), cols=REV, mark="Bar",
        encodings=f'<text column="{r("usr:Customers:qk")}" />', filters=F_P + F_S + F_Y,
        style=ax(REV, "Revenue (million DKK)") + w.header_width(r(CS), 175), pane_style=f'<format attr="mark-color" value="{CB["blue"]}" />', show_labels=True)

DC, LAT, LON = "none:Destination City:nk", "avg:Destination Lat:qk", "avg:Destination Long:qk"
w.sheet("P2 Delivery map", "Deliveries are spread over all of Denmark",
        "Revenue (million DKK) by delivery town in Denmark (circle size). Sweden and Norway are shown in the region chart.",
        [I_P, I_S, I_Y, inst("Destination City", "None", DC, "nominal"), inst("Destination Lat", "Avg", LAT, "quantitative"),
         inst("Destination Long", "Avg", LON, "quantitative"), SUMR, inst("ConsigneeCountryCode", "None", "none:ConsigneeCountryCode:nk", "nominal")],
        rows=r(LAT), cols=r(LON), mark="Circle", encodings=f'<size column="{REV}" /><lod column="{r(DC)}" />',
        filters=F_P + F_S + F_Y + w.member_filter(r("none:ConsigneeCountryCode:nk"), "none:ConsigneeCountryCode:nk", ["DK"])
                + f'<filter class="quantitative" column="{r(LAT)}" included-values="non-null" />',  # one town without coordinates
        pane_style=f'<format attr="mark-color" value="{CB["blue"]}" /><format attr="mark-transparency" value="150" />', mapsource=True)

DR = "none:Destination Region:nk"
w.sheet("P2 Delivery regions", "Sweden takes 17% of revenue, as much as a Danish region",
        "Revenue (million DKK) by delivery region, coloured by product.",
        [I_P, I_S, I_Y, inst("Destination Region", "None", DR, "nominal"), SUMR], rows=r(DR), cols=REV, mark="Bar",
        encodings=f'<color column="{r(P)}" />', filters=F_P + F_S + F_Y, sorts=w.computed_sort(r(DR), REV),
        style=ax(REV, "Revenue (million DKK)") + pcol + w.header_width(r(DR), 150))

# ================================================================ P3 routes and pricing
RT = "none:Route (region):nk"
w.sheet("P3 Top routes", "Syddanmark to Sweden is the most valuable route",
        "Revenue (million DKK) of the 12 largest pickup-to-delivery region pairs, coloured by product.",
        [I_P, I_S, I_Y, I_MC, inst("Route (region)", "None", RT, "nominal"), SUMR], rows=r(RT), cols=REV, mark="Bar",
        encodings=f'<color column="{r(P)}" />', filters=F_P + F_S + F_Y + F_MC + w.top_n(r(RT), RT, 12, "SUM([Revenue (M DKK)])"),
        sorts=w.computed_sort(r(RT), REV), style=ax(REV, "Revenue (million DKK)") + pcol + w.header_width(r(RT), 240))

D = "usr:Discount vs List Price:qk"
w.sheet("P3 Discount", "Groupage sells at 62% below list price",
        "Discount = 1 - price paid / list price (Base_Price, the standard price sheet), by product.",
        [I_P, I_S, I_Y, I_RT, I_MC, U_("Discount vs List Price")], rows=r(P), cols=r(D), mark="Bar", encodings=f'<color column="{r(P)}" />',
        filters=F_P + F_S + F_Y + F_RT + F_MC, sorts=w.manual_sort(r(P), [p for p, _ in PRODUCTS]), style=ax(r(D), "Discount from list price") + pcol + w.header_width(r(P), 110),
        show_labels=True)

MV = "usr:Change 2019 vs 2018 Jan-Aug (M DKK):qk"
w.sheet("P3 Customer movers", "A few customers drive most of the change",
        "Change in revenue (million DKK), Jan-Aug 2019 vs Jan-Aug 2018: the 12 main customers that moved most, up or down.",
        [I_P, I_S, I_RT, inst("Main Customer Name", "None", MC, "nominal"), U_("Change 2019 vs 2018 Jan-Aug (M DKK)")],
        rows=r(MC), cols=r(MV), mark="Bar", encodings=f'<color column="{r(MV)}" />',
        # product, segment and route as context filters, so the top 12 are recomputed for the chosen route
        filters=(F_P + F_S + F_RT).replace("<filter ", '<filter context="true" ')
                + w.top_n(r(MC), MC, 12, f"ABS([Change 2019 vs 2018 Jan-Aug (M DKK)])"),
        sorts=w.computed_sort(r(MC), r(MV)),
        style=ax(r(MV), "Change in revenue (million DKK)") + w.header_width(r(MC), 150) +
              f'<style-rule element="mark"><encoding attr="color" field="{r(MV)}" palette="orange_blue_diverging_10_0" type="interpolated" /></style-rule>',
        show_labels=True)

# ---- route and customer history (actual revenue only; no forecast: 32 months are too little history to forecast reliably)
w.sheet("P3 History", "Revenue history of the selected route or customer",
        "Monthly revenue (million DKK) by product, Jan 2017 - Aug 2019. Click a route, or pick a route or customer above, to see its history.",
        [I_P, I_S, I_RT, I_MC, inst("Month", "Month-Trunc", "tmn:Month:qk", "quantitative"), SUMR], rows=REV, cols=r("tmn:Month:qk"), mark="Line",
        encodings=f'<color column="{r(P)}" />', filters=F_P + F_S + F_RT + F_MC,
        style=ax(REV, "Revenue (million DKK)", "rows") + pcol + f'<style-rule element="axis">{w.axis_title(r("tmn:Month:qk"), "Month", "cols")}</style-rule>')

# ================================================================ P4 customer health and pricing
CS19 = "none:Customer Status 2019:nk"
w.sheet("P4 Customer status", "Existing customers drive growth; lost customers cost only 3.8 million DKK",
        "Change in revenue, Jan-Aug 2019 vs Jan-Aug 2018 (million DKK), by customer status. Labels: number of main customers.",
        [I_P, I_S, inst("Customer Status 2019", "None", CS19, "nominal"), U_("Change 2019 vs 2018 Jan-Aug (M DKK)"), U_("Customers")],
        rows=r(CS19), cols=r(MV), mark="Bar", encodings=f'<text column="{r("usr:Customers:qk")}" />',
        filters=F_P + F_S + w.member_filter(r(CS19), CS19, ["1. Lost in 2019", "2. Retained", "3. New in 2019"]),
        style=ax(r(MV), "Change in revenue (million DKK)") + w.header_width(r(CS19), 130),
        pane_style=f'<format attr="mark-color" value="{CB["blue"]}" />', show_labels=True)
w.sheet("P4 Active customers", "Fewer customers each year, while revenue grows",
        "Main customers with revenue above zero in January-August of each year (unknown customers excluded).",
        [I_P, I_S, I_Y, U_("Customers Jan-Aug")], rows=r("usr:Customers Jan-Aug:qk"), cols=r(Y), mark="Bar",
        encodings=f'<text column="{r("usr:Customers Jan-Aug:qk")}" />', filters=F_P + F_S,
        style=ax(r("usr:Customers Jan-Aug:qk"), "Main customers (Jan-Aug)", "rows") + w.label_horizontal(r(Y)),
        pane_style=f'<format attr="mark-color" value="{CB["blue"]}" />', show_labels=True)
SS = "usr:Surcharge Share:qk"
w.sheet("P4 Surcharges", "Surcharges add 16% to Pallet and Groupage revenue",
        "Surcharges (price paid minus freight) as a share of price paid, by product.",
        [I_P, I_S, I_Y, U_("Surcharge Share")], rows=r(P), cols=r(SS), mark="Bar", encodings=f'<color column="{r(P)}" />',
        filters=F_P + F_S + F_Y, sorts=w.manual_sort(r(P), [p for p, _ in PRODUCTS]),
        style=ax(r(SS), "Surcharges as share of revenue") + pcol + w.header_width(r(P), 110), show_labels=True)
PT = "none:Pallet Type:nk"
w.sheet("P4 Pallet mix", "Full pallets are 66% of pallet shipments and 80% of pallet revenue",
        "Pallet product only: revenue (million DKK) by pallet type; labels show revenue per shipment (DKK). PLL full, HPL half, QPL quarter, SPL special.",
        [I_P, I_S, I_Y, inst("Pallet Type", "None", PT, "nominal"), SUMR, U_("Revenue per Shipment")], rows=r(PT), cols=REV, mark="Bar",
        encodings=f'<text column="{r("usr:Revenue per Shipment:qk")}" />',
        filters=F_P + F_S + F_Y + w.member_filter(r(PT), PT, ["PLL", "HPL", "QPL", "SPL"]), sorts=w.computed_sort(r(PT), REV),
        style=ax(REV, "Revenue (million DKK)") + w.header_width(r(PT), 70), pane_style=f'<format attr="mark-color" value="{CB["blue"]}" />', show_labels=True)

# ================================================================ dashboards (tiled, no overlaps)
def filters(sheet):
    return (w.qfilter(10, 52000, 0, 16000, 9000, sheet, r(Y)) + w.qfilter(11, 68000, 0, 16000, 9000, sheet, r(P))
            + w.qfilter(12, 84000, 0, 16000, 9000, sheet, r(S)))

k = "P1 Segment by product"
w.dashboard2("P1 Products and segments", "Which products earn, and for which industries",
             "DDS data, Jan 2017 - Aug 2019. Revenue = price paid. Click a cell to filter the other charts.", 52000,
             filters(k)
             + w.view(20, 0, 9000, 25000, 14000, "P1 KPI revenue") + w.view(21, 25000, 9000, 25000, 14000, "P1 KPI shipments")
             + w.view(22, 50000, 9000, 25000, 14000, "P1 KPI customers") + w.view(23, 75000, 9000, 25000, 14000, "P1 KPI per shipment")
             + w.view(3, 0, 23000, 50000, 77000, k)
             + w.view(4, 50000, 23000, 38000, 41000, "P1 Monthly revenue") + w.legend(6, 88000, 23000, 12000, 41000, "P1 Monthly revenue", r(P))
             + w.view(5, 50000, 64000, 50000, 36000, "P1 Growth by product"),
             ["P1 KPI revenue", "P1 KPI shipments", "P1 KPI customers", "P1 KPI per shipment", k, "P1 Monthly revenue", "P1 Growth by product"])
w.dashboard2("P2 Customers and geography", "Who the key customers are, and where the goods go",
             "Main customers group several customer IDs. Click a customer to see where its goods go.", 52000,
             filters("P2 Top customers")
             + w.view(3, 0, 9000, 38000, 50000, "P2 Top customers") + w.legend(7, 38000, 9000, 12000, 50000, "P2 Top customers", r(S))
             + w.view(4, 0, 59000, 50000, 41000, "P2 Customer size")
             + w.view(5, 50000, 9000, 50000, 50000, "P2 Delivery map")
             + w.view(6, 50000, 59000, 38000, 41000, "P2 Delivery regions") + w.legend(8, 88000, 59000, 12000, 41000, "P2 Delivery regions", r(P)),
             ["P2 Top customers", "P2 Customer size", "P2 Delivery map", "P2 Delivery regions"])
F3 = (w.qfilter(10, 40000, 0, 15000, 9000, "P3 History", r(P)) + w.qfilter(11, 55000, 0, 15000, 9000, "P3 History", r(S))
      + w.qfilter(12, 70000, 0, 15000, 9000, "P3 History", r(RTF)) + w.qfilter(13, 85000, 0, 15000, 9000, "P3 History", r(MCF)))
w.dashboard2("P3 Routes and pricing", "Routes and prices",
             "Route = pickup to delivery region. Click a route to filter the other charts.", 40000,
             F3
             + w.view(3, 0, 9000, 38000, 46000, "P3 Top routes") + w.legend(7, 38000, 9000, 12000, 46000, "P3 Top routes", r(P))
             + w.view(4, 0, 55000, 50000, 45000, "P3 Discount")
             + w.view(5, 50000, 9000, 50000, 46000, "P3 History")
             + w.view(6, 50000, 55000, 50000, 45000, "P3 Customer movers"),
             ["P3 Top routes", "P3 Discount", "P3 History", "P3 Customer movers"])
F4 = w.qfilter(10, 68000, 0, 16000, 9000, "P4 Surcharges", r(P)) + w.qfilter(11, 84000, 0, 16000, 9000, "P4 Surcharges", r(S))
w.dashboard2("P4 Customer health and pricing", "Is the customer base healthy, and what do customers pay for?",
             "Customer status compares Jan-Aug 2019 with Jan-Aug 2018. Surcharges = price paid - freight. Filters apply to every chart.", 68000,
             F4
             + w.view(3, 0, 9000, 50000, 46000, "P4 Customer status") + w.view(4, 50000, 9000, 50000, 46000, "P4 Active customers")
             + w.view(5, 0, 55000, 50000, 45000, "P4 Surcharges") + w.view(6, 50000, 55000, 50000, 45000, "P4 Pallet mix"),
             ["P4 Customer status", "P4 Active customers", "P4 Surcharges", "P4 Pallet mix"])
w.filter_action("Click a cell: filter P1", "P1 Products and segments", k)
w.filter_action("Click a customer: filter P2", "P2 Customers and geography", "P2 Top customers")
w.filter_action("Click a route: filter P3", "P3 Routes and pricing", "P3 Top routes",
                exclude=["P3 Customer movers"])  # its top 12 follow the Route filter (context), not the click
w.filter_action("Click a product: filter P4", "P4 Customer health and pricing", "P4 Surcharges")
DS_STYLE = w.ds_colors(P, PRODUCTS) + w.ds_colors(S, SEGCOL)

OUT.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("DVA_PostNord_Dashboard.twb", w.xml(DS_STYLE, I_P + I_S))
    z.write(HYPER, "Data/DVA_PostNord_Sales.hyper")
print("wrote", OUT.name, round(OUT.stat().st_size / 1e6, 1), "MB;", len(FIELDS), "fields")
