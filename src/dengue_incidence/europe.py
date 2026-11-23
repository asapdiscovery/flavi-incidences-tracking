"""Fetch yearly dengue and West Nile virus cases reported to ECDC by EU/EEA countries."""

import json
from urllib.request import urlopen

import pandas as pd

# ECDC Surveillance Atlas of Infectious Diseases (atlas.ecdc.europa.eu): yearly cases by country.
ECDC = ("https://atlas.ecdc.europa.eu/public/AtlasService/rest/GetMeasuresResults?healthTopicId={}&datasetId=438"
        "&measurePopulation=&measureIds={}&measureTypes=I&timeCodes=&geoCodes=&geoLevel=1&timeUnit=Year"
        "&isPivotByTimePeriod=false")
DENGUE, WNV = (16, 1185776), (60, 1185894)  # health topic and measure: all dengue cases, locally acquired West Nile
EU_EEA = "AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IS IT LI LT LU LV MT NL NO PL PT RO SE SI SK".split()  # not UK
FIRST = 2010  # as in the US dengue figures


def load(iso3, measure=DENGUE):
    """Return yearly cases by ISO3 code from FIRST, and country names."""
    d = pd.DataFrame(json.load(urlopen(ECDC.format(*measure)))["MeasureResults"])
    d = d[(d.TimeCode.str.len() == 4) & d.GeoCountry.isin(EU_EEA) & (d.dGeoMnemonic == d.GeoCountry)]  # country-years
    d["iso3"] = d.GeoCountry.replace({"EL": "GR"}).map(iso3)
    cases = d.pivot(index="TimeCode", columns="iso3", values="N")
    return cases.set_axis(cases.index.astype(int)).loc[FIRST:], d.groupby("iso3").GeoLabel.first().to_dict()
