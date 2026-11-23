"""Figures of dengue incidence: US states (CDC), the world (WHO, OpenDengue) and the EU/EEA (ECDC)."""

import re
from datetime import date
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import StrMethodFormatter

from .cdc import FIPS, NAMES, STATES

INK, MUTED, GRID, CONTEXT, EMPTY = "#0b0b0b", "#6b6a66", "#e6e5e0", "#d3d2cd", "#e6e6e6"
HERE = Path(__file__).parent
ATLAS = HERE / "states-albers-10m.json"  # us-atlas 3.0.1 (ISC), Census boundaries
WORLD = HERE / "world-50m.geojson"  # Natural Earth 1:50m map units (public domain), one shape per ISO3 code
HIGHLIGHT = {"FL": "#2a78d6", "CA": "#eb6834", "TX": "#1baf7a", "HI": "#eda100"}
US_CONTEXT = [s for s in STATES if s not in HIGHLIGHT]
MIN_POP = 1e6  # countries and territories smaller than this are mapped but left off the line plots
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]  # categorical, in fixed order
RED = ["#f8a49d", "#ed756e", "#db4242", "#b32229", "#7c1117"]  # one-hue ramp, light to dark
CDC_BINS = [  # bins and approximate colors of the CDC jurisdiction map
    (0, "No reported cases", EMPTY),
    (1, "1 to 4", "#c6e9d3"),
    (5, "5 to 49", "#5cc8bb"),
    (50, "50 to 249", "#1f7fa8"),
    (250, "250+", "#0b3a69"),
]
INC_BINS = [  # cumulative cases per 100k (under 1 shown as 0)
    (0, "0", EMPTY), (1, "1–2", RED[0]), (2, "2–5", RED[1]), (5, "5–10", RED[2]), (10, "10–20", RED[3]),
    (20, "20+", RED[4]),
]
REGIONS = {  # each region's total line is named after its key
    "World": dict(
        bins=[(0, "<1 or no data", EMPTY), (1, "1–10", RED[0]), (10, "10–100", RED[1]), (100, "100–1k", RED[2]),
              (1000, "1k–5k", RED[3]), (5000, "5k+", RED[4])],
        crs="EPSG:8857", extent=None, source="Source: WHO, gaps\nfilled from OpenDengue",  # Equal Earth
        size=(18, 7), map_ax=(0.0, 0.12, 0.51, 0.78), line_ax=(0.575, 0.1, 0.3, 0.85), tick_step=4,
        extra=["PAN", "BOL", "ARG", "LKA"],  # recent risers Panama, Argentina; mid-range Bolivia, Sri Lanka
        legend=dict(ncol=6, bbox_to_anchor=(0.01, 0.0), title="Cumulative cases per 100,000"),
    ),
    "EU/EEA": dict(
        bins=[(0, "<1 or no data", EMPTY)] + INC_BINS[1:],
        crs="EPSG:3035", extent=(2.55e6, 1.38e6, 6.0e6, 5.48e6), source="Source: ECDC",  # LAEA; mainland and Iceland
        size=(16, 7), map_ax=(0.17, 0.04, 0.31, 0.86), line_ax=(0.55, 0.1, 0.33, 0.85), tick_step=2, extra=[],
        legend=dict(ncol=1, bbox_to_anchor=(0.01, 0.04), title="Cumulative cases\nper 100,000"),
    ),
}

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED})


def _us_cumulative(df):
    """Return cumulative incidence per 100k as a year x state table."""
    return df[df.status == "All"].pivot(index="year", columns="state", values="incidence").cumsum()


def _bin_color(n, bins):
    """Return the color of the bin a value falls in."""
    return [c for lo, _, c in bins if n >= lo][-1]


def _states():
    """Load pre-projected state outlines (Alaska and Hawaii inset) keyed by postal code."""
    geo = gpd.read_file(ATLAS, layer="states")
    geo["state"] = geo.id.astype(int).map({f: s for s, f in FIPS.items()})
    return geo


