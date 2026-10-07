"""
Writes the four Tableau Prep flows for the MB221 exam (naming follows the class: tool, number, verb, object).

PRP0001_UPLOAD_MASTERDATA        customer master + Danish postcodes  -> DVA_Master_Customers, DVA_Master_PostCodes_DK
PRP0002_UNION_DDS_SALES          100 monthly DDS files (wildcard)    -> DVA_DDS_Shipments
PRP0003_JOIN_SALES_CUSTOMER_GEO  shipments + masters, monthly grain  -> DVA_PostNord_Sales
PRP0004_UPLOAD_VIDEO_VIEWS       lecture video views + video length  -> DVA_Video_Views
"""
import json
import uuid
import zipfile
from pathlib import Path

EXAM = Path(__file__).resolve().parents[2]
DATA = EXAM / "Data"
DDS = DATA / "DDS"
MD = DATA / "Master_Data"
OUT = DATA / "Prep_Output"
DST = EXAM / "1_UPLOAD_TO_WISEFLOW"
META = Path(__file__).with_name("maestro_metadata_format.json")
HEX = {"hexCss": "#0F5C7A", "rgba": ["15", "92", "122", "1"]}
new_id = lambda: str(uuid.uuid4())


class Flow:
    def __init__(self):
        self.nodes, self.conns, self.disp = {}, {}, {}

    # -- basics ------------------------------------------------------------------------------------
    @staticmethod
    def base(kind, btype, name, desc=None):
        return {"nodeType": kind, "name": name, "id": new_id(), "baseType": btype, "nextNodes": [],
                "serialize": False, "description": desc}

    def place(self, node, x, y):
        self.nodes[node["id"]] = node
        self.disp[node["id"]] = {"position": {"x": x, "y": y}, "size": {"width": 1, "height": 1}, "color": HEX}
        return node

    @staticmethod
    def link(a, b, ns="Default"):
        a["nextNodes"].append({"namespace": "Default", "nextNodeId": b["id"], "nextNamespace": ns})

    def chain(self, *items):
        for a, b in zip(items, items[1:]):
            self.link(a, b)

    @staticmethod
    def field(name, ftype):
        return {"name": name, "type": ftype, "collation": None, "caption": None, "ordinal": None, "isGenerated": False}

    def _input_common(self, n, cid, fields):
        n.update(connectionId=cid, connectionAttributes={}, fields=[self.field(*f) for f in fields], actions=[],
                 debugModeRowLimit=1048576, originalDataTypes={}, randomSampling=None, updateTimestamp=1793451980000,
                 restrictedFields={}, userRenamedFields={}, selectedFields=None, samplingType=None, groupByFields=None, filters=[])

    # -- inputs ------------------------------------------------------------------------------------
    def excel(self, name, path, sheet, fields, x, y, desc=None):
        cid = new_id()
        self.conns[cid] = {"connectionType": ".v1.SqlConnection", "id": cid, "name": path.name, "isPackaged": False,
                           "connectionAttributes": {"filename": str(path), "class": "excel-direct", "directory": str(path.parent)}}
        n = self.base(".v1.LoadExcel", "input", name, desc)
        self._input_common(n, cid, fields)
        n["relation"] = {"type": "table", "table": sheet}
        return self.place(n, x, y)

    def hyper(self, name, path, fields, x, y, desc=None):
        cid = new_id()
        self.conns[cid] = {"connectionType": ".v1.SqlConnection", "id": cid, "name": path.name, "isPackaged": False,
                           "connectionAttributes": {"dbname": str(path), "class": "hyper"}}
        n = self.base(".v1.LoadSql", "input", name, desc)
        self._input_common(n, cid, fields)
        n["connectionAttributes"] = {"author-locale": "en_US", "user-language": "en_US", "prep-protocol-role": ":prep-protocol-reader"}
        n["relation"] = {"type": "table", "table": "[Extract].[Extract]"}
        return self.place(n, x, y)

    def excel_wildcard(self, name, folder, pattern, sheet, fields, x, y, desc=None):
        files = sorted(folder.rglob(pattern))
        cid = new_id()
        self.conns[cid] = {"connectionType": ".v1.SqlConnection", "id": cid, "name": files[0].name, "isPackaged": False,
                           "connectionAttributes": {"filename": str(files[0]), "class": "excel-direct", "directory": str(folder)}}
        gen = []
        for f in files:
            node = self.base(".v1.LoadExcel", "input", f.stem)
            node.update(connectionId=new_id(), connectionAttributes={"filename": str(f), "class": "excel-direct"},
                        fields=[self.field(*x_) for x_ in fields], actions=[], debugModeRowLimit=None, originalDataTypes={},
                        randomSampling=None, updateTimestamp=None, restrictedFields=None, userRenamedFields={}, selectedFields=None,
                        samplingType=None, groupByFields=None, filters=None, relation={"type": "table", "table": f"[{sheet}$]"})
            gen.append({"inputUnionInputType": ".ExcelInputUnionInput", "filePath": str(f.relative_to(folder)), "tableName": sheet, "inputNode": node})
        n = self.base(".v1.LoadExcelInputUnion", "input", name, desc)
        self._input_common(n, cid, list(fields) + [("File Paths", "string"), ("Table Names", "string")])
        n.update(relation={"type": "table", "table": f"[{sheet}$]"}, filePattern=pattern, inclusiveFilePattern=True,
                 includeSubDirectory=True, pathNameField="File Paths", errorOnLoadFiles={}, containsHeaders=True,
                 sheetPattern=sheet, inclusiveSheetPattern=True, tableNameField="Table Names", matchedSheetsAndFiles=None,
                 excludedSheetsAndFiles=None, generatedInputs=gen)
        return self.place(n, x, y)

    # -- steps -------------------------------------------------------------------------------------
    @staticmethod
    def step(kind, name, **kw):
        return {**Flow.base(kind, "transform", name), **kw}

    @staticmethod
    def calc(col, expr):
        return Flow.step(".v1.AddColumn", "Calculate " + col, columnName=col, expression=expr)

    @staticmethod
    def drop(*cols):
        return Flow.step(".v1.RemoveColumns", "Remove fields", columnNames=list(cols))

    @staticmethod
    def keep(expr, name="Keep rows"):
        return Flow.step(".v1.FilterOperation", name, filterExpression=expr)

    def clean(self, name, steps, x, y, desc=None):
        for a, b in zip(steps, steps[1:]):
            self.link(a, b)
        n = self.base(".v1.Container", "container", name, desc)
        n.update(loomContainer={"parameters": {"parameters": {}}, "initialNodes": [steps[0]["id"]], "nodes": {s["id"]: s for s in steps},
                                "connections": {}, "connectionIds": [], "nodeProperties": {}, "extensibility": {}},
                 namespacesToInput={"Default": {"nodeId": steps[0]["id"], "namespace": "Default"}},
                 namespacesToOutput={"Default": {"nodeId": steps[-1]["id"], "namespace": "Default"}}, providedParameters=None)
        return self.place(n, x, y)

    def superstep(self, kind, action_kind, name, x, y, desc=None, **action):
        n = self.base(kind, "superNode", name, desc)
        n.update(beforeActionAnnotations=[], afterActionAnnotations=[], actionNode={**self.base(action_kind, "transform", name), **action})
        return self.place(n, x, y)

    def join(self, name, pairs, jtype, x, y, desc=None):
        return self.superstep(".v2018_2_3.SuperJoin", ".v1.SimpleJoin", name, x, y, desc, joinType=jtype,
                              conditions=[{"leftExpression": f"[{l}]", "rightExpression": f"[{r}]", "comparator": "=="} for l, r in pairs])

    def aggregate(self, name, groups, totals, x, y, desc=None):
        return self.superstep(".v2018_2_3.SuperAggregate", ".v1.Aggregate", name, x, y, desc,
                              groupByFields=[{"columnName": c, "function": "GroupBy", "newColumnName": None, "specialFieldType": None} for c in groups],
                              aggregateFields=[{"columnName": c, "function": fn, "newColumnName": new, "specialFieldType": None} for c, fn, new in totals])

    def output(self, name, stem, x, y, desc=None):
        n = self.base(".v1.WriteToHyper", "output", name, desc)
        n.update(hyperOutputFile=str(OUT / f"{stem}.hyper"), tdsOutput=str(OUT / f"{stem}.tds"))
        return self.place(n, x, y)

    # -- write -------------------------------------------------------------------------------------
    def save(self, stem):
        incoming = {x["nextNodeId"] for n in self.nodes.values() for x in n["nextNodes"]}
        flow = {"parameters": {"parameters": {}}, "initialNodes": [i for i in self.nodes if i not in incoming], "nodes": self.nodes,
                "connections": self.conns, "dataConnections": {}, "connectionIds": list(self.conns), "dataConnectionIds": [],
                "nodeProperties": {}, "extensibility": {}, "selection": [], "majorVersion": 1, "minorVersion": 3,
                "documentId": new_id(), "obfuscatorId": None, "performanceSettings": {}}
        display = {"majorVersion": 1, "minorVersion": 0, "fieldOrder": {"fieldOrdinals": {}, "minOrdinal": 0, "maxOrdinal": 0},
                   "flowDisplaySettings": {"flowGroupNodeDisplay": {}, "flowSelection": {"type": "nothing", "selectedNodePath": None, "selectedType": None},
                                           "flowNodeDisplaySettings": self.disp}, "hiddenColumns": []}
        # PRP0001 and PRP0004 are submitted as packaged flows (.tflx, exported from Prep Builder with their small inputs);
        # their plain .tfl goes to 2_DO_NOT_UPLOAD. Re-export the .tflx in Prep after a rebuild.
        dst = EXAM / "2_DO_NOT_UPLOAD" / "Flows_unpackaged" if stem.startswith(("PRP0001", "PRP0004")) else DST
        dst.mkdir(parents=True, exist_ok=True)
        path = dst / f"{stem}.tfl"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("flow", json.dumps(flow))
            z.writestr("displaySettings", json.dumps(display))
            z.writestr("maestroMetadata", META.read_text(encoding="utf-8"))
        print("wrote", path.name, len(self.nodes), "steps")


