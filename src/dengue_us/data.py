"""Fetch CDC ArboNET dengue case counts and Census population estimates."""

from urllib.error import HTTPError

import pandas as pd

# CDC's dengue dashboards (historic + current year) are drawn from these ArboNET extracts.
# cdc.gov rejects browser-like user agents; pandas' default urllib agent is accepted.
CDC = "https://www.cdc.gov/wcms/vizdata/live/ncezid_dvbd/DEN"
CENSUS = "https://www2.census.gov/programs-surveys/popest/datasets"

_JURISDICTIONS = """
AL 1 Alabama|AK 2 Alaska|AZ 4 Arizona|AR 5 Arkansas|CA 6 California|CO 8 Colorado
CT 9 Connecticut|DE 10 Delaware|DC 11 District of Columbia|FL 12 Florida|GA 13 Georgia
HI 15 Hawaii|ID 16 Idaho|IL 17 Illinois|IN 18 Indiana|IA 19 Iowa|KS 20 Kansas|KY 21 Kentucky
LA 22 Louisiana|ME 23 Maine|MD 24 Maryland|MA 25 Massachusetts|MI 26 Michigan|MN 27 Minnesota
MS 28 Mississippi|MO 29 Missouri|MT 30 Montana|NE 31 Nebraska|NV 32 Nevada|NH 33 New Hampshire
NJ 34 New Jersey|NM 35 New Mexico|NY 36 New York|NC 37 North Carolina|ND 38 North Dakota
OH 39 Ohio|OK 40 Oklahoma|OR 41 Oregon|PA 42 Pennsylvania|RI 44 Rhode Island
SC 45 South Carolina|SD 46 South Dakota|TN 47 Tennessee|TX 48 Texas|UT 49 Utah|VT 50 Vermont
VA 51 Virginia|WA 53 Washington|WV 54 West Virginia|WI 55 Wisconsin|WY 56 Wyoming
AS 60 American Samoa|FM 64 Micronesia|GU 66 Guam|MH 68 Marshall Islands|MP 69 Northern Mariana Islands
PW 70 Palau|PR 72 Puerto Rico|VI 78 U.S. Virgin Islands|US 0 United States
"""
_rows = [r.split(" ", 2) for r in _JURISDICTIONS.replace("\n", "|").split("|") if r]
FIPS = {abbr: int(fips) for abbr, fips, _ in _rows}
NAMES = {abbr: name for abbr, _, name in _rows}
STATES = [s for s, f in FIPS.items() if 0 < f <= 56]  # 50 states + DC
STATUSES = ["All", "Locally acquired", "Travel associated"]


def cases():
    """Return yearly dengue cases by jurisdiction and travel status, and the CDC data cutoff."""
    hist = pd.read_csv(f"{CDC}/Cases_by_Jurisdiction_Historic.csv", dtype={"Year": str})
    hist = hist[~hist.Year.str.contains("-")]  # drop the multi-year total rows
    cur = pd.read_csv(f"{CDC}/Cases_by_Jurisdiction_Current.csv", dtype={"Year": str})
    df = pd.concat([hist, cur]).rename(
        columns={"Year": "year", "Travel status": "status", "Jurisdiction": "state", "Count": "cases"}
    )
    df["year"] = df.year.astype(int)
    df = df.drop_duplicates(["year", "status", "state"], keep="last")[["year", "status", "state", "cases"]]
    cutoff = pd.read_csv(f"{CDC}/Data_Bites_Current.csv").Cutoff.iloc[0]
    return df, cutoff


def _pop_wide(df, years):
    """Reshape a Census NST-EST file to a state x year population table."""
    df = df[df.SUMLEV.isin([10, 40])].set_index("STATE")
    out = df[[f"POPESTIMATE{y}" for y in years]].set_axis(list(years), axis=1)
    return out.rename(index={f: s for s, f in FIPS.items()})


def population(last_year):
    """Return July 1 population by state and year, carrying the newest Census vintage forward."""
    old = pd.read_csv(f"{CENSUS}/2010-2020/state/totals/nst-est2020-alldata.csv", encoding="latin-1")
    for v in range(last_year, 2020, -1):
        try:
            new = pd.read_csv(f"{CENSUS}/2020-{v}/state/totals/NST-EST{v}-ALLDATA.csv", encoding="latin-1")
            break
        except HTTPError:
            continue
    pop = _pop_wide(old, range(2010, 2020)).join(_pop_wide(new, range(2020, v + 1)))
    for y in range(v + 1, last_year + 1):
        pop[y] = pop[v]
    return pop


def build():
    """Return a tidy table of cases, population and incidence per 100k, and the CDC data cutoff."""
    raw, cutoff = cases()
    years = range(raw.year.min(), raw.year.max() + 1)
    juris = list(FIPS) + sorted(set(raw.state) - set(FIPS))
    idx = pd.MultiIndex.from_product([STATUSES, juris, years], names=["status", "state", "year"])
    df = raw.set_index(["status", "state", "year"]).cases.reindex(idx, fill_value=0).unstack("year")
    for st in STATUSES:
        df.loc[(st, "US")] = df.loc[st].loc[STATES].sum()
    pop = population(years[-1]).rename_axis("state").stack().rename("population")
    out = df.stack().rename("cases").reset_index().join(pop, on=["state", "year"])
    out["population"] = out.population.astype("Int64")
    out["incidence"] = out.cases / out.population * 1e5
    return out, cutoff
