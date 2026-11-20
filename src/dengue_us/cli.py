"""Rebuild the dengue data snapshot and figures, stamped with today's date."""

import argparse
from datetime import date
from pathlib import Path

from .data import build
from .plots import animation, cases_map, incidence_lines


def main():
    """Fetch the latest CDC and Census data and write date-stamped outputs."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=Path("."), help="directory to write data/ and figures/ into")
    p.add_argument("--stamp", default=date.today().isoformat(), help="date stamp for file names")
    args = p.parse_args()

    df, cutoff = build()
    paths = {
        "data": args.out / "data" / f"{args.stamp}.csv",
        "lines": args.out / "figures" / "incidence_lines" / f"{args.stamp}.png",
        "map": args.out / "figures" / "cases_map" / f"{args.stamp}.png",
        "gif": args.out / "figures" / "animation" / f"{args.stamp}.gif",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(paths["data"], index=False, float_format="%.4f")
    incidence_lines(df, cutoff, paths["lines"])
    cases_map(df, paths["map"], (df.year.min(), df.year.max() - 1))  # full years only, as on CDC's map
    animation(df, paths["gif"])
    print(f"CDC data through {cutoff}")
    for path in paths.values():
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