OUT.mkdir(parents=True, exist_ok=True)
FIX = lambda f: (f"REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE({f},'Ã¸','ø'),'Ã¦','æ'),'Ã¥','å'),'Ã˜','Ø'),'Ã†','Æ'),'Ã…','Å')")

# ================================================================ PRP0001 master data
f = Flow()
cust = f.excel("Customer master (DDS)", MD / "ADS_DDS_RF_CustomerNumbers_MasterData.xlsx", "[DDS$]",
               [("Customer ID", "string"), ("Main Customer", "string"), ("Industry Level 1", "string"), ("Industry Level 2", "string"),
                ("System", "string"), ("Allocated SAP Number", "string")], 0, 0,
               "Customer master for the DDS system: one row per Customer ID, grouped into Main Customers and industry segments.")
c_cust = f.clean("Tidy customer master", [
    f.calc("Industry Segment", "IFNULL(TRIM([Industry Level 1]), 'Missing SNI')"),
    f.calc("Industry Sub-segment", "IFNULL(TRIM([Industry Level 2]), 'Missing SNI')"),
    f.drop("System", "Industry Level 1", "Industry Level 2")], 1, 0,
    "System is always DDS. Industry names are trimmed and blanks are labelled Missing SNI, as in the ADS sheet.")
f.chain(cust, c_cust, f.output("Output customers", "DVA_Master_Customers", 2, 0))

