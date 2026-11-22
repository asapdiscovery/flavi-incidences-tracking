"""Figures of dengue incidence: US states from CDC, and the world and Europe from WHO."""

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import StrMethodFormatter

from .cdc import FIPS, NAMES, STATES

INK, MUTED, GRID, CONTEXT, EMPTY, NODATA = "#0b0b0b", "#6b6a66", "#e6e5e0", "#d3d2cd", "#e6e6e6", "white"
HERE = Path(__file__).parent
ATLAS = HERE / "states-albers-10m.json"  # us-atlas 3.0.1 (ISC), Census boundaries
WORLD = HERE / "world-50m.geojson"  # Natural Earth 1:50m map units (public domain), one shape per ISO3 code
HIGHLIGHT = {"FL": "#2a78d6", "CA": "#eb6834", "TX": "#1baf7a", "HI": "#eda100"}
US_CONTEXT = [s for s in STATES if s not in HIGHLIGHT]
MIN_POP = 1e6  # WHO countries and territories smaller than this are mapped but left off the line plots
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
REGIONS = {  # WHO animations; each region's total line is named after it
    "World": dict(
        highlight={"BRA": "#2a78d6", "PER": "#eb6834", "ARG": "#1baf7a", "THA": "#eda100", "NIC": "#e87ba4",
                   "PRY": "#008300"},
        bins=[(0, "0", EMPTY), (1, "1–10", RED[0]), (10, "10–100", RED[1]), (100, "100–1k", RED[2]),
              (1000, "1k–5k", RED[3]), (5000, "5k+", RED[4])],
        crs="EPSG:8857", extent=None, tick_step=2, steps=6, dashed=True,  # Equal Earth; yearly, current year partial
    ),
    "Europe": dict(
        highlight={"ITA": "#2a78d6", "FRA": "#eb6834", "ESP": "#1baf7a"},
        bins=[(0, "0", EMPTY), (1e-9, "<0.05", RED[0]), (0.05, "0.05–0.1", RED[1]), (0.1, "0.1–0.25", RED[2]),
              (0.25, "0.25–0.5", RED[3]), (0.5, "0.5+", RED[4])],  # 1e-9: any case at all
        crs="EPSG:3035", extent=(2.2e6, 1.3e6, 9.26e6, 5.5e6), tick_step=1, steps=2, dashed=False,  # LAEA; monthly
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


def _spread(ys, gap):
    """Nudge label positions upward so neighbours are at least `gap` apart."""
    out, prev = {}, float("-inf")
    for k in sorted(ys, key=ys.get):
        out[k] = prev = max(ys[k], prev + gap)
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
    for c, y in _spread(ends, gap=13 * fs / height_pt * ymax).items():
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
    reported, filled = cum.notna(), cum.fillna(0)
    stamp = fig.text(0.01, 0.97, "", fontsize=26, fontweight="bold", color=INK, va="top")
    guide = ax_line.axvline(x[0], color=MUTED, lw=0.8, zorder=0)
    dots = {c: ax_line.plot([], [], "o", ms=9, color=k, mec="white", mew=1.5, zorder=5)[0] for c, k in marked.items()}

    def update(t):
        """Draw the frame for time t, which falls in period k."""
        k = np.searchsorted(x, t - 1e-9)
        for c, shape in shapes.items():
            on = c in reported and reported[c].iat[k]
            shape.set_facecolor(_bin_color(np.interp(t, x, filled[c]), bins) if on else NODATA)
            shape.set_edgecolor("white" if on else CONTEXT)
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
    shapes = {s: gpd.GeoSeries([g]).plot(ax=ax_map, lw=0.5).collections[-1] for s, g in zip(geo.state, geo.geometry)}
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
def who_animation(region, cum, labels, size, names, path):
    """Animate a WHO region's cumulative incidence map filling in while circles advance along the line plot."""
    s = REGIONS[region]
    fig = plt.figure(figsize=(18, 7), dpi=100)
    ax_map = fig.add_axes((0.0, 0.12, 0.51, 0.78), anchor="S")  # a cropped extent should match this aspect
    ax_line = fig.add_axes((0.575, 0.1, 0.3, 0.85))
    world = gpd.read_file(WORLD).to_crs(s["crs"])
    shapes = {c: gpd.GeoSeries([g]).plot(ax=ax_map, lw=0.4).collections[-1] for c, g in zip(world.iso3, world.geometry)}
    if s["extent"]:
        ax_map.set(xlim=s["extent"][::2], ylim=s["extent"][1::2])
    ax_map.set_axis_off()
    handles = [Patch(color=c, label=l) for _, l, c in s["bins"]] + [Patch(fc=NODATA, ec=CONTEXT, label="No data")]
    fig.legend(handles=handles, loc="lower left", ncol=7, bbox_to_anchor=(0.01, 0.0), frameon=False, fontsize=18,
               title="Cumulative cases per 100,000", title_fontsize=18, alignment="left", handlelength=1,
               handletextpad=0.4, columnspacing=0.8)
    context = [c for c in cum.columns if size.get(c, 0) >= MIN_POP and c not in s["highlight"]]
    _draw_lines(ax_line, cum, context, s["highlight"], region, names, _year_ticks(cum.index, s["tick_step"]), fs=2,
                end_dots=False, dashed=s["dashed"], ylabel="Cases per 100,000 residents")
    ax_line.text(0.02, 0.98, "Source: WHO global\ndengue surveillance", transform=ax_line.transAxes, va="top",
                 fontsize=20, color=MUTED, bbox=dict(facecolor="white", edgecolor="none", pad=2))
    _animate(fig, ax_line, shapes, cum, labels, s["bins"], s["highlight"] | {region: INK}, path, steps=s["steps"])


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
