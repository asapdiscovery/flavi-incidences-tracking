"""Rebuild the dengue data snapshots and figures (US from CDC, world from WHO and OpenDengue, EU/EEA from ECDC)."""

import argparse
from datetime import date
from pathlib import Path

from . import cdc, europe, world
from .plots import animation, cases_map, incidence_lines, region_animation


def main():
    """Fetch the latest surveillance and population data and write date-stamped outputs."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=Path("."), help="directory to write data/ and figures/ into")
    p.add_argument("--stamp", default=date.today().isoformat(), help="date stamp for file names")
    args = p.parse_args()

    df, cutoff = cdc.build()
    cases, source, pop, names = world.load()
    eu, eu_names = europe.load(world.countries())
    data, figs = args.out / "data", args.out / "figures"
    paths = {
        "us_data": data / "us" / f"{args.stamp}.csv",
        "world_data": data / "world" / f"{args.stamp}.csv",
        "europe_data": data / "europe" / f"{args.stamp}.csv",
        "us_lines": figs / "us" / "incidence_lines" / f"{args.stamp}.png",
        "us_map": figs / "us" / "cases_map" / f"{args.stamp}.png",
        "us_gif": figs / "us" / "animation" / f"{args.stamp}.gif",
        "world_gif": figs / "world" / "animation" / f"{args.stamp}.gif",
        "europe_gif": figs / "europe" / "animation" / f"{args.stamp}.gif",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(paths["us_data"], index=False, float_format="%.4f")
    world.table(cases, source, pop, names).to_csv(paths["world_data"], index=False, float_format="%.4f")
    world.table(eu, "ECDC", pop, eu_names).to_csv(paths["europe_data"], index=False, float_format="%.4f")
    incidence_lines(df, cutoff, paths["us_lines"])
    cases_map(df, paths["us_map"], (df.year.min(), df.year.max() - 1))  # full years only, as on CDC's map
    animation(df, paths["us_gif"])
    region_animation("World", world.cumulative(cases, pop, "World"), pop.iloc[-1], names, paths["world_gif"])
    region_animation("EU/EEA", world.cumulative(eu, pop[eu.columns], "EU/EEA"), pop.iloc[-1], eu_names,
                     paths["europe_gif"])
    print(f"CDC data through {cutoff}; WHO/OpenDengue through {cases.index[-1]}; ECDC through {eu.index[-1]}")
    for path in paths.values():
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
