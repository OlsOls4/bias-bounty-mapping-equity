---
title: "Estimating Coverage Gaps without Labels: Method Documentation"
subtitle: "Bias Bounty Mapping Equity Challenge · Best Documentation entry · Zindi user Olsols4"
date: "October 2026"
geometry: margin=2cm
fontsize: 10pt
---

# 1. What we did, in plain English

The challenge asks for a coverage-gap score between 0 (fully mapped) and 1 (not mapped) for each census tract. The organisers built the true scores by comparing Overture Maps with reference layers that were later removed from the data package. No labels were released. **We therefore submit a transparent prior, not a trained model.** Every tract gets a baseline of 0.035, plus up to 0.07 depending on how rural its population is, plus 0.04 if it overlaps tribal land. We set these three numbers by hand and checked them against whole-submission leaderboard scores (six submissions in total); they were never fitted to labels. Separately, our Bias Discovery report measures *where Overture's data comes from* in each tract, using only the provided files. Section 6 shows how those measurements could become component estimates.

> **Glossary.** *Tract*: a US census tract, keyed by its 11-digit `GEOID`. *Component*: one of the three gaps (roads, buildings, places) that make up the score. *Defined / undefined*: a component is undefined when the tract has nothing in the reference to compare against. *Reference layer*: the authoritative dataset Overture was compared with. *RMSE*: root mean squared error, the leaderboard metric (section 4.4). *Lineage / source*: which upstream dataset supplied an Overture feature (OpenStreetMap, Microsoft ML, Google ML, Esri, Meta, ...). *ML footprint*: a building outline detected from imagery by a machine-learning model. *Public leaderboard (LB)*: the RMSE Zindi shows for each submission on part of the test tracts. *Prior*: a simple rule set from domain reasoning, not learned from data. *Stratum*: a group of tracts (for example rural, high SVI). *SVI*: CDC Social Vulnerability Index percentile.

# 2. Data sources

| Source | Version | Used for | Status |
|----------------------|----------------|------------------------|---------|
| Overture Maps buildings, places, roads (challenge extracts) | release 2026-08-19.0 | source, attribute completeness, counts, road km | measured |
| Census ACS housing units (table B25001) | 2020–2024 5-year | homes per tract (denominator) | measured |
| Census tract polygons and attributes, as shipped by the challenge | 2020 population; 2025 tract boundaries | tract shapes, land area, `pct_urban`, `ur_class` | measured |
| Strata table: SVI 2022, CVI, urban/rural, tribal overlap, drought, wildfire, heat, fire history, weather stations | vintage column per source in the file | strata and v5 inputs | measured |
| Scored tract list (sample submissions) | as shipped | the 9,794 tracts we predict | given |
| Public-leaderboard RMSE of our own six submissions | 13 Oct 2026 | calibrating the v5 prior | leaderboard-derived |
| Overture Buildings Guide, <https://docs.overturemaps.org/guides/buildings/> | page updated 19 Aug 2026; retrieved 14 Oct 2026 | conflation priority, 10 m² ML rule (interpretation only) | external documentation |
| Challenge page, <https://zindi.world/competitions/bias-bounty-mapping-equity-challenge>, and the bucket `README.md` | retrieved 14 Oct 2026 | component definitions | external documentation |

Files read, per region `<r>` (7 files × 5 regions):

```
reference/<r>/<r>-overture-buildings.parquet     reference/<r>/<r>-census-acs-housing.parquet
reference/<r>/<r>-overture-pois.parquet          reference/<r>/<r>-sample-submission.csv
reference/<r>/<r>-overture-roads.parquet         strata/<r>/<r>-strata-tract-table.parquet
                                                 strata/<r>/<r>-census-tracts.parquet
```

