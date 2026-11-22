# Dengue incidence: United States, world and Europe

Figures tracking reported dengue incidence, rebuilt from public surveillance data whenever the pipeline is rerun. The US figures come from CDC data; the world and Europe figures come from WHO data only. Each run writes date-stamped files, so the folders under `figures/` build up a running history.

## Usage

```bash
uv run dengue-incidence            # fetch latest data, write today's figures + data snapshots
uv run dengue-incidence --stamp 2026-12-01 --out .
```

Outputs:

| Path | Content |
|---|---|
| `figures/us/incidence_lines/<date>.png` | Cumulative cases per 100k by state since 2010; US total and selected states highlighted |
| `figures/us/animation/<date>.gif` | US map of cumulative incidence filling in by year, alongside the line plot (`.png`: final frame) |
| `figures/us/cases_map/<date>.png` | Cumulative cases by jurisdiction, binned as on CDC's map (sanity check against cdc.gov) |
| `figures/world/animation/<date>.gif` | World map and per-country lines by year since 2014 (`.png`: final frame) |
| `figures/europe/animation/<date>.gif` | WHO European Region map and per-country lines by month since 2024 (`.png`: final frame) |
| `data/us/<date>.csv` | Tidy CDC table: status, state, year, cases, population, incidence per 100k |
| `data/who/<date>.csv` | Tidy WHO table: region, country, year, cases, population, incidence per 100k |

## Data

**United States**
- **Cases**: CDC [ArboNET](https://www.cdc.gov/mosquitoes/php/arbonet/), from the CSV extracts behind the CDC dengue dashboards ([historic](https://www.cdc.gov/dengue/data-research/facts-stats/historic-data.html), [current year](https://www.cdc.gov/dengue/data-research/facts-stats/current-data.html)). They are served from `https://www.cdc.gov/wcms/vizdata/live/ncezid_dvbd/DEN/`.
- **Population**: US Census Bureau state population estimates. Vintage 2020 covers 2010–2019; the newest available vintage covers 2020 on, and its latest estimate is carried forward to years not yet released.

**World and Europe**
- **Cases**: the [WHO Global Dengue Surveillance dashboard](https://worldhealthorg.shinyapps.io/dengue_global/), via its public API `xmart-api-public.who.int/ARBOV/V_DENGUE_GLOBAL_VALIDATED_PUBLIC`.
  - These are national counts (suspected and confirmed cases) reported by ministries of health to WHO. Data for the Americas arrives via PAHO's PLISA.
  - There is no public global database upstream of this table.
- **Population**: taken from the same table where it is given (the Americas, yearly). Elsewhere it is WHO GHO's 2020 total population (`ORALHEALTH_DENOMINATOR_TTLPOP`).

**Map outlines** (bundled in `src/dengue_incidence/`)
- US: [us-atlas](https://github.com/topojson/us-atlas) 3.0.1 (ISC license, from Census cartographic boundaries).
- World: [Natural Earth](https://www.naturalearthdata.com/) 1:50m admin-0 map units (public domain). Shapes are merged to one per ISO3 code, Antarctica is dropped and outlines are simplified. French overseas departments are mapped separately from France.

## Caveats

**United States** (from CDC)
- Cases are counted by state of residence, not where infection occurred.
- The two most recent years are provisional, and the current year is year to date.
- "United States" means the 50 states + DC; Puerto Rico and other territories are reported separately.

**World and Europe** (WHO)
- WHO's global system started in 2024. Before that, the table holds the Americas from 2014 plus a handful of Asian countries (Indonesia, Thailand, Sri Lanka, Bangladesh, Nepal) and Australia. Most of Africa, Europe, the Eastern Mediterranean and the Western Pacific first report in 2023–24. Maps leave countries white until their first report.
- The World line is all reported cases divided by the population of every WHO member state and reporting territory. Before 2024 it is pulled down by countries not yet reporting.
- The line plots show countries of at least 1 million people; smaller ones are only mapped. Thirteen small territories have no WHO population figure and show as no data.
- Europe is the WHO European Region, which also covers Turkey, the Caucasus and Central Asia. Its data starts in 2024 and counts locally acquired cases. Réunion and Mayotte are filed under it but left out here, as in WHO's own European trend.
- Surveillance and case definitions differ between countries and over time. The current year of the world plot is partial (dashed).
- Where a country files both weekly and monthly series, the fuller one is kept. Rows dated after the current year are typos and are dropped.