geo = f.excel("Danish postcodes (GeoNames)", MD / "New_PostCodes_Data_DK" / "DK_Geonames.xlsx", "[Blad2$]",
              [("Column1", "string"), ("Postal Code", "integer"), ("Column3", "string"), ("Column4", "string"), ("Column5", "integer"),
               ("Column6", "string"), ("Column7", "integer"), ("Column8", "string"), ("Column9", "string"), ("Lat", "real"),
               ("Long", "real"), ("Column12", "real")], 0, 1,
              "GeoNames postcode list for Denmark: city, region, municipality and coordinates.")
c_geo = f.clean("Fix Danish letters and names", [
    f.calc("City", FIX("[Column3]")),
    f.calc("Region", "TRIM(REPLACE(" + FIX("[Column4]") + ", 'Region ', ''))"),
    f.calc("Municipality", FIX("[Column6]")),
    f.calc("Latitude", "FLOAT([Lat])"), f.calc("Longitude", "FLOAT([Long])"),
    f.drop("Column1", "Column3", "Column4", "Column5", "Column6", "Column7", "Column8", "Column9", "Column12", "Lat", "Long")], 1, 1,
    "The file was saved with the wrong text encoding, so ø, æ and å appear as Ã¸, Ã¦ and Ã¥. We repair them, make the coordinates numbers and drop unused columns.")
a_geo = f.aggregate("One row per postcode", ["Postal Code"],
                    [("City", "MIN", "City"), ("Region", "MIN", "Region"), ("Municipality", "MIN", "Municipality"),
                     ("Latitude", "AVG", "Lat"), ("Longitude", "AVG", "Long")], 2, 1,
                    "Some postcodes belong to two municipalities (for example 2000 Frederiksberg). One row per postcode stops the sales join from duplicating rows.")