**Data audit.** We read only the 35 files listed in `reports/DATA_SHA256SUMS.txt` (7 per region × 5 regions), all fetched by `reports/get_data.sh` from the challenge's public Source Cooperative bucket (`humane-intelligence/bias-bounty-mapping-equity-challenge`). We did **not** use, download or reconstruct any removed reference layer: TIGER/Line roads, Microsoft building footprints, the facility layer (USGS National Map facility counts on the current challenge page; called HIFLD in the bucket README), County Business Patterns, or the `<region>-coverage-gap.csv` files. The strata table carries USFS Wildfire-Risk and CarbonPlan columns that count buildings, housing units or people (for example `usfs_BuildingCount_sum`, `usfs_HUCount_sum`, `carbonplan_buildings`). These may derive from Microsoft footprints, so `build_master.py` **drops them at build time** (26 columns). Only hazard measures such as `usfs_WHP_mean` remain. The challenge page describes four regions; the bucket README adds `eastern-wa` (415 tracts, added 2026-09-08). Zindi scores all five (9,794 rows), and we include all five.

# 3. The target: coverage-gap score and its components

The challenge defines the score as **the mean of the components that are defined for the tract**. A defined component is a number in [0, 1]; an undefined component is left out, so the divisor is 1, 2 or 3. Tracts with no defined component are dropped from the scored list. Undefined components are common: the challenge reports that at least one is undefined in 21% of eastern Oklahoma tracts, 37% of northern California, 28% of south-central Texas and 55% of Maricopa.

Write $O$ for the Overture quantity in the tract and $R$ for the reference quantity. The README gives the per-type form $g = 1 - \min(1, O/R)$ for the facilities half of the places component. **We assume the same form for the other comparisons; the challenge page only says they "compare" the two quantities.**

**Road network gap** (named highways only):
$$\texttt{transport\_gap} = 1-\min\Big(1,\ \frac{\text{km of Overture motorway, trunk, primary, secondary}}{\text{km of TIGER S1100 + S1200}}\Big)$$

**Building footprint gap** (ACS homes are a sanity check only, not part of the ratio):
$$\texttt{building\_gap} = 1-\min\Big(1,\ \frac{\text{Overture building count}}{\text{Microsoft footprint count}}\Big)$$

**Places (POI) gap**: the mean of a facilities half and an establishments half, where $t$ runs over the facility types defined in the tract:
$$\texttt{poi\_gap} = \tfrac12\Big[\operatorname*{mean}_{t\,\in\,\{\text{fire, EMS, school}\}}\Big(1-\min\big(1, \tfrac{O_t}{R_t}\big)\Big) + \Big(1-\min\big(1, \tfrac{\text{all Overture places}}{\text{CBP establishments}}\big)\Big)\Big]$$

| Component | Plain English | Undefined when | What our method estimates |
|-----------|------------------------|------------------|----------------------------|
| `transport_gap` | How much of the named-highway network Overture is missing | the tract has no TIGER named highway | Not estimated separately; v5 has no road term. Overture major-road km is measured (`road_km.py`) |
| `building_gap` | How many buildings Overture is missing against Microsoft's ML footprints | no Microsoft footprint in the tract | Not estimated separately; we measure source shares and buildings per home (section 6) |
| `poi_gap` | How many emergency facilities, schools and businesses Overture is missing | a facility type: no reference facility of that type; the whole component: no facility *and* no establishment | Not estimated separately; place counts by category and place attributes are measured |

Overture categories used for the facility types (README): fire = `fire_department`; EMS = `ambulance_and_ems_services`; schools = `elementary_school`, `middle_school`, `high_school`, `school`, `private_school`, `public_school`. Hospitals are excluded because Overture's hospital count runs about 12 times the reference. Road values are not comparable across regions, because the Overture/TIGER highway ratio ranges from 0.71 to 1.59 between regions.

**What happens when one half of `poi_gap` is undefined** is not stated. We assume the defined half is used alone (assumed).

## 3.1 What the leaderboard tells us about the target

For a constant prediction $c$, the leaderboard RMSE satisfies $\text{RMSE}^2 = \text{sd}^2 + (\text{mean}-c)^2$. Two of our submissions, all zeros (RMSE 0.10725) and all 0.05 (RMSE 0.08956), give a public-split **mean of about 0.060 and a standard deviation of about 0.089**. A symmetric distribution with that mean and spread would need negative values, so the target must be skewed: most tracts sit near 0, with a tail of large gaps. The public/private split is unknown, and we assume it is random.

