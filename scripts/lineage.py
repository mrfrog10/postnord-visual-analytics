"""Figure: data lineage from raw files through the Prep flows to the two packaged workbooks."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "Screenshots" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
BLUE, ORANGE, GREY, LIGHT = "#1170aa", "#fc7d0b", "#57606c", "#eaf1f6"
fig, ax = plt.subplots(figsize=(12, 6.2))
ax.set_xlim(0, 12); ax.set_ylim(0, 6.2); ax.axis("off")


def box(x, y, w, h, title, sub, edge, fill="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fill, ec=edge, lw=1.6))
    ax.text(x + w / 2, y + h - 0.2, title, ha="center", va="top", fontsize=8.4, weight="bold", color="#222222")
    ax.text(x + w / 2, y + h - 0.48, sub, ha="center", va="top", fontsize=7.8, color="#444444", linespacing=1.3)


def arrow(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.2))


for x, t in [(0.2, "1. Raw data"), (3.2, "2. Tableau Prep flows"), (6.6, "3. Extracts (.hyper)"), (9.5, "4. Dashboards (.twbx)")]:
    ax.text(x, 6.0, t, fontsize=10.5, weight="bold", color=BLUE)
box(0.2, 3.7, 2.6, 1.9, "DDS sales files", "100 .xls files, 4 product folders\nJan 2017 - Aug 2019\n3,234,869 rows", GREY)
box(0.2, 1.85, 2.6, 1.6, "Master data", "Customer master (DDS sheet)\n4,229 customer IDs\nDanish postcodes (GeoNames)", GREY)
box(0.2, 0.2, 2.6, 1.4, "Dataset-2.xls", "8,968 video views\n+ video length sheet", GREY)
box(3.2, 3.7, 3.0, 1.9, "PRP0002_UNION_DDS_SALES", "wildcard union of 100 files,\nkeep status 10, convert types,\nremove 1,504 repeated rows", BLUE, LIGHT)
box(3.2, 1.85, 3.0, 1.6, "PRP0001_UPLOAD_MASTERDATA", "fix Danish letters,\none row per postcode", BLUE, LIGHT)
box(3.2, 0.2, 3.0, 1.4, "PRP0004_UPLOAD_VIDEO_VIEWS", "join video length, 40 min rule,\nweek, weekday, hour, completion", BLUE, LIGHT)
box(6.6, 4.25, 2.5, 1.35, "DVA_DDS_Shipments", "3,233,365 shipments", GREY)
box(6.6, 2.35, 2.5, 1.55, "PRP0003_JOIN_SALES_\nCUSTOMER_GEO", "\n\nmonthly grain + customer\n+ pickup / delivery place", BLUE, LIGHT)
box(6.6, 0.2, 2.5, 1.4, "DVA_Video_Views", "8,968 views, 17 fields", GREY)
box(9.5, 2.35, 2.3, 1.55, "DVA_PostNord_\nDashboard", "\n\nP1, P2, P3\n(930,757-row extract)", ORANGE, "#fff4ea")
box(9.5, 0.2, 2.3, 1.4, "DVA_Video_\nDashboard", "\n\nV1, V2", ORANGE, "#fff4ea")
arrow(2.8, 4.65, 3.2, 4.65); arrow(2.8, 2.65, 3.2, 2.65); arrow(2.8, 0.9, 3.2, 0.9)
arrow(6.2, 4.65, 6.6, 4.9); arrow(7.85, 4.25, 7.85, 3.9); arrow(6.2, 2.65, 6.6, 2.9)
arrow(6.2, 0.9, 6.6, 0.9); arrow(9.1, 3.1, 9.5, 3.1); arrow(9.1, 0.9, 9.5, 0.9)
ax.text(7.85, 2.25, "+ DVA_Master_Customers, DVA_Master_PostCodes_DK", fontsize=6.8, color=GREY, ha="center", va="top")
fig.savefig(OUT / "lineage.png", dpi=170, bbox_inches="tight")
print("saved", OUT / "lineage.png")
