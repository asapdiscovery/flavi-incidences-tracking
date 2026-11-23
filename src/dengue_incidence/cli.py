"""Rebuild the data snapshots and figures: dengue (CDC, WHO, OpenDengue, ECDC) and West Nile virus (CDC, ECDC)."""

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

    raw, cutoff = cdc.cases()
    df = cdc.build(raw)
    wnv_raw, wnv_cutoff = cdc.wnv_cases()
    wnv = cdc.build(wnv_raw, ["Neuroinvasive"])
    cases, source, pop, names = world.load()
    iso3 = world.countries()
    eu, eu_names = europe.load(iso3)
    eu_wnv, eu_wnv_names = europe.load(iso3, europe.WNV)
    data, figs, stamp = args.out / "data", args.out / "figures", args.stamp
    paths = {  # by virus, then region
        "us_data": data / "dengue" / "us" / f"{stamp}.csv",
        "world_data": data / "dengue" / "world" / f"{stamp}.csv",
        "europe_data": data / "dengue" / "europe" / f"{stamp}.csv",
        "us_lines": figs / "dengue" / "us" / "incidence_lines" / f"{stamp}.png",
        "us_map": figs / "dengue" / "us" / "cases_map" / f"{stamp}.png",
        "us_gif": figs / "dengue" / "us" / "animation" / f"{stamp}.gif",
        "world_gif": figs / "dengue" / "world" / "animation" / f"{stamp}.gif",
        "europe_gif": figs / "dengue" / "europe" / "animation" / f"{stamp}.gif",
        "wnv_us_data": data / "wnv" / "us" / f"{stamp}.csv",
        "wnv_europe_data": data / "wnv" / "europe" / f"{stamp}.csv",
        "wnv_us_gif": figs / "wnv" / "us" / "animation" / f"{stamp}.gif",
        "wnv_europe_gif": figs / "wnv" / "europe" / "animation" / f"{stamp}.gif",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(paths["us_data"], index=False, float_format="%.4f")
    world.table(cases, source, pop, names).to_csv(paths["world_data"], index=False, float_format="%.4f")
    world.table(eu, "ECDC", pop, eu_names).to_csv(paths["europe_data"], index=False, float_format="%.4f")
    wnv.to_csv(paths["wnv_us_data"], index=False, float_format="%.4f")
    world.table(eu_wnv, "ECDC", pop, eu_wnv_names).to_csv(paths["wnv_europe_data"], index=False, float_format="%.4f")
    incidence_lines(df, cutoff, paths["us_lines"])
    cases_map(df, paths["us_map"], (df.year.min(), df.year.max() - 1))  # full years only, as on CDC's map
    animation(df, paths["us_gif"])
    region_animation("World", world.cumulative(cases, pop, "World"), pop.iloc[-1], names, paths["world_gif"])
    region_animation("EU/EEA", world.cumulative(eu, pop[eu.columns], "EU/EEA"), pop.iloc[-1], eu_names,
                     paths["europe_gif"])
    animation(wnv, paths["wnv_us_gif"], "West Nile virus")
    region_animation("EU/EEA", world.cumulative(eu_wnv, pop[eu_wnv.columns], "EU/EEA"), pop.iloc[-1], eu_wnv_names,
                     paths["wnv_europe_gif"], "West Nile virus")
    print(f"Dengue: CDC data through {cutoff}; WHO/OpenDengue through {cases.index[-1]}; ECDC through {eu.index[-1]}")
    print(f"West Nile virus: CDC data through {wnv_cutoff}; ECDC through {eu_wnv.index[-1]}")
    for path in paths.values():
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