# 4. The submitted method (v5)

## 4.1 Formula

$$\widehat{\text{gap}} = 0.035 + 0.07\,(1-\text{pct\_urban}) + 0.04\,\mathbf{1}[\text{tribal\_any}]$$

* `pct_urban` is the Census share of the tract's population living in urban areas (0–1). `tribal_any` is the strata flag for overlap with any legal or statistical tribal area. It is set when the overlap is at least 1% of the tract (the smallest flagged overlap is 1.0%).
* An urban non-tribal tract gets 0.035, a fully rural tract 0.105, a rural tribal tract 0.145 and an urban tribal tract 0.075. Values are rounded to 5 decimals.
* **The coefficients were hand-set, not fitted to labels.** We chose them as a rural/tribal prior, calibrated with public-leaderboard feedback. The intercept puts the mean prediction near the leaderboard-implied 0.060, and the rural and tribal increments reflect the expectation that rural and tribal tracts have larger gaps. v5 scored a public RMSE of 0.08312, against about 0.0896 for the best constant, so the rural/tribal signal is real.
* `reports/v5_method.py` regenerates the submitted file exactly (9,794 rows; maximum absolute difference 0.0).

## 4.2 Our submissions (all six)

| Submission | Public RMSE | What it taught us |
|--------------|------|-------------------------------|
| v1 component heuristic (missing eastern-wa rows) | rejected | Zindi scores 9,794 rows, eastern-wa included |
| v1b same heuristic, all regions | 0.12485 | worse than all zeros: its urban/rural direction was wrong, so it was dropped |
| v0 all zeros | 0.10725 | root mean square of the target is about 0.107 |
| v3 constant 0.05 | 0.08956 | with v0, gives target mean ≈ 0.060 and sd ≈ 0.089 |
| v4 heuristic × 0.35 | 0.10089 | still worse than a constant |
| **v5 rural/tribal prior** | **0.08312** | best; submitted method |

No other probes were submitted. The challenge allows 10 submissions per day; we used six in total.

## 4.3 Why there is no component model yet

Without labels, every mapping from an Overture measurement to a component is an assumption, and our only component-level attempt (v1b) did worse than predicting zero everywhere. The Bias Discovery report also shows that the building component is probably **circular** where Overture's footprints are themselves Microsoft ML (37% of tracts with buildings). There the benchmark should agree with Overture almost by construction, and human-mapped tracts carry 15–20% fewer footprints per home. A naive "more ML means a bigger building gap" term would therefore point the wrong way.

## 4.4 The metric

$$\text{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^{n}\big(\hat y_i - y_i\big)^2}$$

Here $y_i$ is the organisers' score for tract $i$, $\hat y_i$ our prediction, and $n$ the number of tracts in the leaderboard split. Lower is better, and each tract counts equally regardless of population.

# 5. Edge cases

