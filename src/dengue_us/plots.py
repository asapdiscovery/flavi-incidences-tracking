"""Figures of US dengue incidence."""

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Patch, Rectangle

from .data import FIPS, NAMES, STATES

INK, MUTED, GRID, CONTEXT, EMPTY = "#0b0b0b", "#6b6a66", "#e6e5e0", "#d3d2cd", "#e6e6e6"
HIGHLIGHT = {"FL": "#2a78d6", "CA": "#eb6834", "TX": "#1baf7a", "HI": "#eda100"}
ATLAS = Path(__file__).with_name("states-albers-10m.json")  # us-atlas 3.0.1 (ISC), Census boundaries
CDC_BINS = [  # bins and approximate colors of the CDC jurisdiction map
    (0, "No reported cases", EMPTY),
    (1, "1 to 4", "#c6e9d3"),
    (5, "5 to 49", "#5cc8bb"),
    (50, "50 to 249", "#1f7fa8"),
    (250, "250+", "#0b3a69"),
]
INC_BINS = [  # cumulative cases per 100k (under 1 shown as 0), one-hue red ramp
    (0, "0", EMPTY),
    (1, "1–2", "#f8a49d"),
    (2, "2–5", "#ed756e"),
    (5, "5–10", "#db4242"),
    (10, "10–20", "#b32229"),
    (20, "20+", "#7c1117"),
]

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED})


def _cumulative(df):
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


def _source(fig, cutoff, last):
    """Add the shared source and caveat footnote."""
    fig.text(0.01, 0.01, f"Source: CDC ArboNET via cdc.gov/dengue (data through {cutoff}; "
             f"{last - 1}–{last} provisional, {last} year to date); US Census Bureau population estimates.\n"
             "Travel-associated and locally acquired cases. United States = 50 states + DC; Puerto Rico and other "
             "territories excluded.", fontsize=8, color=MUTED, va="bottom")


def _draw_lines(ax, inc, end_dots=True, tick_step=1, fs=1, ylabel="Cumulative cases per 100,000 residents",
                to_date=True):
    """Draw cumulative incidence lines with the final, year-to-date segment dashed and labelled ends."""
    x, last = inc.index, inc.index[-1]
    ymax = 1.05 * inc.loc[last, STATES].max()
    lines = [(s, CONTEXT, 0.8, 1) for s in STATES if s not in HIGHLIGHT]
    lines += [(s, c, 2, 2) for s, c in HIGHLIGHT.items()] + [("US", INK, 3, 3)]
    for s, color, lw, z in lines:
        ax.plot(x[:-1], inc[s].iloc[:-1], color=color, lw=lw, zorder=z, solid_capstyle="round")
        ax.plot(x[-2:], inc[s].iloc[-2:], color=color, lw=lw, zorder=z, ls=(0, (3, 2)))

    ends = {s: inc.at[last, s] for s in [*HIGHLIGHT, "US"]}
    height_pt = ax.get_position().height * ax.figure.get_figheight() * 72
    for s, y in _spread(ends, gap=13 * fs / height_pt * ymax).items():
        if end_dots:
            ax.plot(last, ends[s], "o", ms=5, color=INK if s == "US" else HIGHLIGHT[s], zorder=4)
        ax.annotate(NAMES[s], (last, ends[s]), xytext=(last + 0.45, y), va="center", fontsize=10 * fs, color=INK,
                    fontweight="bold" if s == "US" else "normal", annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6, shrinkA=1, shrinkB=4))

    ax.set(xlim=(x[0] - 0.3, last + 0.3), ylim=(0, ymax), ylabel=ylabel)
    ticks = x[::-1][::tick_step][::-1]  # count back from the final year so it is always labelled
    ax.set_xticks(ticks, [f"{t}\n(to date)" if to_date and t == last else str(t) for t in ticks], fontsize=9 * fs)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=0, pad=4 * fs)


def incidence_lines(df, cutoff, path):
    """Plot cumulative per-state incidence in gray with the US total and highlighted states on top."""
    inc = _cumulative(df)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=200)
    _draw_lines(ax, inc)
    ax.set_title(f"Cumulative dengue incidence in the United States, {inc.index[0]}–{inc.index[-1]}", loc="left",
                 fontsize=15, fontweight="bold", color=INK, pad=24)
    ax.text(0, 1.02, f"Yearly cases per 100,000 residents summed since {inc.index[0]}, by state of residence. "
            "Gray: other states and DC.", transform=ax.transAxes, fontsize=10, color=MUTED)
    _source(fig, cutoff, inc.index[-1])
    fig.tight_layout(rect=(0, 0.05, 0.9, 1))
    fig.savefig(path)
    plt.close(fig)


@plt.rc_context({"font.size": 20})  # doubles default-sized text (axis label, y ticks)
def animation(df, path, steps=6, fps=12):
    """Animate the cumulative incidence map filling in while circles advance along the line plot."""
    inc = _cumulative(df)
    years, last = inc.index.to_numpy(), inc.index[-1]
    ts = np.linspace(years[0], last, (len(years) - 1) * steps + 1)
    frames = [ts[0]] * fps + list(ts) + [last] * 4 * fps  # hold the first and last frames

    fig = plt.figure(figsize=(18, 7), dpi=100)
    ax_map = fig.add_axes((0.0, 0.0, 0.44, 0.8))
    ax_line = fig.add_axes((0.5, 0.1, 0.36, 0.85))
    geo = _states()
    shapes = {s: gpd.GeoSeries([g]).plot(ax=ax_map, edgecolor="white", lw=0.5).collections[-1]
              for s, g in zip(geo.state, geo.geometry)}
    ax_map.invert_yaxis()  # us-atlas is pre-projected in screen coordinates
    ax_map.set_axis_off()
    year = fig.text(0.01, 0.97, "", fontsize=26, fontweight="bold", color=INK, va="top")
    fig.legend(handles=[Patch(color=c, label=l) for _, l, c in INC_BINS], loc="upper right", ncol=6,
               bbox_to_anchor=(0.43, 0.88), frameon=False, fontsize=18, title="Cumulative cases per 100,000",
               title_fontsize=18, alignment="left", handlelength=1, handletextpad=0.4, columnspacing=0.8)

    _draw_lines(ax_line, inc, end_dots=False, tick_step=2, fs=2, ylabel="Cases per 100,000 residents", to_date=False)
    ax_line.text(0.02, 0.98, "Source: CDC ArboNET\nvia cdc.gov/dengue", transform=ax_line.transAxes, va="top",
                 fontsize=20, color=MUTED, bbox=dict(facecolor="white", edgecolor="none", pad=2))
    guide = ax_line.axvline(years[0], color=MUTED, lw=0.8, zorder=0)
    dots = {s: ax_line.plot([], [], "o", ms=9, color=c, mec="white", mew=1.5, zorder=5)[0]
            for s, c in [*HIGHLIGHT.items(), ("US", INK)]}

    def update(t):
        """Draw the frame for fractional year t."""
        for s, shape in shapes.items():
            shape.set_facecolor(_bin_color(np.interp(t, years, inc[s]), INC_BINS))
        for s, dot in dots.items():
            dot.set_data([t], [np.interp(t, years, inc[s])])
        guide.set_xdata([t, t])
        year.set_text(str(round(t)))

    FuncAnimation(fig, update, frames=frames).save(path, writer=PillowWriter(fps=fps))
    plt.close(fig)


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
