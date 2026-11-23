# Flavivirus incidence tracking: dengue and West Nile virus

Figures tracking reported dengue and West Nile virus incidence, rebuilt from public surveillance data whenever the pipeline is rerun. Dengue: the US figures come from CDC data, the world figures from WHO (gaps filled from OpenDengue) and the Europe figures from ECDC. West Nile virus: the US figure comes from CDC data and the Europe figure from ECDC. Each run writes date-stamped files, so the folders under `figures/` build up a running history.

## Usage

```bash
uv run dengue-incidence            # fetch latest data, write today's figures + data snapshots
uv run dengue-incidence --stamp 2026-12-01 --out .
```

Outputs are grouped by virus, then region. Each `.gif` has a `.png` of its final frame next to it.

```
figures/
  dengue/
    us/        animation/  incidence_lines/  cases_map/
    world/     animation/
    europe/    animation/
  wnv/         West Nile virus
    us/        animation/
    europe/    animation/
    world/     README only: WHO does not track West Nile virus
data/          the same virus and region folders, one CSV per run
```

| Path | Content |
|---|---|
| `figures/dengue/us/incidence_lines/<date>.png` | Cumulative cases per 100k by state since 2010; US total and selected states highlighted |
| `figures/dengue/us/animation/<date>.gif` | US map of cumulative incidence filling in by year, alongside the line plot |
| `figures/dengue/us/cases_map/<date>.png` | Cumulative cases by jurisdiction, binned as on CDC's map (sanity check against cdc.gov) |
| `figures/dengue/world/animation/<date>.gif` | World map and per-country lines by year since 2000, top 3 countries and 4 others highlighted |
| `figures/dengue/europe/animation/<date>.gif` | EU/EEA map and per-country lines by year since 2010, top 3 countries highlighted |
| `figures/wnv/us/animation/<date>.gif` | US map and per-state lines of neuroinvasive cases by year since 1999, 5 states highlighted |
| `figures/wnv/europe/animation/<date>.gif` | EU/EEA map and per-country lines of locally acquired cases by year since 2010, top 3 countries and Italy highlighted |
| `data/dengue/us/<date>.csv` | Tidy CDC table: status, state, year, cases, population, incidence per 100k |
| `data/dengue/world/<date>.csv` | Tidy world table: year, country, cases, source (WHO or OpenDengue), population, incidence per 100k |
| `data/dengue/europe/<date>.csv` | Tidy ECDC table, same columns as the world one |
| `data/wnv/us/<date>.csv` | Tidy CDC table of neuroinvasive cases, same columns as `data/dengue/us` |
| `data/wnv/europe/<date>.csv` | Tidy ECDC table of locally acquired cases, same columns as `data/dengue/europe` |

## Data

