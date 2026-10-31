"""Part 2 workbook: DVA_Video_Dashboard.twbx (two dashboards for the course manager and teachers). Version 2 after evaluation."""
import zipfile
from pathlib import Path
from twb import Workbook, CB

EXAM = Path(__file__).resolve().parents[2]
HYPER = EXAM / "Data" / "Prep_Output" / "DVA_Video_Views.hyper"
OUT = EXAM / "1_UPLOAD_TO_WISEFLOW" / "DVA_Video_Dashboard.twbx"

FIELDS = [("Completion", "real"), ("Course Week", "integer"), ("Hour", "integer"), ("Lecture/Exercise", "string"),
          ("Length Used (min)", "real"), ("Location", "string"), ("Minutes Viewed", "real"), ("Session", "string"),
          ("Session Type", "string"), ("Study Program", "string"), ("Timestamp", "datetime"), ("UserName", "string"),
          ("Video Length (Minutes)", "real"), ("View Date", "date"), ("View Length Band", "string"), ("Weekday", "string"),
          ("Weekday Nr", "integer")]
VIDEOS = [("Introduction to Data Visualization - Part 1", "L02 Intro to data visualisation 1"),
          ("Introduction to Data Visualization - Part 2", "L02 Intro to data visualisation 2"),
          ("Introduction to Data Visualization - Part 3", "L02 Intro to data visualisation 3"),
          ("Visual Perception - Part 1", "L03 Visual perception 1"), ("Visual Perception - Part 2", "L03 Visual perception 2"),
          ("Visual Perception - Part 3", "L03 Visual perception 3"),
          ("The Details of Information Design - Part 1", "L04 Information design 1"), ("The Details of Information Design - Part 2", "L04 Information design 2"),
          ("The Details of Information Design - Part 3", "L04 Information design 3"),
          ("Preattentive attributes - Part 1", "L05 Preattentive attributes 1"), ("Preattentive attributes - Part 2", "L05 Preattentive attributes 2"),
          ("Preattentive attributes - Part 3", "L05 Preattentive attributes 3"),
          ("Visual Analytics and Dashboards - Part 1", "L06 Visual analytics & dashboards 1"),
          ("Visual Analytics and Dashboards - Part 2", "L06 Visual analytics & dashboards 2"),
          ("Colors (Part 1)", "L07 Colours 1"), ("Colors (Part 2)", "L07 Colours 2")]
VIDEO_CASE = "CASE [Session] " + " ".join(f"WHEN '{a}' THEN '{b}'" for a, b in VIDEOS) + " ELSE [Session] END"
CALCS = [("Students", "integer", "measure", "quantitative", "COUNTD([UserName])", "n#,##0"),
         ("Views", "integer", "measure", "quantitative", "COUNT([UserName])", "n#,##0"),
         ("Minutes per Student", "real", "measure", "quantitative", "SUM([Minutes Viewed]) / COUNTD([UserName])", "n#,##0"),
         ("Average Completion", "real", "measure", "quantitative", "AVG([Completion])", "p0%"),
         ("Watch Hours", "real", "measure", "quantitative", "SUM([Minutes Viewed]) / 60", "n#,##0"),
         ("Short View Share", "real", "measure", "quantitative", "SUM(IF [Minutes Viewed] < 1 THEN 1 ELSE 0 END) / COUNT([UserName])", "p0%"),
         ("Video", "string", "dimension", "nominal", VIDEO_CASE),
         # Lester's feedback: a week without views is a zero, not a gap. LOOKUP makes Tableau fill in missing weeks; ZN turns them into 0.
         ("Views incl zero weeks", "integer", "measure", "quantitative", "ZN(LOOKUP(COUNT([UserName]), 0))", "n#,##0")]
w = Workbook("Video Views", "DVA_Video_Views.hyper", FIELDS, CALCS)
r, inst = w.ref, w.inst
TYPES = [("Pre-recorded lecture", CB["blue"]), ("Live lecture recording", CB["orange"]), ("Exercise recording", CB["grey"])]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

