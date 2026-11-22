"""Fetch WHO global dengue surveillance counts and WHO population figures."""

import json
from datetime import date
from urllib.request import urlopen

import numpy as np
import pandas as pd

# The WHO Global Dengue Surveillance dashboard (worldhealthorg.shinyapps.io/dengue_global) reads this table.
WHO = "https://xmart-api-public.who.int/ARBOV/V_DENGUE_GLOBAL_VALIDATED_PUBLIC?$format=csv"
GHO_POP = "https://ghoapi.azureedge.net/api/ORALHEALTH_DENOMINATOR_TTLPOP"  # WHO 2020 population (thousands)
FIRST = 2014  # the Americas join via PAHO; before this only 1-3 countries report
OVERSEAS = ["REU", "MYT"]  # filed under WHO Europe, but left out of WHO's own European trend


def load():
    """Return WHO dengue rows (one reporting series per country and year), population by year and country names."""
    df = pd.read_csv(WHO)
    df = df[df.YEAR.between(FIRST, date.today().year)]  # also drops a few rows mistyped as 2027-29
    tot = df.groupby(["ISO3", "YEAR", "DATE_TYPE"]).CASES.sum().reset_index()
    df = df.merge(tot.loc[tot.groupby(["ISO3", "YEAR"]).CASES.idxmax(), ["ISO3", "YEAR", "DATE_TYPE"]])  # fuller series
    gho = pd.DataFrame(json.load(urlopen(GHO_POP))["value"]).query("SpatialDimType == 'COUNTRY'")
    gho = gho.set_index("SpatialDim").NumericValue * 1e3
    pop = df.groupby(["YEAR", "ISO3"]).POPULATION.mean().unstack()
    pop = pop.reindex(columns=pop.columns.union(gho.index)).ffill().bfill()
    pop = pop.where(pop.notna(), gho, axis=1)  # WHO 2020 figures where the dengue table has none
    return df, pop, df.groupby("ISO3").COUNTRY.first().to_dict()


def table(df, pop, names):
    """Return a tidy yearly table: WHO region, country, year, cases, population, incidence per 100k."""
    out = df.groupby(["WHO_REGION", "ISO3", "YEAR"]).CASES.sum(min_count=1).rename("cases").reset_index()
    out = out.join(pop.stack().rename("population"), on=["YEAR", "ISO3"])
    out.insert(2, "country", out.ISO3.map(names))
    out["population"] = out.population.round().astype("Int64")
    out["incidence"] = out.cases / out.population * 1e5
    return out.rename(columns={"WHO_REGION": "region", "ISO3": "iso3", "YEAR": "year"})


def _cumulative(cases, pop, total):
    """Return cumulative cases per 100k, blank until a country first reports, plus a population-weighted total."""
    inc = (cases / pop * 1e5).assign(**{total: cases.where(pop.notna()).sum(axis=1) / pop.sum(axis=1) * 1e5})
    return inc.fillna(0).cumsum().where(inc.notna().cummax())


def world(df, pop, names):
    """Return yearly cumulative incidence by country with a World total, frame labels, populations and names."""
    cases = df.groupby(["YEAR", "ISO3"]).CASES.sum(min_count=1).unstack().reindex(columns=pop.columns)
    cum = _cumulative(cases, pop.loc[cases.index], "World")
    return cum, [str(y) for y in cum.index], pop.iloc[-1], names | {"World": "World"}


def europe(df, pop, names):
    """Return monthly cumulative incidence in mainland WHO Europe with a total, frame labels, populations and names."""
    eu = df[(df.WHO_REGION == "EUR") & ~df.ISO3.isin(OVERSEAS)]
    month = pd.to_datetime(eu.START_DATE).dt.to_period("M").rename("month")
    cases = eu.groupby([month, "ISO3"]).CASES.sum(min_count=1).unstack()
    cases = cases.reindex(pd.period_range(cases.index.min(), cases.dropna(how="all").index.max(), freq="M"))
    cum = _cumulative(cases, pop.loc[cases.index.year, cases.columns].set_axis(cases.index), "Europe")
    end = cases.index.year + cases.index.month / 12  # each month is plotted at its end
    cum = pd.concat([cum.iloc[[0]] * 0, cum]).set_axis(np.r_[end[0] - 1 / 12, end])  # lines start at zero
    labels = list(cases.index.strftime("%b %Y"))
    return cum, labels[:1] + labels, pop.iloc[-1], names | {"Europe": "Europe"}
