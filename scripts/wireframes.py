"""First-idea wireframes (iteration 0) for the report: hand-drawn style, before any Tableau build."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Wedge, Circle

OUT = Path(__file__).resolve().parents[1] / "Screenshots" / "v0_wireframes"
OUT.mkdir(parents=True, exist_ok=True)


def box(ax, x, y, w, h, label, note=None):
    ax.add_patch(Rectangle((x, y), w, h, fill=False, lw=1.6))
    ax.text(x + 0.015, y + h - 0.045, label, fontsize=10, weight="bold", va="top")
    if note:
        ax.text(x + 0.015, y + 0.03, note, fontsize=7.5, color="#555555", va="bottom", wrap=True)


def bars(ax, x, y, w, h, n=6, horizontal=True):
    for i in range(n):
        L = (0.9 - i * 0.12) * w * 0.8
        if horizontal:
            ax.add_patch(Rectangle((x + 0.02, y + h - 0.12 - i * (h - 0.16) / n), L, (h - 0.2) / n * 0.6, fill=False, lw=1))
        else:
            ax.add_patch(Rectangle((x + 0.03 + i * w / (n + 1), y + 0.07), w / (n + 2) * 0.7, L * h / w * 0.7, fill=False, lw=1))


def line(ax, x, y, w, h):
    import numpy as np
    xs = np.linspace(x + 0.03, x + w - 0.03, 30)
    for k, s in enumerate((0.25, 0.45, 0.65)):
        ax.plot(xs, y + h * s + 0.03 * np.sin(xs * 40 + k) + (xs - x) * 0.08, lw=1, color="black")


def pie(ax, cx, cy, r):
    a = 0
    for frac in (0.54, 0.33, 0.1, 0.03):
        ax.add_patch(Wedge((cx, cy), r, a, a + frac * 360, fill=False, lw=1.2)); a += frac * 360


def sheet(title, draw, name):
    with plt.xkcd(scale=0.6, length=120, randomness=2):
        fig, ax = plt.subplots(figsize=(11, 6.2))
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=2))
        ax.text(0.02, 0.965, title, fontsize=13, weight="bold", va="top")
        draw(ax)
        fig.savefig(OUT / f"{name}.png", dpi=150, bbox_inches="tight"); plt.close(fig)


def part1(ax):
    for i, t in enumerate(["Revenue", "Shipments", "Customers"]):
        box(ax, 0.02 + i * 0.16, 0.78, 0.15, 0.12, t); ax.text(0.095 + i * 0.16, 0.8, "123", fontsize=14, ha="center")
    box(ax, 0.02, 0.36, 0.47, 0.39, "Revenue share by product", "pie chart?")
    pie(ax, 0.25, 0.53, 0.13)
    box(ax, 0.51, 0.36, 0.47, 0.54, "Monthly revenue", "one line per product")
    line(ax, 0.51, 0.36, 0.47, 0.5)
    box(ax, 0.02, 0.03, 0.47, 0.3, "Top customers (table)", "name | segment | revenue")
    for i in range(5):
        ax.plot([0.04, 0.47], [0.24 - i * 0.04] * 2, lw=0.8, color="black")
    box(ax, 0.51, 0.03, 0.47, 0.3, "Map of Denmark", "revenue by postcode")
    ax.add_patch(Circle((0.7, 0.18), 0.05, fill=False)); ax.add_patch(Circle((0.82, 0.13), 0.03, fill=False))


def part2(ax):
    box(ax, 0.02, 0.52, 0.47, 0.38, "Views per lecture", "bar per session")
    bars(ax, 0.02, 0.52, 0.47, 0.38, 6, horizontal=False)
    box(ax, 0.51, 0.52, 0.47, 0.38, "Views per programme", "total views")
    bars(ax, 0.51, 0.52, 0.47, 0.38, 6)
    box(ax, 0.02, 0.05, 0.47, 0.42, "Views per day", "line over the semester")
    line(ax, 0.02, 0.05, 0.47, 0.38)
    box(ax, 0.51, 0.05, 0.47, 0.42, "Time of day", "bar per hour")
    bars(ax, 0.51, 0.05, 0.47, 0.42, 8, horizontal=False)


sheet("Iteration 0 - Part 1 sales dashboard (one page)", part1, "wireframe_part1")
sheet("Iteration 0 - Part 2 video dashboard (one page)", part2, "wireframe_part2")
print("saved to", OUT)