prog, loc, stype, vid = "none:Study Program:nk", "none:Location:nk", "none:Session Type:nk", "none:Video:nk"
I_PROG, I_LOC, I_TYPE = inst("Study Program", "None", prog, "nominal"), inst("Location", "None", loc, "nominal"), inst("Session Type", "None", stype, "nominal")
GLOBAL = w.all_filter(r(prog), prog, 1) + w.all_filter(r(loc), loc, 2)
U_ = lambda n: inst(n, "User", f"usr:{n}:qk", "quantitative")
typecolor = w.color_map(r(stype), TYPES)
DS_STYLE = w.ds_colors(stype, TYPES)
ax = lambda f, label, scope="cols": f'<style-rule element="axis">{w.axis_title(f, label, scope)}</style-rule>'

# ---------------------------------------------------------------- V1: content performance
w.sheet("V1 Pre-recorded drop-off",
        "Viewers fall from 397 students to 21 across the pre-recorded lectures",
        "Students who opened each pre-recorded video (bars) and their average completion (labels), in lecture order. 3 Feb - 13 Apr 2022.",
        [I_PROG, I_LOC, I_TYPE, inst("Video", "None", vid, "nominal"), U_("Students"), U_("Average Completion")],
        rows=r(vid), cols=r("usr:Students:qk"), mark="Bar",
        encodings=f'<text column="{r("usr:Average Completion:qk")}" />',
        filters=GLOBAL + w.member_filter(r(stype), stype, ["Pre-recorded lecture"]),
        sorts=w.manual_sort(r(vid), [b for _, b in VIDEOS]),
        style=ax(r("usr:Students:qk"), "Students who opened the video") + w.header_width(r(vid), 230),
        pane_style=f'<format attr="mark-color" value="{CB["blue"]}" />', show_labels=True)

w.sheet("V1 Session types",
        "Pre-recorded lectures are watched far more completely",
        "Average completion = minutes viewed / video length (40 min assumed for live and exercise recordings), capped at 100%.",
        [I_PROG, I_LOC, I_TYPE, U_("Average Completion")],
        rows=r(stype), cols=r("usr:Average Completion:qk"), mark="Bar", encodings=f'<color column="{r(stype)}" />',
        filters=GLOBAL, sorts=w.manual_sort(r(stype), [t for t, _ in TYPES]),
        style=ax(r("usr:Average Completion:qk"), "Average completion") + typecolor + w.header_width(r(stype), 170), show_labels=True)

band = "none:View Length Band:nk"
w.sheet("V1 View length",
        "A third of all views last under one minute",
        "Number of views by length of the viewing session, coloured by session type.",
        [I_PROG, I_LOC, I_TYPE, inst("View Length Band", "None", band, "nominal"), U_("Views")],
        rows=r(band), cols=r("usr:Views:qk"), mark="Bar", encodings=f'<color column="{r(stype)}" />', filters=GLOBAL,
        style=ax(r("usr:Views:qk"), "Views") + typecolor + w.header_width(r(band), 120))

# ---------------------------------------------------------------- V2: programmes and timing
w.sheet("V2 Weekday and hour",
        "Viewing peaks on Thursday mornings, the lecture day",
        "Number of views by weekday and the hour viewing started. Darker = more views; white = no views.",
        [I_PROG, I_LOC, I_TYPE, inst("Weekday", "None", "none:Weekday:nk", "nominal"), inst("Hour", "None", "none:Hour:ok", "ordinal"), U_("Views")],
        rows=r("none:Weekday:nk"), cols=r("none:Hour:ok"), mark="Square", encodings=f'<color column="{r("usr:Views:qk")}" />',
        filters=GLOBAL, sorts=w.manual_sort(r("none:Weekday:nk"), DAYS),
        style=(f'<style-rule element="mark"><encoding attr="color" field="{r("usr:Views:qk")}" palette="blue_10_0" type="interpolated" /></style-rule>'
               + w.label_horizontal(r("none:Hour:ok")) + w.header_width(r("none:Weekday:nk"), 95)))