f.chain(geo, c_geo, a_geo, f.output("Output postcodes", "DVA_Master_PostCodes_DK", 3, 1))
f.save("PRP0001_UPLOAD_MASTERDATA")

# ================================================================ PRP0002 union of the 100 DDS files
DDS_FIELDS = [("Customer_ID", "string"), ("ConsignorCountryCode", "string"), ("Consignor Location Nr", "string"),
              ("ConsigneeCountryCode", "string"), ("Consignee Location Nr", "string"), ("Freight calc_ status", "integer"),
              ("Product", "string"), ("Parcel/Pallet type", "string"), ("Shipment Tracking Number", "string"),
              ("ShipmentDate", "date"), ("ConsignorParcelCount", "string"), ("ConsignorWeight", "string"), ("Freight", "real"),
              ("Surcharge", "real"), ("Dangerous goods surcharge", "real"), ("Delivery outside of core area surcharge", "real"),
              ("Energy surcharge", "real"), ("Infrastructure surcharge", "real"), ("Multi-parcel surcharge", "real"),
              ("Private delivery surcharge", "real"), ("Road toll", "real"), ("Special goods surcharge", "real"),
              ("Price_Paid", "real"), ("Base_Price", "real"), ("FileName", "string")]
f = Flow()
dds = f.excel_wildcard("DDS monthly files (100)", DDS, "DatadumpProduct*.xls", "sheet1", DDS_FIELDS, 0, 0,
                       "Wildcard union: every file named DatadumpProduct*.xls in the four product folders, Jan 2017 to Aug 2019.")
c_std = f.clean("Standardise products and customers", [
    f.keep("[Freight calc_ status] = 10", "Keep delivered and invoiced (status 10)"),
    f.calc("Product Name", "CASE [Product] WHEN 'I' THEN 'Innight' WHEN 'G' THEN 'Groupage' WHEN 'L' THEN 'Pallet' WHEN 'R' THEN 'Road Freight' END"),
    f.calc("Pallet Type", "IF [Product] = 'L' THEN IFNULL([Parcel/Pallet type], 'PLL') ELSE 'Not a pallet' END"),
    f.calc("Customer ID", "IFNULL([Customer_ID], 'UNKNOWN')"),
    f.calc("Surcharges", "[Price_Paid] - [Freight]"),
    f.calc("Pickup Postcode", "INT([Consignor Location Nr])"),
    f.calc("Delivery Postcode", "INT([Consignee Location Nr])"),
    f.calc("Parcel Count", "INT([ConsignorParcelCount])"),
    f.calc("Weight", "FLOAT([ConsignorWeight])"),
    f.drop("Customer_ID", "Parcel/Pallet type", "Freight calc_ status", "FileName", "File Paths", "Table Names", "Surcharge",
           "Consignor Location Nr", "Consignee Location Nr", "ConsignorParcelCount", "ConsignorWeight",
           "Dangerous goods surcharge", "Delivery outside of core area surcharge", "Energy surcharge", "Infrastructure surcharge",
           "Multi-parcel surcharge", "Private delivery surcharge", "Road toll", "Special goods surcharge")], 1, 0,
    "Revenue counts only invoiced shipments. Product codes become names; a blank pallet type means a full pallet (PLL) per the variable list; "
    "a missing customer becomes UNKNOWN so its revenue is not lost. Surcharges = Price_Paid - Freight. The wildcard union reads postcodes, "
    "parcel counts and weights as text, so they are converted to numbers.")
dedup = f.aggregate("Remove exact repeats", ["Customer ID", "ConsignorCountryCode", "Pickup Postcode", "ConsigneeCountryCode",
                                             "Delivery Postcode", "Product", "Product Name", "Pallet Type", "Shipment Tracking Number",
                                             "ShipmentDate", "Parcel Count", "Weight", "Freight", "Surcharges",
                                             "Price_Paid", "Base_Price"], [], 2, 0,
                    "Groups by every field, so rows that are identical in every column are kept once and nothing is added up.")
f.chain(dds, c_std, dedup, f.output("Output shipments", "DVA_DDS_Shipments", 3, 0))
f.save("PRP0002_UNION_DDS_SALES")

