"""Fetch yearly dengue cases by country (WHO, gaps filled from OpenDengue) and World Bank population."""

import json
from datetime import date
from urllib.request import urlopen

import pandas as pd

# The WHO Global Dengue Surveillance dashboard (worldhealthorg.shinyapps.io/dengue_global) reads this table.
WHO = "https://xmart-api-public.who.int/ARBOV/V_DENGUE_GLOBAL_VALIDATED_PUBLIC?$format=csv"
OPENDENGUE = ("https://raw.githubusercontent.com/OpenDengue/master-repo/main/data/releases/V1.3.1/"
              "National_extract_V1_3_1.zip")
WB_COUNTRIES = "https://api.worldbank.org/v2/country?format=json&per_page=400"
WB_POP = "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?format=json&per_page=20000&date={}:{}"
FIRST = 2000  # OpenDengue covers about 95 countries a year from here on


def _world_bank(url):
    """Return the records of a World Bank API query."""
    return pd.DataFrame(json.load(urlopen(url))[1])


def countries():
    """Return World Bank ISO3 codes indexed by ISO2 code, regional and income aggregates dropped."""
    meta = _world_bank(WB_COUNTRIES)
    return meta[meta.region.str["value"] != "Aggregates"].set_index("iso2Code").id


def load():
    """Return yearly cases by country with their source, population by year and country names."""
    who = pd.read_csv(WHO)
    who = who[who.YEAR.between(FIRST, date.today().year)]  # also drops a few rows mistyped as 2027-29
    series = who.groupby(["YEAR", "ISO3", "DATE_TYPE"]).CASES.sum(min_count=1)
    cases = series.groupby(level=[0, 1]).max().unstack()  # some countries file weekly and monthly: keep the fuller
    od = pd.read_csv(OPENDENGUE)
    od = od[od.Year.between(FIRST, od.Year.max() - 1)]  # its latest year is partial
    filled = cases.combine_first(od.groupby(["Year", "ISO_A0"]).dengue_total.sum(min_count=1).unstack())
    source = pd.DataFrame("OpenDengue", filled.index, filled.columns).where(cases.reindex_like(filled).isna(), "WHO")

    wb = _world_bank(WB_POP.format(FIRST, date.today().year))
    wb = wb[wb.countryiso3code.isin(countries())].pivot(index="date", columns="countryiso3code", values="value")
    pop = wb.set_axis(wb.index.astype(int)).reindex(filled.index).ffill()  # latest estimate carried forward
    pop = pop.combine_first(who.groupby(["YEAR", "ISO3"]).POPULATION.mean().unstack().ffill().bfill())  # territories
    names = od.groupby("ISO_A0").adm_0_name.first().str.title().to_dict()
    return filled, source.where(filled.notna()), pop, names | who.groupby("ISO3").COUNTRY.first().to_dict()


def table(cases, source, pop, names):
    """Return a tidy yearly table: country, year, cases, source (per cell or one name), population, incidence."""
    source = pd.DataFrame(source, cases.index, cases.columns)
    out = pd.concat({"cases": cases.stack(), "source": source.stack()}, axis=1).dropna(subset="cases")
    out = out.rename_axis(["year", "iso3"]).join(pop.stack().rename_axis(["year", "iso3"]).rename("population"))
    out = out.reset_index()
    out.insert(1, "country", out.iso3.map(names))
    out["population"] = out.population.round().astype("Int64")
    out["incidence"] = out.cases / out.population * 1e5
    return out


def cumulative(cases, pop, total):
    """Return cumulative cases per 100k by country in `pop`, blank until it first reports, plus their overall total."""
    pop, cases = pop.loc[cases.index], cases.reindex(columns=pop.columns)
    overall = (cases.where(pop.notna()).sum(axis=1) / pop.sum(axis=1) * 1e5).rename(total)
    inc = pd.concat([cases / pop * 1e5, overall], axis=1)
    return inc.fillna(0).cumsum().where(inc.notna().cummax())