**Dengue, United States**
- **Cases**: CDC [ArboNET](https://www.cdc.gov/mosquitoes/php/arbonet/), from the CSV extracts behind the CDC dengue dashboards ([historic](https://www.cdc.gov/dengue/data-research/facts-stats/historic-data.html), [current year](https://www.cdc.gov/dengue/data-research/facts-stats/current-data.html)). They are served from `https://www.cdc.gov/wcms/vizdata/live/ncezid_dvbd/DEN/`.

**Dengue, world**
- **Cases**: the [WHO Global Dengue Surveillance dashboard](https://worldhealthorg.shinyapps.io/dengue_global/), via its public API `xmart-api-public.who.int/ARBOV/V_DENGUE_GLOBAL_VALIDATED_PUBLIC`. These are national counts (suspected and confirmed cases) reported by ministries of health to WHO; data for the Americas arrive via PAHO's PLISA. WHO's global collection started in 2024. Before that the table holds little beyond the Americas (from 2014), and nothing before 2014.
- **Gaps**: country-years missing from WHO's table are filled from [OpenDengue](https://opendengue.org) (national extract, V1.3.1), a research compilation of national counts from WHO regional offices (PAHO for the Americas), Project Tycho, ministries of health and the literature. It supplies every figure before 2014, and most of South and East Asia and the Pacific until 2024. It covers about 95 countries a year from 2000. Its latest year is partial and is not used. Neither source copies the other: where both have a figure they agree exactly about 70% of the time, as both draw on the same national and regional reports. Citation: Clarke J et al. OpenDengue: data from the OpenDengue database, version 1.3, figshare (2025), [doi:10.6084/m9.figshare.24259573](https://doi.org/10.6084/m9.figshare.24259573); [paper](https://doi.org/10.1038/s41597-024-03120-7).

**Dengue, Europe**
- **Cases**: [ECDC Surveillance Atlas of Infectious Diseases](https://atlas.ecdc.europa.eu/public/index.aspx) (data from TESSy). It gives all reported dengue cases by EU/EEA country, via the atlas's public API `atlas.ecdc.europa.eu/public/AtlasService/rest/GetMeasuresResults`. Cases are counted by the country where they are diagnosed and notified, normally where the patient lives, as CDC counts the US cases. Most are travel-associated: the person was infected abroad and fell ill or was diagnosed after coming home. In 2010–2024, 1.5% of cases were locally acquired (France, Italy, Spain and a few in Germany). Local spread needs the tiger mosquito (*Aedes albopictus*), which is established in southern Europe but not in the Nordic countries.

**West Nile virus, United States**
- **Cases**: CDC ArboNET, from the CSV extracts behind the CDC West Nile dashboards ([historic](https://www.cdc.gov/west-nile-virus/data-maps/historic-data.html), [current year](https://www.cdc.gov/west-nile-virus/data-maps/current-year-data.html)), served from `https://www.cdc.gov/wcms/vizdata/live/ncezid_dvbd/WNV/`. The figure counts neuroinvasive disease (meningitis, encephalitis, acute flaccid paralysis) by state of residence. Most infections are mild or silent and are rarely tested, so CDC compares areas by neuroinvasive cases, which are reported more consistently. CDC publishes the current year by state only for all cases, so its neuroinvasive cases are summed from CDC's county table.

**West Nile virus, Europe**
- **Cases**: the same ECDC atlas, locally acquired cases by EU/EEA country. Unlike dengue, nearly all West Nile cases reported in the EU/EEA were caught in the reporting country (96% in 2010–2024), so the map shows where people are infected. The virus is carried by *Culex* mosquitoes, which are common across Europe; most cases are in Greece, Italy, Romania and Hungary.

**Population**
- US: US Census Bureau state population estimates. The 2000–2010 intercensal estimates cover 2000–2009, vintage 2020 covers 2010–2019 and the newest available vintage covers 2020 on. The latest estimate is carried forward to years not yet released, and 1999 uses the 2000 estimate.
- World and Europe: World Bank total population (`SP.POP.TOTL`), yearly, with the latest estimate carried forward. Territories the World Bank does not list separately (e.g. French Guiana, Guadeloupe, Martinique) use the population in WHO's dengue table.

**Map outlines** (bundled in `src/dengue_incidence/`)
- US: [us-atlas](https://github.com/topojson/us-atlas) 3.0.1 (ISC license, from Census cartographic boundaries).
- World: [Natural Earth](https://www.naturalearthdata.com/) 1:50m admin-0 map units (public domain). Shapes are merged to one per ISO3 code, Antarctica is dropped and outlines are simplified. French overseas departments are mapped separately from France.

## Caveats

**United States** (CDC)
- Cases are counted by state of residence, not where infection occurred.
- The two most recent years are provisional, and the current year is year to date (dashed).
- "United States" means the 50 states + DC; Puerto Rico and other territories are reported separately.
- West Nile: the county table misses a few current-year cases that CDC counts nationally (1,378 of 1,434 neuroinvasive cases in 2026 so far). The highlighted states are set in `plots.py`: the three with the highest cumulative incidence (South Dakota, North Dakota, Nebraska), Arizona for its record 2021 outbreak and California for the most cases.

**World** (WHO, OpenDengue)
- The world figure starts in 2000; the US and Europe dengue figures start in 2010. Figures from the 2000s are all from OpenDengue, and surveillance has changed a lot since, so early years compare less well.
- Before 2024, neither source covers most of Africa, Europe or the Eastern Mediterranean. Countries without data are gray, the same as those under 1 per 100,000.
- The World line divides all reported cases by the population of every country, so before 2024 it is pulled down by countries not yet reporting.
- A country's series can switch source, mostly from OpenDengue to WHO in 2024. The CSV records the source of each figure.
- WHO and OpenDengue count only locally acquired cases in Europe, so Europe is near zero on the world map. The Europe figure counts all reported cases instead.
- The current year is partial (dashed). Where a country files both weekly and monthly series to WHO, the fuller one is kept. Rows dated after the current year are typos and are dropped.

**Europe** (ECDC)
- EU/EEA means the EU plus Iceland, Liechtenstein and Norway. The UK reported until 2019 and is left out. Other countries are gray: ECDC also publishes West Nile cases from some neighbours (e.g. Serbia, Türkiye), but they are left out.
- ECDC's atlas is updated yearly and lags well behind, so the series ends earlier than the world and US ones.
- Not every country reported from the start: 23–24 did in 2010 and 29–30 by 2023. Surveillance systems differ between countries.
- The map shows the mainland and Iceland. Cyprus and the Atlantic islands are off the map but included in the lines.

**World and Europe**
- The line plots show countries of at least 1 million people; smaller ones are only mapped. The three with the highest final cumulative incidence are highlighted on the lines. The world figure also highlights two recent risers (Panama, Argentina) and two mid-range countries (Bolivia, Sri Lanka), and the West Nile Europe figure Italy (the most cases); these are set in `plots.py`.
- Surveillance and case definitions differ between countries and over time.