# ================================================================ PRP0003 join + monthly grain
SHIP = [("Customer ID", "string"), ("ConsignorCountryCode", "string"), ("Pickup Postcode", "integer"), ("ConsigneeCountryCode", "string"),
        ("Delivery Postcode", "integer"), ("Product", "string"), ("Product Name", "string"), ("Pallet Type", "string"),
        ("Shipment Tracking Number", "string"), ("ShipmentDate", "date"), ("Parcel Count", "integer"), ("Weight", "real"),
        ("Freight", "real"), ("Surcharges", "real"), ("Price_Paid", "real"), ("Base_Price", "real")]
CUST = [("Customer ID", "string"), ("Main Customer", "string"), ("Allocated SAP Number", "string"), ("Industry Segment", "string"), ("Industry Sub-segment", "string")]
GEO = [("Postal Code", "integer"), ("City", "string"), ("Region", "string"), ("Municipality", "string"), ("Lat", "real"), ("Long", "real")]
f = Flow()
ship = f.hyper("Shipments", OUT / "DVA_DDS_Shipments.hyper", SHIP, 0, 0, "Output of PRP0002: one row per invoiced shipment.")
c_m = f.clean("Add month and destination key", [
    f.calc("Month", "DATE(DATETRUNC('month', [ShipmentDate]))"),
    f.calc("Destination DK Postcode", "IF [ConsigneeCountryCode] = 'DK' THEN [Delivery Postcode] END")], 1, 0,
    "Month is the reporting grain. Postcodes are only unique within a country, so only Danish destinations are matched to Danish postcodes.")
agg = f.aggregate("Monthly grain", ["Month", "Product Name", "Pallet Type", "Customer ID", "Pickup Postcode", "ConsigneeCountryCode",
                                    "Delivery Postcode", "Destination DK Postcode"],
                  [("Shipment Tracking Number", "COUNT", "Shipments"), ("Parcel Count", "SUM", "Parcels"),
                   ("Weight", "SUM", "Weight kg"), ("Price_Paid", "SUM", "Revenue DKK"), ("Freight", "SUM", "Freight DKK"),
                   ("Surcharges", "SUM", "Surcharges DKK"), ("Base_Price", "SUM", "List Price DKK")], 2, 0,
                  "3.2 million shipments are summed to one row per month, product, customer and route, which keeps the dashboard fast (Fisher et al., 2012).")
f.chain(ship, c_m, agg)
cust = f.hyper("Customers", OUT / "DVA_Master_Customers.hyper", CUST, 2, 1, "Output of PRP0001.")
j_c = f.join("Add customer and segment", [("Customer ID", "Customer ID")], "left", 3, 0,
             "Left join: shipments whose customer is not in the master are kept.")
f.link(agg, j_c, "Left"); f.link(cust, j_c, "Right")
c_c = f.clean("Label unmatched customers", [
    f.calc("Main Customer Name", "IF [Customer ID] = 'UNKNOWN' THEN 'Unknown customer' ELSE IFNULL([Main Customer], 'Not in master') END"),
    f.calc("Segment", "IF [Customer ID] = 'UNKNOWN' THEN 'Unknown customer' ELSE IFNULL([Industry Segment], 'Not in master') END"),
    f.calc("Sub-segment", "IF [Customer ID] = 'UNKNOWN' THEN 'Unknown customer' ELSE IFNULL([Industry Sub-segment], 'Not in master') END"),
    f.drop("Customer ID-1", "Main Customer", "Industry Segment", "Industry Sub-segment")], 4, 0)
f.link(j_c, c_c)
geo_o = f.hyper("Postcodes (origin)", OUT / "DVA_Master_PostCodes_DK.hyper", GEO, 4, 1, "Output of PRP0001.")
j_o = f.join("Add pickup place", [("Pickup Postcode", "Postal Code")], "left", 5, 0, "All shipments are picked up in Denmark.")
f.link(c_c, j_o, "Left"); f.link(geo_o, j_o, "Right")
c_o = f.clean("Name pickup fields", [
    f.calc("Origin City", "IFNULL([City], 'Unknown postcode')"), f.calc("Origin Region", "IFNULL([Region], 'Unknown postcode')"),
    f.calc("Origin Lat", "[Lat]"), f.calc("Origin Long", "[Long]"),
    f.drop("Postal Code", "City", "Region", "Municipality", "Lat", "Long")], 6, 0)