def _spread(ys, gap, top=np.inf):
    """Nudge label positions upward so neighbours are at least `gap` apart, then back down below `top`."""
    out, prev = {}, -np.inf
    for k in sorted(ys, key=ys.get):
        out[k] = prev = max(ys[k], prev + gap)
    for k in sorted(out, key=out.get, reverse=True):
        out[k] = top = min(out[k], top)
        top -= gap
    return out


def _year_ticks(x, step=1, to_date=False):
    """Label whole years in the range of x, every `step` counting back from the last so it is always shown."""
    years = np.arange(np.ceil(x[0]), np.floor(x[-1]) + 1, dtype=int)[::-1][::step][::-1]
    return {y: f"{y}\n(to date)" if to_date and y == years[-1] else str(y) for y in years}


def _source(fig, cutoff, last):
    """Add the shared source and caveat footnote."""
    fig.text(0.01, 0.01, f"Source: CDC ArboNET via cdc.gov/dengue (data through {cutoff}; "
             f"{last - 1}–{last} provisional, {last} year to date); US Census Bureau population estimates.\n"
             "Travel-associated and locally acquired cases. United States = 50 states + DC; Puerto Rico and other "
             "territories excluded.", fontsize=8, color=MUTED, va="bottom")


def _draw_lines(ax, cum, context, highlight, total, names, ticks, fs=1, end_dots=True, dashed=True,
                ylabel="Cumulative cases per 100,000 residents"):
    """Draw context lines in gray, highlights in color and the total in black, with labelled ends."""
    x = cum.index.to_numpy(float)
    pad, ymax, solid = 0.02 * (x[-1] - x[0]), 1.05 * cum.iloc[-1][context + list(highlight)].max(), len(x) - dashed
    lines = [(c, CONTEXT, 0.8, 1) for c in context] + [(c, k, 2, 2) for c, k in highlight.items()]
    for c, color, lw, z in lines + [(total, INK, 3, 3)]:
        ax.plot(x[:solid], cum[c].iloc[:solid], color=color, lw=lw, zorder=z, solid_capstyle="round")
        if dashed:  # the final period is partial
            ax.plot(x[-2:], cum[c].iloc[-2:], color=color, lw=lw, zorder=z, ls=(0, (3, 2)))

    ends = {c: cum[c].iloc[-1] for c in [*highlight, total]}
    height_pt = ax.get_position().height * ax.figure.get_figheight() * 72
    for c, y in _spread(ends, gap=13 * fs / height_pt * ymax, top=ymax).items():
        if end_dots:
            ax.plot(x[-1], ends[c], "o", ms=5, color=highlight.get(c, INK), zorder=4)
        ax.annotate(names[c], (x[-1], ends[c]), xytext=(1.01, y), textcoords=("axes fraction", "data"), va="center",
                    fontsize=10 * fs, color=INK, fontweight="bold" if c == total else "normal", annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6, shrinkA=1, shrinkB=4))

    ax.set(xlim=(x[0] - pad, x[-1] + pad), ylim=(0, ymax), ylabel=ylabel)
    ax.set_xticks(list(ticks), list(ticks.values()), fontsize=9 * fs)
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,g}"))
    ax.grid(axis="y", color=GRID, lw=1)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=0, pad=4 * fs)