| Case | Count | Handling and rationale |
|----------------------|-------|------------------------------------------------|
| **Zero-population tracts** (special-use 98xx tracts such as parks and airports, plus 2 water tracts) | 27 | No `pct_urban`. We impute the mean over scored tracts (0.800), giving 0.04899. *Rationale:* with no residents there is no rural population share; the mean keeps these tracts at the typical level rather than at an extreme. A region-median fill (0.97–1.00) would give 0.035–0.037, a change of at most 0.014 on 27 rows. Examples: `04005980100`, `04013216858`, `48201324102`. |
| **Water-dominated tracts (99xx)** | 2 | `48039990000`, `48057990000`: zero land area and no Overture buildings, places or major roads. The README says tracts with no reference data are dropped, so at least one component must be defined here (probably a highway on a bridge or causeway; inferred). Predicted with the zero-population fill; excluded from all per-resident and per-area statistics. |
| Populated tract with no Overture buildings or places | 0 | Checked: every populated tract has at least one of each. |
| Tracts with no Overture buildings / places | 2 / 2 | The two water tracts. Source shares are undefined (NaN); excluded from source statistics, never imputed. |
| Zero housing units | 82 | Buildings per home undefined (NaN); excluded from those ratios. |
| No Overture major road | 137 | `km_major = 0`. This could mean "no highway" (component undefined) or "highway missing" (gap = 1); we cannot tell which, so roads carry no weight in v5. |
| `eastern-wa` rows | 415 | Added to the bucket on 2026-09-08 and scored by Zindi. Our first submission omitted them and was rejected; every later submission includes them. |
| Cross-state tracts | 3 | `35023970000` (New Mexico, in maricopa-az); `40013795900` and `40085094200` (Oklahoma, eastern-ok only). Treated as ordinary members, as the README specifies. |
| Missing SVI / CVI | 88 / 2 | 61 of the 88 are populated. Excluded from both sides of SVI or CVI strata comparisons and from regression rows (9,706 complete). Not used by v5. |
| Sliver tribal overlaps | 61 | These tracts carry an `aiannh_name` but overlap it by under 1% (e.g. `53041972000`, Yakama Nation, 0.13%), so `tribal_any = False` as shipped. We follow the flag and never use such tracts as reservation examples. |
| Region boundary | all | Every tract has `frac_inside_aoi` = 1.0, so no clipping correction is needed. |

# 6. From measurements to component estimates (framework, not submitted)

We measured per tract, from Overture only: source shares of buildings and places; attribute completeness (class, name, floors, address, website); buildings per housing unit; places per 1,000 residents; and km of major road. As illustrative *stand-ins* for the three components, `weightings.py` computes the following. They are **not** estimates of the official components and were never validated.

* Building stand-in: $\operatorname{clip}\big(1 - \tfrac{\text{buildings per home}}{\text{median in same region} \times \text{density quintile}}, 0, 1\big)$; undefined if the tract has 0 homes.
* Places stand-in: the same with places per 1,000 residents; undefined if 0 residents.
* Transport stand-in: the same with major-road km per km² (median over tracts with roads); undefined if 0 km of major road.

Because they compare each tract only with tracts of similar density in its own region, these stand-ins remove rurality by construction. That is a design choice a real model would have to make deliberately. Only 1.8% of tracts have an undefined stand-in, against the 21–55% the challenge reports for the official components, so the "undefined" rule matters far more for the real score than for this illustration.

# 7. Alternative weightings

**(a) Tract- vs population-weighting of stratum ratios** (stratum mean ÷ rest mean; `alt_weighting.csv`):

| Stratum | v5, tract-wt | v5, pop-wt | non-OSM share, tract-wt | non-OSM share, pop-wt |
|---|---|---|---|---|
| Rural | 2.80 | 2.79 | 2.09 | 2.08 |
| Tribal (any overlap) | 2.33 | 2.39 | 2.03 | 2.11 |
| High SVI | 0.91 | 0.94 | 1.18 | 1.21 |
| High CVI | 1.07 | 1.08 | 1.49 | 1.55 |
| Winter drought | 0.86 | 0.86 | 0.62 | 0.62 |
| Wildfire hazard | 1.63 | 1.60 | 1.25 | 1.23 |
| Summer heat | 0.77 | 0.80 | 1.22 | 1.33 |
| Hazard + high SVI | 0.97 | 0.99 | 1.10 | 1.15 |

Switching from tract to population weighting moves each ratio by at most 0.11, so conclusions do not depend on it. What is measured matters far more: v5 has no social-vulnerability gradient by construction (SVI ratio 0.91), while the measured source mix does (1.18).

**(b) Ways of combining components**, applied to the stand-ins of section 6 (tract-weighted stratum ratios; `composite_weightings.csv`):