f.link(j_o, c_o)
geo_d = f.hyper("Postcodes (destination)", OUT / "DVA_Master_PostCodes_DK.hyper", GEO, 6, 1, "Output of PRP0001.")
j_d = f.join("Add delivery place", [("Destination DK Postcode", "Postal Code")], "left", 7, 0, "Only Danish destinations can match.")
f.link(c_o, j_d, "Left"); f.link(geo_d, j_d, "Right")
c_d = f.clean("Name delivery fields and route", [
    f.calc("Destination City", "IF [ConsigneeCountryCode] = 'SE' THEN 'Sweden' ELSEIF [ConsigneeCountryCode] = 'NO' THEN 'Norway' ELSE IFNULL([City], 'Unknown postcode') END"),
    f.calc("Destination Region", "IF [ConsigneeCountryCode] = 'SE' THEN 'Sweden' ELSEIF [ConsigneeCountryCode] = 'NO' THEN 'Norway' ELSE IFNULL([Region], 'Unknown postcode') END"),
    f.calc("Destination Lat", "[Lat]"), f.calc("Destination Long", "[Long]"),
    f.calc("Route (region)", "[Origin Region] + ' to ' + [Destination Region]"),
    f.calc("Discount DKK", "[List Price DKK] - [Revenue DKK]"),
    f.drop("Postal Code", "City", "Region", "Municipality", "Lat", "Long", "Destination DK Postcode")], 8, 0,
    "Sweden and Norway are kept as one destination each, because the postcode master covers Denmark only. Discount = list price - price paid.")
f.chain(j_d, c_d, f.output("Output sales", "DVA_PostNord_Sales", 9, 0))
f.save("PRP0003_JOIN_SALES_CUSTOMER_GEO")

# ================================================================ PRP0004 video views
V = DATA / "Dataset-2.xls"
f = Flow()
views = f.excel("Video views", V, "['Dataset-2$']",
                [("Timestamp", "datetime"), ("Lecture/Exercise", "string"), ("Session Name", "string"), ("Minutes Viewed", "real"),
                 ("UserName", "string"), ("Study Program", "string"), ("Location", "string")], 0, 0,
                "One row each time a student starts a video, 3 Feb to 13 Apr 2022.")
length = f.excel("Video length (pre-recorded)", V, "['Video Length - Prerecorded$']",
                 [("Session Name", "string"), ("Video Length (Minutes)", "real")], 0, 1, "Published length of the 16 pre-recorded videos.")
c_v = f.clean("Trim names", [f.calc("Session", "TRIM([Session Name])"), f.drop("Session Name")], 1, 0)
c_l = f.clean("Trim names", [f.calc("Session Key", "TRIM([Session Name])"), f.drop("Session Name")], 1, 1)
j = f.join("Add video length", [("Session", "Session Key")], "left", 2, 0, "Left join: live and exercise recordings have no length in the file.")
f.link(c_v, j, "Left"); f.link(c_l, j, "Right")
f.chain(views, c_v); f.chain(length, c_l)
c_x = f.clean("Session type, length and time fields", [
    f.calc("Session Type", "IF NOT ISNULL([Video Length (Minutes)]) THEN 'Pre-recorded lecture' ELSEIF [Lecture/Exercise] = 'Visual Analytics - exercises' THEN 'Exercise recording' ELSE 'Live lecture recording' END"),
    f.calc("Length Used (min)", "IFNULL([Video Length (Minutes)], 40)"),
    f.calc("Completion", "IF [Minutes Viewed] / [Length Used (min)] > 1 THEN 1 ELSE [Minutes Viewed] / [Length Used (min)] END"),
    f.calc("View Date", "DATE([Timestamp])"),
    f.calc("Course Week", "INT(DATEDIFF('day', #2022-01-31#, DATE([Timestamp])) / 7) + 1"),
    f.calc("Weekday", "DATENAME('weekday', [Timestamp])"),
    f.calc("Weekday Nr", "DATEPART('iso-weekday', [Timestamp])"),
    f.calc("Hour", "DATEPART('hour', [Timestamp])"),
    f.calc("View Length Band", "IF [Minutes Viewed] < 1 THEN '1. Under 1 min' ELSEIF [Minutes Viewed] < 10 THEN '2. 1-10 min' ELSEIF [Minutes Viewed] < 30 THEN '3. 10-30 min' ELSE '4. 30 min or more' END"),
    f.drop("Session Key")], 3, 0,
    "The brief: other sessions count as 40 minutes. Completion is capped at 100% because one view can include rewinding. "
    "Course week 1 starts Monday 31 Jan 2022, the week of the first lecture.")
f.chain(j, c_x, f.output("Output video views", "DVA_Video_Views", 4, 0))
f.save("PRP0004_UPLOAD_VIDEO_VIEWS")