week = "none:Course Week:ok"
w.sheet("V2 Weekly views",
        "Views dip in week 4 and fade after week 3",
        "Views per course week by session type; weeks without views show as 0. Week 1 starts Monday 31 Jan 2022; week 11 ends 13 Apr.",
        [I_PROG, I_LOC, I_TYPE, inst("Course Week", "None", week, "ordinal"),
         '<column-instance column="[Views incl zero weeks]" derivation="User" name="[usr:Views incl zero weeks:qk]" pivot="key" type="quantitative">'
         '<table-calc ordering-type="Columns" /></column-instance>'],
        rows=r("usr:Views incl zero weeks:qk"), cols=r(week), mark="Line", encodings=f'<color column="{r(stype)}" />',
        filters=GLOBAL, style=ax(r("usr:Views incl zero weeks:qk"), "Views", "rows") + typecolor)

w.sheet("V2 Programmes",
        "Engagement per student differs a lot between programmes",
        "Minutes watched per student (bars); labels show the number of students. Per student, so large and small programmes compare fairly.",
        [I_PROG, I_LOC, I_TYPE, U_("Minutes per Student"), U_("Students")],
        rows=r(prog), cols=r("usr:Minutes per Student:qk"), mark="Bar", encodings=f'<text column="{r("usr:Students:qk")}" />',
        filters=GLOBAL, sorts=w.computed_sort(r(prog), r("usr:Minutes per Student:qk")),
        style=ax(r("usr:Minutes per Student:qk"), "Minutes watched per student") + w.header_width(r(prog), 270),
        pane_style=f'<format attr="mark-color" value="{CB["blue"]}" />', show_labels=True)

# ---------------------------------------------------------------- dashboards (tiled, no overlaps)
def filt(sheet):
    return (w.qfilter(10, 66000, 0, 17000, 9000, sheet, r(prog)) + w.qfilter(11, 83000, 0, 17000, 9000, sheet, r(loc)))

w.dashboard2("V1 Content performance", "Which recordings work, and where students drop off",
             "For the course manager and teachers. MB221, spring 2022. Filters apply to every chart; click a video to filter the others.", 66000,
             filt("V1 Session types")
             + w.view(3, 0, 9000, 55000, 91000, "V1 Pre-recorded drop-off")
             + w.view(4, 55000, 9000, 45000, 42000, "V1 Session types")
             + w.view(5, 55000, 51000, 32000, 49000, "V1 View length") + w.legend(6, 87000, 51000, 13000, 49000, "V1 View length", r(stype)),
             ["V1 Pre-recorded drop-off", "V1 Session types", "V1 View length"])
w.dashboard2("V2 Programmes and timing", "When students watch, and how programmes compare",
             "Views by weekday, hour and course week; minutes per student by programme. Click a programme to filter the timing charts.", 66000,
             filt("V2 Programmes")
             + w.view(3, 0, 9000, 55000, 46000, "V2 Weekday and hour")
             + w.view(4, 0, 55000, 42000, 45000, "V2 Weekly views") + w.legend(7, 42000, 55000, 13000, 45000, "V2 Weekly views", r(stype))
             + w.view(5, 55000, 9000, 45000, 91000, "V2 Programmes"),
             ["V2 Weekday and hour", "V2 Weekly views", "V2 Programmes"])
w.filter_action("Click a video: filter V1", "V1 Content performance", "V1 Pre-recorded drop-off")
w.filter_action("Click a programme: filter V2", "V2 Programmes and timing", "V2 Programmes")

OUT.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("DVA_Video_Dashboard.twb", w.xml(DS_STYLE, I_TYPE))
    z.write(HYPER, "Data/DVA_Video_Views.hyper")
print("wrote", OUT.name, round(OUT.stat().st_size / 1e3), "KB")