| Stratum | A. mean of defined (official) | B. undefined = 0 | C. worst component | D. buildings ×2 |
|---|---|---|---|---|
| Rural | 0.82 | 0.81 | 0.84 | 0.73 |
| Tribal (any overlap) | 0.89 | 0.88 | 0.86 | 0.85 |
| High SVI | 0.83 | 0.83 | 0.86 | 0.89 |
| High CVI | 0.86 | 0.86 | 0.87 | 0.86 |
| Winter drought | 1.04 | 1.04 | 1.04 | 1.00 |
| Wildfire hazard | 0.99 | 0.98 | 0.96 | 0.91 |
| Summer heat | 1.08 | 1.09 | 1.08 | 1.14 |
| Hazard + high SVI | 0.88 | 0.88 | 0.90 | 0.94 |

*A* is the official rule. *B* treats "nothing to compare" as "fully mapped"; with the official undefined rates (up to 55%) it would push scores down most in highway-free rural tracts, understating rural gaps. *C* emphasises single failures, such as a missing fire station, which suits an emergency-response reading. *D* weights buildings 0.5 and roads and places 0.25 each, renormalised over defined components; buildings matter most for heat and fire exposure counts. On these stand-ins the choice of rule moves ratios by up to 0.11 (rural: 0.73–0.84). We kept the official rule A because it is what the leaderboard scores.

# 8. Reproducibility

**Environment.** Python 3.12 with the pinned packages in `reports/requirements.txt` (pandas 3.0.6, numpy 2.5.4, geopandas 1.2.0, pyarrow 26.0.0, shapely 2.2.0, pyproj 3.8.0, scipy 1.18.1, matplotlib 3.11.2). No credentials, GPU or DuckDB are needed.

**One command.** From the project root: `bash reports/get_data.sh` (downloads the 35 inputs and verifies their SHA-256 checksums), `pip install -r reports/requirements.txt`, then `bash reports/run_all.sh`. The whole run takes about 6 minutes on one CPU, with no step over about 70 s. Results are deterministic: there is no model training, and all bootstraps use seed 20261014.

| Order | Script (in `reports/`) | Output | What it does |
|----|--------------------|--------------------|------------------------------|
| 1, per region | `poi_counts.py`, `road_km.py`, `poi_attrs.py`, `poi_source_address.py`, `bld_lineage.py --tract` | `cache/<region>-*` | per-tract place counts, road km, place attributes and sources; building sources, vintage and attributes |
| 2 | `build_master.py` | `cache/master.parquet` | joins everything (9,794 × 255); **drops USFS/CarbonPlan count columns** |
| 3 | `v5_method.py` | `cache/v5_reproduced.csv` | the submitted scores (must run before step 4) |
| 4 | `analysis.py` | `tables/*.csv`, `results.json`, `report_numbers.csv` | every table and number cited in both reports |
| 5 | `weightings.py` | `tables/alt_weighting.csv`, `composite_weightings.csv` | section 7 |
| 6 | `area_floor.py northern-ca` | `tables/footprint_area_*.csv` | 10 m² ML-footprint floor evidence |
| 7 | `figures.py`, `maps.py` | `fig/*.png` | all figures |

**Assignment rules.** Each building goes to the tract containing the centre of its bounding box. Each place goes to the tract containing its point. Road length is the exact length of each road segment inside each tract, measured in the equal-area projection EPSG:5070. Shared code and definitions (strata, border counties, clustered standard errors, bootstraps) live in one file, `reports/common.py`, so both reports use identical definitions.

# 9. Limitations

* **No labels.** Component accuracy cannot be assessed. The only performance evidence is public RMSE from six submissions on an unknown split.
* **Hand-set coefficients.** v5 is a transparent prior, not an estimated model, and may not hold on the private split.
* **Assumed component form.** The $1-\min(1, O/R)$ form is stated only for the facilities half; we assume it elsewhere.
* **Places reflect commerce as well as mapping**, which affects the establishments half of `poi_gap` and our places-per-resident measures.
* **Mixed vintages.** ACS is 2020–24, Overture 2026-08, SVI 2022, and CVI uses 2010 tracts crosswalked to 2020. Fast-changing tracts (burned or newly built) are the least reliable.
