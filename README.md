# Dengue incidence in the United States

Figures tracking reported dengue cases and incidence by US state, rebuilt from CDC data whenever the pipeline is rerun. Each run drops date-stamped files, so the folders under `figures/` form a running history.

## Usage

```bash
uv run dengue-us            # fetch latest data, write today's figures + data snapshot
uv run dengue-us --stamp 2026-12-01 --out .
```

Outputs:

| Path | Content |
|---|---|
| `figures/incidence_lines/<date>.png` | Cumulative cases per 100k by state since 2010; US total and selected states highlighted |
| `figures/animation/<date>.gif` | Map of cumulative incidence filling in by year, alongside the line plot |
| `figures/cases_map/<date>.png` | Cumulative cases by jurisdiction, binned as on CDC's map (sanity check against cdc.gov) |
| `data/<date>.csv` | Tidy table: status, state, year, cases, population, incidence per 100k |

## Data

- **Cases**: CDC [ArboNET](https://www.cdc.gov/mosquitoes/php/arbonet/) via the CSV extracts behind the CDC dengue dashboards ([historic](https://www.cdc.gov/dengue/data-research/facts-stats/historic-data.html), [current year](https://www.cdc.gov/dengue/data-research/facts-stats/current-data.html)), served from `https://www.cdc.gov/wcms/vizdata/live/ncezid_dvbd/DEN/`.
- **Population**: US Census Bureau state population estimates (vintage 2020 for 2010–2019, newest available vintage for 2020 on; the latest estimate is carried forward to years not yet released).

- **Map outlines**: [us-atlas](https://github.com/topojson/us-atlas) 3.0.1 (ISC license, from Census cartographic boundaries), bundled in `src/dengue_us/`.

Caveats (from CDC): cases are counted by state of residence, not where infection occurred; the two most recent years are provisional; the current year is year to date. "United States" here means the 50 states + DC; Puerto Rico and other territories are reported separately.