def _animate(fig, ax_line, shapes, cum, labels, bins, marked, path, steps=6, fps=12):
    """Fill in the map while circles advance along the lines, saving the GIF and its final frame as PNG."""
    x = cum.index.to_numpy(float)
    ts = np.linspace(x[0], x[-1], (len(x) - 1) * steps + 1)
    frames = [x[0]] * fps + list(ts) + [x[-1]] * 4 * fps  # hold the first and last frames
    filled = cum.fillna(0)  # countries are gray until they first report
    stamp = fig.text(0.01, 0.97, "", fontsize=26, fontweight="bold", color=INK, va="top")
    guide = ax_line.axvline(x[0], color=MUTED, lw=0.8, zorder=0)
    dots = {c: ax_line.plot([], [], "o", ms=9, color=k, mec="white", mew=1.5, zorder=5)[0] for c, k in marked.items()}

    def update(t):
        """Draw the frame for time t, which falls in period k."""
        k = np.searchsorted(x, t - 1e-9)
        for c, shape in shapes.items():
            shape.set_facecolor(_bin_color(np.interp(t, x, filled[c]), bins))
        for c, dot in dots.items():
            dot.set_data([t], [np.interp(t, x, cum[c])])
        guide.set_xdata([t, t])
        stamp.set_text(labels[k])

    FuncAnimation(fig, update, frames=frames).save(path, writer=PillowWriter(fps=fps))
    update(x[-1])
    fig.savefig(path.with_suffix(".png"))
    plt.close(fig)


def incidence_lines(df, cutoff, path):
    """Plot cumulative per-state incidence in gray with the US total and highlighted states on top."""
    inc = _us_cumulative(df)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=200)
    _draw_lines(ax, inc, US_CONTEXT, HIGHLIGHT, "US", NAMES, _year_ticks(inc.index, to_date=True))
    ax.set_title(f"Cumulative dengue incidence in the United States, {inc.index[0]}–{inc.index[-1]}", loc="left",
                 fontsize=15, fontweight="bold", color=INK, pad=24)
    ax.text(0, 1.02, f"Yearly cases per 100,000 residents summed since {inc.index[0]}, by state of residence. "
            "Gray: other states and DC.", transform=ax.transAxes, fontsize=10, color=MUTED)
    _source(fig, cutoff, inc.index[-1])
    fig.tight_layout(rect=(0, 0.05, 0.9, 1))
    fig.savefig(path)
    plt.close(fig)


@plt.rc_context({"font.size": 20})  # doubles default-sized text (axis label, y ticks)
def animation(df, path):
    """Animate the US cumulative incidence map filling in while circles advance along the line plot."""
    inc = _us_cumulative(df)
    fig = plt.figure(figsize=(18, 7), dpi=100)
    ax_map = fig.add_axes((0.0, 0.0, 0.44, 0.8))
    ax_line = fig.add_axes((0.5, 0.1, 0.36, 0.85))
    geo = _states()
    shapes = {s: gpd.GeoSeries([g]).plot(ax=ax_map, ec="white", lw=0.5).collections[-1]
              for s, g in zip(geo.state, geo.geometry)}
    ax_map.invert_yaxis()  # us-atlas is pre-projected in screen coordinates
    ax_map.set_axis_off()
    fig.legend(handles=[Patch(color=c, label=l) for _, l, c in INC_BINS], loc="upper right", ncol=6,
               bbox_to_anchor=(0.43, 0.88), frameon=False, fontsize=18, title="Cumulative cases per 100,000",
               title_fontsize=18, alignment="left", handlelength=1, handletextpad=0.4, columnspacing=0.8)
    _draw_lines(ax_line, inc, US_CONTEXT, HIGHLIGHT, "US", NAMES, _year_ticks(inc.index, 2), fs=2, end_dots=False,
                ylabel="Cases per 100,000 residents")
    ax_line.text(0.02, 0.98, "Source: CDC ArboNET\nvia cdc.gov/dengue", transform=ax_line.transAxes, va="top",
                 fontsize=20, color=MUTED, bbox=dict(facecolor="white", edgecolor="none", pad=2))
    _animate(fig, ax_line, shapes, inc, [str(y) for y in inc.index], INC_BINS, HIGHLIGHT | {"US": INK}, path)


