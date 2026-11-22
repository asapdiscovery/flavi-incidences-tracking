"""Rebuild the dengue data snapshots and figures (US from CDC; world and Europe from WHO), stamped with today's date."""

import argparse
from datetime import date
from pathlib import Path

from . import cdc, who
from .plots import animation, cases_map, incidence_lines, who_animation


def main():
    """Fetch the latest CDC, Census and WHO data and write date-stamped outputs."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=Path("."), help="directory to write data/ and figures/ into")
    p.add_argument("--stamp", default=date.today().isoformat(), help="date stamp for file names")
    args = p.parse_args()

    df, cutoff = cdc.build()
    rows, pop, names = who.load()
    data, figs = args.out / "data", args.out / "figures"
    paths = {
        "us_data": data / "us" / f"{args.stamp}.csv",
        "who_data": data / "who" / f"{args.stamp}.csv",
        "us_lines": figs / "us" / "incidence_lines" / f"{args.stamp}.png",
        "us_map": figs / "us" / "cases_map" / f"{args.stamp}.png",
        "us_gif": figs / "us" / "animation" / f"{args.stamp}.gif",
        "world_gif": figs / "world" / "animation" / f"{args.stamp}.gif",
        "europe_gif": figs / "europe" / "animation" / f"{args.stamp}.gif",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(paths["us_data"], index=False, float_format="%.4f")
    who.table(rows, pop, names).to_csv(paths["who_data"], index=False, float_format="%.4f")
    incidence_lines(df, cutoff, paths["us_lines"])
    cases_map(df, paths["us_map"], (df.year.min(), df.year.max() - 1))  # full years only, as on CDC's map
    animation(df, paths["us_gif"])
    who_animation("World", *who.world(rows, pop, names), paths["world_gif"])
    who_animation("Europe", *who.europe(rows, pop, names), paths["europe_gif"])
    print(f"CDC data through {cutoff}; WHO data through {rows[rows.CASES.notna()].START_DATE.max()}")
    for path in paths.values():
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
