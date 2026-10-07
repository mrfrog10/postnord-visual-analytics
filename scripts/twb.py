"""Small helpers that write Tableau workbook XML (one data source per workbook, hyper extract packaged)."""
import uuid
from xml.sax.saxutils import escape, quoteattr as qa

U = lambda: "{" + str(uuid.uuid4()).upper() + "}"
E = lambda s: escape(s, {'"': "&quot;"})
RT = {"date": (133, "Year"), "datetime": (135, "Year"), "real": (5, "Sum"), "string": (129, "Count"), "integer": (20, "Sum")}

# Tableau Color Blind palette
CB = {"blue": "#1170aa", "orange": "#fc7d0b", "lightblue": "#5fa2ce", "darkorange": "#c85200", "grey": "#7b848f",
      "lightgrey": "#c8d0d9", "lightorange": "#ffbc79", "paleblue": "#a3cce9", "darkgrey": "#57606c"}


class Workbook:
    def __init__(self, ds, hyper_name, fields, calcs, geo=()):
        self.ds, self.hyper, self.fields, self.calcs, self.geo = ds, hyper_name, fields, calcs, set(geo)
        self.sheets, self.windows, self.dashboards, self.dash_windows, self.styles = [], [], [], [], []

    # ------------------------------------------------------------------ data source
    def role(self, n, t):
        if n in self.geo:
            sem = "[Geographical].[Latitude]" if "Lat" in n else "[Geographical].[Longitude]"
            return f'datatype="real" name="[{n}]" role="measure" semantic-role="{sem}" type="quantitative"'
        if t in ("date", "datetime"):
            return f'datatype="{t}" name="[{n}]" role="dimension" type="ordinal"'
        if t == "string":
            return f'datatype="string" name="[{n}]" role="dimension" type="nominal"'
        if t == "integer" and n.endswith(("Nr", "Week", "Hour", "Code", "Postcode")):
            return f'datatype="integer" name="[{n}]" role="dimension" type="ordinal"'
        return f'datatype="{t}" name="[{n}]" role="measure" type="quantitative"'

    def records(self, extract=False):
        out = []
        for i, (n, t) in enumerate(self.fields):
            out.append(f'<metadata-record class="column"><remote-name>{E(n)}</remote-name><remote-type>{RT[t][0]}</remote-type>'
                       f'<local-name>[{E(n)}]</local-name><parent-name>[Extract]</parent-name><remote-alias>{E(n)}</remote-alias>'
                       f'<ordinal>{i}</ordinal><local-type>{t}</local-type><aggregation>{RT[t][1]}</aggregation>'
                       f'<contains-null>true</contains-null>'
                       + ("<collation flag='0' name='binary' />" if extract and t == "string" else "")
                       + f'<object-id>[{self.ds}_object]</object-id></metadata-record>')
        return "<metadata-records>" + "".join(out) + "</metadata-records>"

    @staticmethod
    def calc_xml(c):
        n, t, ro, ty, formula, fmt = (list(c) + [None])[:6]
        f = f' default-format={qa(fmt)}' if fmt else ""
        return f'<column caption={qa(n)} datatype="{t}" name="[{E(n)}]" role="{ro}" type="{ty}"{f}><calculation class="tableau" formula={qa(formula)} /></column>'

    def datasource(self, extra_style="", ds_instances=""):
        conn = (f'class="hyper" access-mode="readonly" author-locale="en_US" dbname="Data/{self.hyper}" default-settings="hyper" '
                f'schema="Extract" tablename="Extract" username="tableau_internal_user"')
        cols = "".join(f'<column {self.role(n, t)} />' for n, t in self.fields)
        return (f'<datasource caption="{self.ds}" inline="true" name="{self.ds}" version="18.1"><connection class="federated"><named-connections>'
                f'<named-connection caption="{self.ds}" name="hyper.{self.ds}"><connection {conn} /></named-connection></named-connections>'
                f'<relation connection="hyper.{self.ds}" name="Extract" table="[Extract].[Extract]" type="table" />{self.records()}</connection>'
                f'{cols}{"".join(self.calc_xml(c) for c in self.calcs)}{ds_instances}'
                f'<extract count="-1" enabled="true" object-id="" units="records"><connection {conn}>'
                f'<relation name="Extract" table="[Extract].[Extract]" type="table" />{self.records(True)}</connection></extract>'
                f'<layout dim-ordering="alphabetic" measure-ordering="alphabetic" show-structure="true" /><style>{extra_style}</style><object-graph><objects><object caption="{self.ds}" id="{self.ds}_object"><properties context="">'
                f'<relation connection="hyper.{self.ds}" name="Extract" table="[Extract].[Extract]" type="table" /></properties>'
                f'<properties context="extract"><relation name="Extract" table="[Extract].[Extract]" type="table" /></properties></object></objects></object-graph></datasource>')

    # ------------------------------------------------------------------ instances and references
    def ref(self, name):
        return f"[{self.ds}].[{name}]"

    @staticmethod
    def inst(col, der, name, ty):
        return f'<column-instance column="[{E(col)}]" derivation="{der}" name="[{E(name)}]" pivot="key" type="{ty}" />'

    def deps(self, instances):
        cols = "".join(f'<column {self.role(n, t)} />' for n, t in self.fields) + "".join(self.calc_xml(c) for c in self.calcs)
        return (f'<datasources><datasource caption="{self.ds}" name="{self.ds}" /></datasources>'
                f'<datasource-dependencies datasource="{self.ds}">{cols}{"".join(instances)}</datasource-dependencies>')

    # ------------------------------------------------------------------ worksheet
    def sheet(self, name, title, subtitle, instances, rows, cols, mark="Automatic", encodings="", filters="", sorts="",
              style="", pane_style="", panes=None, mapsource=False, show_labels=False, extra_view=""):
        t = (f'<layout-options><title><formatted-text><run bold="true" fontsize="12">{E(title)}\n</run>'
             f'<run fontcolor="#555555" fontsize="9">{E(subtitle)}</run></formatted-text></title></layout-options>')
        lab = '<format attr="mark-labels-show" value="true" /><format attr="mark-labels-cull" value="true" />' if show_labels else ""
        ms = '<mapsources><mapsource name="Tableau" /></mapsources>' if mapsource else ""
        pane = panes or (f'<pane selection-relaxation-option="selection-relaxation-allow"><view><breakdown value="auto" /></view>'
                         f'<mark class="{mark}" /><encodings>{encodings}</encodings><style><style-rule element="mark">{lab}{pane_style}</style-rule></style></pane>')
        xml = (f'<worksheet name={qa(name)}>{t}<table><view>{self.deps(instances)}{filters}{sorts}{extra_view}<aggregation value="true" /></view>'
               f'<style>{style}</style><panes>{pane}</panes><rows>{rows}</rows><cols>{cols}</cols></table><simple-id uuid="{U()}" /></worksheet>')
        if mapsource:
            xml = xml.replace(f'<datasource-dependencies datasource="{self.ds}">', f'{ms}<datasource-dependencies datasource="{self.ds}">', 1)
        self.sheets.append(xml)
        self.windows.append(f'<window class="worksheet" name={qa(name)}><cards><edge name="left"><strip size="160"><card type="pages" />'
                            f'<card type="filters" /><card type="marks" /></strip></edge><edge name="top"><strip size="2147483647"><card type="columns" />'
                            f'</strip><strip size="2147483647"><card type="rows" /></strip><strip size="2147483647"><card type="title" /></strip></edge>'
                            f'</cards><viewpoint><zoom type="entire-view" /></viewpoint><simple-id uuid="{U()}" /></window>')

    # ------------------------------------------------------------------ styles
    def axis_title(self, field, label, scope="rows"):
        return f'<format attr="title" class="0" field="{E(field)}" scope="{scope}" value={qa(label)} />'

    def color_map(self, field, pairs):
        return (f'<style-rule element="mark"><encoding attr="color" field="{E(field)}" palette="color_blind_10_0" type="palette">'
                + "".join(f'<map to="{c}"><bucket>&quot;{E(v)}&quot;</bucket></map>' for v, c in pairs) + '</encoding></style-rule>')

    @staticmethod
    def manual_sort(field, values):
        return (f'<sort class="manual" column="{E(field)}" direction="ASC"><dictionary>'
                + "".join(f'<bucket>&quot;{E(v)}&quot;</bucket>' for v in values) + '</dictionary></sort>')

    @staticmethod
    def computed_sort(field, using, direction="DESC"):
        return f'<sort class="computed" column="{E(field)}" direction="{direction}" using="{E(using)}" />'

    def top_n(self, field_inst, level, n, expression):
        return (f'<filter class="categorical" column="{E(field_inst)}"><groupfilter count="{n}" end="top" function="end" units="records" '
                f'user:ui-marker="end" user:ui-top-by-field="true"><groupfilter direction="DESC" expression={qa(expression)} function="order" '
                f'user:ui-marker="order"><groupfilter function="level-members" level="[{E(level)}]" user:ui-enumeration="all" '
                f'user:ui-marker="enumerate" /></groupfilter></groupfilter></filter>')

    def all_filter(self, field_inst, level, group=None):
        g = f' filter-group="{group}"' if group else ""
        return (f'<filter class="categorical" column="{E(field_inst)}"{g}><groupfilter function="level-members" level="[{E(level)}]" '
                f'user:ui-enumeration="all" user:ui-marker="enumerate" /></filter>')

    def member_filter(self, field_inst, level, members):
        inner = "".join(f'<groupfilter function="member" level="[{E(level)}]" member="&quot;{E(m)}&quot;" />' for m in members)
        return f'<filter class="categorical" column="{E(field_inst)}"><groupfilter function="union">{inner}</groupfilter></filter>'

    # ------------------------------------------------------------------ dashboard
    def dashboard(self, name, title, subtitle, zones, sheets):
        head = (f'<zone h="9000" id="2" type-v2="text" w="98000" x="1000" y="0"><formatted-text><run bold="true" fontsize="17">{E(title)}\n</run>'
                f'<run fontcolor="#555555" fontsize="10">{E(subtitle)}</run></formatted-text></zone>')
        self.dashboards.append(f'<dashboard name={qa(name)}><style /><size maxheight="900" maxwidth="1600" minheight="900" minwidth="1600" '
                               f'sizing-mode="fixed" /><zones><zone h="100000" id="1" type-v2="layout-basic" w="100000" x="0" y="0">'
                               f'{head}{zones}</zone></zones><simple-id uuid="{U()}" /></dashboard>')
        self.dash_windows.append(f'<window class="dashboard" name={qa(name)}><viewpoints>'
                                 + "".join(f'<viewpoint name={qa(s)}><zoom type="entire-view" /></viewpoint>' for s in sheets)
                                 + f'</viewpoints><active id="-1" /><simple-id uuid="{U()}" /></window>')

    @staticmethod
    def view(i, x, y, w, h, sheet):
        return (f'<zone h="{h}" id="{i}" name={qa(sheet)} w="{w}" x="{x}" y="{y}"><zone-style><format attr="border-style" value="none" />'
                f'<format attr="margin" value="6" /></zone-style></zone>')

    def legend(self, i, x, y, w, h, sheet, field):
        return f'<zone h="{h}" id="{i}" name={qa(sheet)} param="{E(field)}" pane-specification-id="0" type-v2="color" w="{w}" x="{x}" y="{y}" />'

    def qfilter(self, i, x, y, w, h, sheet, field, mode="checkdropdown"):
        return f'<zone h="{h}" id="{i}" mode="{mode}" name={qa(sheet)} param="{E(field)}" type-v2="filter" values="relevant" w="{w}" x="{x}" y="{y}" />'

    @staticmethod
    def text(i, x, y, w, h, html_runs):
        return f'<zone h="{h}" id="{i}" type-v2="text" w="{w}" x="{x}" y="{y}"><formatted-text>{html_runs}</formatted-text></zone>'

    # ------------------------------------------------------------------ v2 helpers
    @staticmethod
    def header_width(field, px):
        return f'<style-rule element="header"><format attr="width" field="{E(field)}" value="{px}" /></style-rule>'

    @staticmethod
    def label_horizontal(field):
        return f'<style-rule element="label"><format attr="text-orientation" field="{E(field)}" value="0" /></style-rule>'

    def ds_colors(self, field_name, pairs):
        """Colour assignment stored on the data source, so every sheet uses it (field_name like none:Product Name:nk)."""
        return (f'<style-rule element="mark"><encoding attr="color" field="[{E(field_name)}]" palette="color_blind_10_0" type="palette">'
                + "".join(f'<map to="{c}"><bucket>&quot;{E(v)}&quot;</bucket></map>' for v, c in pairs) + '</encoding></style-rule>')

    def dashboard2(self, name, title, subtitle, header_w, zones, sheets):
        """Tiled layout with no overlaps: header on the left of the top band, filters to its right."""
        head = (f'<zone h="9000" id="2" type-v2="text" w="{header_w}" x="0" y="0"><formatted-text><run bold="true" fontsize="16">{E(title)}\n</run>'
                f'<run fontcolor="#555555" fontsize="9">{E(subtitle)}</run></formatted-text></zone>')
        self.dashboards.append(f'<dashboard name={qa(name)}><style /><size maxheight="900" maxwidth="1600" minheight="900" minwidth="1600" '
                               f'sizing-mode="fixed" /><zones><zone h="100000" id="1" type-v2="layout-basic" w="100000" x="0" y="0">'
                               f'{head}{zones}</zone></zones><simple-id uuid="{U()}" /></dashboard>')
        self.dash_windows.append(f'<window class="dashboard" name={qa(name)}><viewpoints>'
                                 + "".join(f'<viewpoint name={qa(s)}><zoom type="entire-view" /></viewpoint>' for s in sheets)
                                 + f'</viewpoints><active id="-1" /><simple-id uuid="{U()}" /></window>')

    def filter_action(self, caption, dashboard, source_sheet, exclude=()):
        """Click a mark in source_sheet to filter the other charts of the same dashboard (Shneiderman's relate task).
        exclude: sheets on the dashboard that the action should not filter (syntax as in Tableau's Superstore sample)."""
        if not hasattr(self, "actions"):
            self.actions = []
        n = len(self.actions) + 1
        ex = f'<param name="exclude" value={qa(",".join(exclude))} />' if exclude else ""
        self.actions.append(f'<action caption={qa(caption)} name="[Action{n}_{uuid.uuid4().hex[:8].upper()}]"><activation auto-clear="true" type="on-select" />'
                            f'<source dashboard={qa(dashboard)} type="sheet" worksheet={qa(source_sheet)} />'
                            f'<command command="tsc:tsl-filter">{ex}<param name="special-fields" value="all" /><param name="target" value={qa(dashboard)} /></command></action>')

    # ------------------------------------------------------------------ write
    def xml(self, extra_ds_style="", ds_instances=""):
        return (f"<?xml version='1.0' encoding='utf-8'?>\n<workbook original-version=\"18.1\" source-build=\"2026.3.0 (20263.26.1022.1645)\" "
                f"source-platform=\"win\" version=\"18.1\" xmlns:user=\"http://www.tableausoftware.com/xml/user\"><document-format-change-manifest>"
                f"<AnimationOnByDefault /><MarkAnimation /><ObjectModelEncapsulateLegacy /><ObjectModelExtractV2 /><ObjectModelTableType />"
                f"<SchemaViewerObjectModel /><SheetIdentifierTracking /><WindowsPersistSimpleIdentifiers /></document-format-change-manifest>"
                f"<preferences><preference name='ui.encoding.shelf.height' value='24' /><preference name='ui.shelf.height' value='26' /></preferences>"
                f"<datasources>{self.datasource(extra_ds_style, ds_instances)}</datasources>"
                f"<mapsources><mapsource name='Tableau' /></mapsources>"
                + (f"<actions>{''.join(self.actions)}</actions>" if getattr(self, "actions", None) else "") +
                f"<worksheets>{''.join(self.sheets)}</worksheets><dashboards>{''.join(self.dashboards)}</dashboards>"
                f"<windows source-height='30'>{''.join(self.dash_windows)}{''.join(self.windows)}</windows><thumbnails /></workbook>")
