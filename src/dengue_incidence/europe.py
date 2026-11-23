"""Fetch yearly dengue cases reported to ECDC by EU/EEA countries."""

import json
from urllib.request import urlopen

import pandas as pd

# ECDC Surveillance Atlas of Infectious Diseases (atlas.ecdc.europa.eu): dengue, all reported cases, by country.
ECDC = ("https://atlas.ecdc.europa.eu/public/AtlasService/rest/GetMeasuresResults?healthTopicId=16&datasetId=438"
        "&measurePopulation=All%20cases&measureIds=1185776&measureTypes=I&timeCodes=&geoCodes=&geoLevel=1"
        "&timeUnit=Year&isPivotByTimePeriod=false")
FIRST = 2010  # as in the US figures


def load(iso3):
    """Return yearly cases by ISO3 code from FIRST, and country names."""
    d = pd.DataFrame(json.load(urlopen(ECDC))["MeasureResults"])
    d = d[(d.TimeCode.str.len() == 4) & d.GeoCountry.notna()]  # yearly, by country (not EU totals)
    d = d[d.GeoCountry != "UK"]  # reported until it left the EU in 2020
    d["iso3"] = d.GeoCountry.replace({"EL": "GR"}).map(iso3)
    cases = d.pivot(index="TimeCode", columns="iso3", values="N")
    return cases.set_axis(cases.index.astype(int)).loc[FIRST:], d.groupby("iso3").GeoLabel.first().to_dict()