@plt.rc_context({"font.size": 20})
def region_animation(region, cum, size, names, path):
    """Animate a region's cumulative incidence map filling in while circles advance along the line plot."""
    s = REGIONS[region]
    names = {c: re.sub(r" \(.*\)", "", n) for c, n in names.items()} | {region: region}  # "Bolivia (...)"
    fig = plt.figure(figsize=s["size"], dpi=100)
    ax_map = fig.add_axes(s["map_ax"], anchor="S")
    ax_line = fig.add_axes(s["line_ax"])
    geo = gpd.read_file(WORLD).to_crs(s["crs"]).set_index("iso3").geometry
    shapes = {c: gpd.GeoSeries([g]).plot(ax=ax_map, fc=EMPTY, ec="white", lw=0.4).collections[-1]
              for c, g in geo.items()}  # all gray to start with; those without data stay that way
    if s["extent"]:
        ax_map.set(xlim=s["extent"][::2], ylim=s["extent"][1::2])
    ax_map.set_axis_off()
    fig.legend(handles=[Patch(color=c, label=l) for _, l, c in s["bins"]], loc="lower left", frameon=False,
               fontsize=18, title_fontsize=18, alignment="left", handlelength=1, handletextpad=0.4, columnspacing=0.8,
               **s["legend"])

    shown = [c for c in cum.columns.drop(region) if size.get(c, 0) >= MIN_POP]
    end = cum.iloc[-1][shown]
    highlight = dict(zip([*end.nlargest(3).index, *s["extra"]], PALETTE))
    context = [c for c in shown if c not in highlight]
    _draw_lines(ax_line, cum, context, highlight, region, names, _year_ticks(cum.index, s["tick_step"]), fs=2,
                end_dots=False, dashed=cum.index[-1] == date.today().year, ylabel="Cases per 100,000 residents")
    ax_line.text(0.02, 0.98, s["source"], transform=ax_line.transAxes, va="top", fontsize=20, color=MUTED,
                 bbox=dict(facecolor="white", edgecolor="none", pad=2))
    shapes = {c: shape for c, shape in shapes.items() if c in cum}
    _animate(fig, ax_line, shapes, cum, [str(y) for y in cum.index], s["bins"], highlight | {region: INK}, path)


def cases_map(df, path, years):
    """Draw a CDC-style map of cumulative cases by jurisdiction over a range of years."""
    sel = df[(df.status == "All") & df.year.between(*years)]
    total = sel.groupby("state").cases.sum()
    geo = _states()
    geo["color"] = [_bin_color(total.get(s, 0), CDC_BINS) for s in geo.state]

    fig, ax = plt.subplots(figsize=(10, 6.6), dpi=200)
    geo.plot(ax=ax, color=geo.color, edgecolor="white", lw=0.6)
    ax.invert_yaxis()
    ax.set_axis_off()

    groups = [("U.S. territories", ["AS", "GU", "MP", "PR", "VI"]), ("Freely associated states", ["FM", "MH", "PW"])]
    x0 = 0.02
    for title, codes in groups:
        fig.text(x0, 0.2, title, fontsize=10, fontweight="bold", color=INK)
        for i, s in enumerate(codes):
            n = total.get(s, 0)
            fig.patches.append(Rectangle((x0 + i * 0.055, 0.14), 0.048, 0.045, transform=fig.transFigure,
                                         color=_bin_color(n, CDC_BINS)))
            fig.text(x0 + i * 0.055 + 0.024, 0.162, s, ha="center", va="center", fontsize=9,
                     color="white" if n >= 5 else INK, fontweight="bold")
        x0 += 0.38
    fig.legend(handles=[Patch(color=c, label=l) for _, l, c in CDC_BINS], loc="lower left", ncol=5,
               frameon=False, bbox_to_anchor=(0.01, 0.06), fontsize=9)
    fig.suptitle(f"All dengue cases by jurisdiction of residence, {years[0]}–{years[1]}", x=0.02, ha="left",
                 fontsize=15, fontweight="bold", color=INK)
    n_all = int(total.drop("US").sum())
    fig.text(0.02, 0.02, f"Source: CDC ArboNET via cdc.gov/dengue. Total: {n_all:,} cases.", fontsize=8, color=MUTED)
    fig.subplots_adjust(left=0, right=1, top=0.93, bottom=0.22)
    fig.savefig(path)
    plt.close(fig)
