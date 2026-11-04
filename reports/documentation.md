---
title: "Estimating Coverage Gaps without Labels: Method Documentation"
subtitle: "Bias Bounty Mapping Equity Challenge · Entry for the Best Documentation prize"
date: "Zindi username **OlsOls4** · November 2026"
geometry: margin=2cm
fontsize: 10pt
header-includes:
  - \usepackage{needspace}
  - \setlength{\abovedisplayskip}{4pt}
  - \setlength{\belowdisplayskip}{4pt}
---

| | |
|:----------------|:---------------------------------------------------------------|
| **Zindi username** | **OlsOls4** |
| **Submission this writeup documents** | **`S9ekqtTA`** (file `v5_rural.csv`), public RMSE **0.08312** (best of our five scored submissions; all are listed in section 2) |
| **Code** | <https://github.com/OlsOls4/bias-bounty-mapping-equity>, release tag `v1.0` |
| **Reproduce** | `git clone --branch v1.0 https://github.com/OlsOls4/bias-bounty-mapping-equity`, then `cd bias-bounty-mapping-equity`, `pip install -r reports/requirements.txt`, `bash reports/get_data.sh` (fetches the 35 public input files and checks their SHA-256), `bash reports/run_all.sh` (about 6 min on one CPU). For the submission alone: `python reports/v5_method.py` (all commands from the repository root) |
| **Check** | `v5_method.py` writes `cache/v5_reproduced.csv`, which is byte-identical to the submitted file: 9,794 rows, SHA-256 `b39ce63b5cc95da9ad3df9ddc74e97e9`\newline`ed3378b827a4284ac273f21ee4568d58` (verified 30 Oct 2026) |
| **Data used for the scored submission** | Only challenge-provided files. No removed reference layer (TIGER roads, Microsoft Building Footprints, HIFLD/USGS facilities, County Business Patterns) or any copy of one was downloaded or used, anywhere in this work |

# 1. Summary in plain language

**The task.** For each of 9,794 US census tracts, predict a *coverage-gap score* between 0 (Overture Maps has everything) and 1 (Overture has nothing). The organisers computed the true scores by comparing Overture with authoritative reference maps of roads, buildings and facilities. Those reference maps were then removed from the data, and using them, or copies of them, is forbidden. No true scores were released.

**What this means.** None of the three parts of the score (roads, buildings, places) can be computed: each one is "Overture's count divided by the reference count", and the reference half is gone. So we did the following instead:

1. **We measured what *can* be measured.** For every tract we counted Overture's roads, buildings and places, and recorded where each came from (OpenStreetMap volunteers, Microsoft's or Google's machine-learning, Meta, and so on). Section 4 sets these measurements against each official part of the score.
2. **We submitted a simple, transparent rule.** Every tract scores 0.035, plus up to 0.07 depending on how rural its residents are, plus 0.04 if it overlaps tribal land. We chose the three numbers by reasoning, then checked them against the leaderboard. They were never fitted to true scores, because there are none.
3. **We tested how sensitive the result is.** The leaderboard reports one error number per submission. With a little algebra (section 7.1), the error numbers of submissions already made tell us the error a *different* rule would get, without submitting it. That shows the rule sits within 0.0003 RMSE of the best rescaling the evidence allows.
4. **We documented every awkward case**: tracts with no residents, tracts that are mostly water, and tracts where Overture has no data (section 6).

Practitioners who want the flagged tracts rather than the model should use the Bias Discovery report and its tract list.

**Terms used throughout.** *Tract*: a census tract, keyed by its 11-digit `GEOID`. *Component*: one of the three official parts of the score (`transport_gap`, `building_gap`, `poi_gap`). *Reference layer*: the removed authoritative map a component compares Overture with. *Defined / undefined*: a component is undefined in a tract that has nothing in the reference to compare against; it is then left out of that tract's score. *Proxy*: something we measured from Overture alone that relates to a component (for example km of major road). *Stand-in*: an illustrative per-tract number built from a proxy (section 7.3); not an estimate of the official component. *Source* (or lineage): the upstream dataset that supplied an Overture feature. *RMSE*: root mean squared error, the leaderboard metric (section 5.3). *Public leaderboard*: the RMSE Zindi shows on about 30% of tracts; the other 70% (private) decide the final ranking. *Probe*: a submission made to learn something about the hidden scores, not to win. *Stratum*: a group of tracts (for example rural, high SVI). *SVI*: CDC Social Vulnerability Index percentile (0–1).

# 2. All leaderboard submissions

All were made on 13 Oct 2026, in this order. Zindi allows 10 per day and 300 in total. *Columns*: "all 5" = `GEOID`, the three optional component columns and `coverage_gap_score`; "2" = `GEOID` and `coverage_gap_score` only.

| # | Zindi ID | File | Columns | Public RMSE | What it tested |
|--|---------|-------------------------------|---------|-------|------------------------------------|
| 1 | `Y8oU6S3Z` | `v1_heuristic.csv` | all 5 | rejected | omitted the 415 `eastern-wa` tracts; Zindi requires all 9,794 rows |
| 2 | `qsJXKWh8` | `v1b_heuristic_withWA.csv` | all 5 | 0.12485 | a hand-built component heuristic (see note) |
| 3 | `aJGQu4SY` | `v0_zeros_all.csv` | all 5, all 0 | 0.10725 | probe: RMSE of all-zeros = the root mean square of the true scores |
| 4 | `sVEQQUor` | `v3_const005.csv` | 2 | 0.08956 | probe: with #3, gives the mean (0.060) and spread (0.089) of true scores |
| 5 | `j1ChXUdz` | `v4_heur_x035.csv` | all 5 | 0.10089 | #2 multiplied by 0.35 |
| **6** | **`S9ekqtTA`** | **`v5_rural.csv`** | **2** | **0.08312** | **rural/tribal rule; the submission this writeup documents** |

**Note on files with component columns (found while writing this report).** The challenge lets a submission include the three components as optional extra columns. Submissions #3, #5 and #2 are the same file multiplied by 0, 0.35 and 1. Squared error is a parabola in that multiplier, so their three RMSEs reveal the public mean of the squared predictions *in whichever column was scored*. That value is 0.0121. It matches the `transport_gap` column of #2 (0.0122; a random 30% sample gives 0.0106–0.0140) and none of the others (`coverage_gap_score` 0.0399; `building_gap` 0.0185; `poi_gap` 0.159; table `lb_scored_column_check.csv`). **We therefore infer that, for #2 and #5, the leaderboard scored the first prediction column (`transport_gap`), not the coverage-gap score.** Two consequences follow:

* the v1b heuristic as a composite was never actually tested; the 0.12485 belongs to its road rule;
* the probes #3, #4 and #6 are unaffected, because #3 is zero in every column and #4 and #6 contain only `coverage_gap_score`. Our selected submission therefore contains no optional columns.

The Evaluation page says scores are computed against the coverage-gap score, and we follow that reading. If Zindi instead matched *both* files by column position, every number in sections 4.1 and 7.1 would describe the road component instead. Our data cannot rule this out.

# 3. Data sources

| Source | Version | Used for |
|----------------------------------|------------------------|----------------------------------|
| Overture Maps buildings, places, roads (challenge extracts) | release 2026-08-19.0 | source, attributes, counts, road km |
| Census ACS housing units (table B25001) | 2020–2024 5-year | homes per tract |
| Census tract polygons and attributes (shipped by the challenge) | 2020 census (DHC); TIGER 2025 boundaries | tract shape, land area `ALAND`, `pct_urban`, `ur_class` |
| Strata table: CDC SVI | 2022 | strata only |
| Strata table: Climate Vulnerability Index | 2010 tracts, crosswalked to 2020 | strata only |
| Strata table: tribal overlap (`tribal_any`, `tribal_legal`) | TIGER 2025 | v5 input and strata |
| Strata table: drought (USDM), heat (EPHT), wildfire (USFS WRC 2nd ed., 2024), fire history (MTBS, NIFC, FPA FOD), weather stations (GHCN) | 2015–2023 seasonal indices; fire records to 2023–2025 | strata only |
| Scored tract list (`<region>-sample-submission.csv`) | as shipped | the 9,794 rows we predict |
| Public-leaderboard RMSE of our own submissions | 13 Oct 2026 | calibration and sensitivity (sections 4.1, 7.1) |
| Challenge pages <https://zindi.world/competitions/bias-bounty-mapping-equity-challenge> and bucket `README.md` | retrieved 14 and 30 Oct 2026 | component definitions |
| Overture Buildings Guide <https://docs.overturemaps.org/guides/buildings/> | retrieved 14 Oct 2026 | interpretation only |

**Files read** (7 per region × 5 regions = 35), for each region `<r>`:

```
reference/<r>/<r>-overture-buildings.parquet     reference/<r>/<r>-census-acs-housing.parquet
reference/<r>/<r>-overture-pois.parquet          reference/<r>/<r>-sample-submission.csv
reference/<r>/<r>-overture-roads.parquet         strata/<r>/<r>-strata-tract-table.parquet
                                                 strata/<r>/<r>-census-tracts.parquet
```

They come from the public Source Cooperative bucket `humane-intelligence/bias-bounty-mapping-equity-challenge`. `get_data.sh` fetches them with the AWS CLI, or with plain `curl` from `https://data.source.coop/...` if the CLI is absent, and checks them against `DATA_SHA256SUMS.txt`.

**Excluded columns.** The strata table carries USFS Wildfire-Risk and CarbonPlan columns that count buildings, homes or people (for example `usfs_BuildingCount_sum`, `carbonplan_buildings`). These may derive from Microsoft footprints, the removed building reference. `build_master.py` therefore **drops all 26 of them** at build time. Hazard measures such as `usfs_WHP_mean` are kept.

# 4. How each component is defined, and what we computed for it

The organisers' score is **the mean of the components defined for the tract** (divisor 1, 2 or 3). A tract with no defined component is dropped from the scored list. Undefined components are common: at least one is undefined in 21% of eastern Oklahoma tracts, 37% of northern California, 28% of south-central Texas and 55% of Maricopa (challenge Evaluation page). Write $O$ for Overture's quantity and $R$ for the reference quantity. The README states the form $g = 1-\min(1, O/R)$ for each facility type; **we assume the same form for the other comparisons**, which the challenge only says "compare".

$$\texttt{transport\_gap} = 1-\min\Big(1,\ \frac{\text{Overture km of motorway, trunk, primary, secondary}}{\text{TIGER km of S1100 + S1200}}\Big)$$
$$\texttt{building\_gap} = 1-\min\Big(1,\ \frac{\text{Overture building count}}{\text{Microsoft footprint count}}\Big)$$
$$\texttt{poi\_gap} = \tfrac12\Big[\operatorname*{mean}_{t\,\in\,\{\text{fire, EMS, school}\}}\Big(1-\min\big(1, \tfrac{O_t}{R_t}\big)\Big) + \Big(1-\min\big(1, \tfrac{\text{all Overture places}}{\text{CBP establishments}}\big)\Big)\Big]$$

For each component, the table below gives the official definition, why it cannot be computed, the proxies we did compute per tract, and how the submitted score relates to it. The proxy numbers are medians over the 9,767 populated tracts (rural / urban medians in brackets). "Spearman" is the rank correlation with the submitted v5 score. All values come from `component_table.py` (`tables/component_proxies.csv`, `tables/no_overture_counts.csv`).

\needspace{12\baselineskip}

| | `transport_gap` (roads) | `building_gap` (buildings) | `poi_gap` (places) |
|:------------|:-----------------------|:-----------------------|:-----------------------|
| **Official definition** | Overture named-highway km vs TIGER S1100+S1200 km. Undefined if the tract has no TIGER named highway | Overture building count vs Microsoft US Building Footprints count. ACS homes are a sanity check, not in the ratio. Undefined if no Microsoft footprint | Half: fire stations, EMS and schools vs USGS National Map (HIFLD) counts, per type. Half: all places vs CBP establishments. Undefined if no facility *and* no establishment |
| **Why we cannot compute it** | TIGER roads removed (prohibited) | Microsoft footprints removed (prohibited) | Facility and CBP layers removed (prohibited) |
| **Numerator we computed** (exactly as defined) | `km_major` = 7.9 km (rural 44.0 / urban 6.2); 0 in 137 tracts | `n_bld` = 1,726 (2,997 / 1,536); 0 in 2 tracts | `n_poi` = 142 (115 / 151); fire 0 in 6,912 tracts, EMS 0 in 9,078, schools 0 in 2,100 |
| **Other proxies computed** | km by class (`km_motorway`, `km_trunk`, `km_primary`, `km_secondary`, tertiary, minor); major km per km² of land = 1.41 (0.18 / 1.90) | source shares: OSM 0.73 (0.11 / 0.83), Microsoft ML 0.17 (0.88 / 0.10), Google ML present in 289 tracts; buildings per home 1.07 (2.03 / 0.98) | places per 1,000 residents 36.4 (36.8 / 36.3); share of places with an address 0.973 (0.929 / 0.977); place sources (Meta, Foursquare, ...) |
| **Spearman with v5** | `km_major` +0.53; per km² $-0.70$ | Microsoft share +0.49; OSM share $-0.48$ | addressed share $-0.48$; places per 1,000 $-0.01$ |
| **Expected sign if used** | unknown: Overture/TIGER ratio is 0.71–1.59 between regions | probably *reversed*: where Overture's footprints are Microsoft's, the benchmark agrees almost by construction (Bias Discovery §6) | fewer facilities / places per resident $\rightarrow$ larger gap (plausible, unverified) |
| **In the submitted file?** | no column | no column | no column |

**What we submitted.** The submitted file `v5_rural.csv` has exactly two columns, `GEOID` and `coverage_gap_score`; **no component columns were submitted.** v5 predicts the aggregate score directly. It uses none of the proxies above, only two strata columns (`pct_urban`, `tribal_any`). Its implicit treatment of undefined components is to ignore them: it predicts the same kind of number whether the tract's score averages one component or three. The proxies feed the Bias Discovery analysis and the illustrative stand-ins of section 7.3.

**Why no component model.** Each proxy-to-component mapping needs the reference denominator, which only the removed layers hold. Our one component heuristic (v1b) could not be evaluated as a composite (section 2 note). The building proxy also points the wrong way where Overture *is* Microsoft (37% of tracts): there, human-mapped tracts carry 15–20% fewer footprints per home. **If labels existed**, we would fit each component separately on its defined tracts (with the 0/1 `_defined` flags as a second target), cross-validated by county, and compare against v5.

## 4.1 What the leaderboard tells us about the target

For a constant prediction $c$, $\text{RMSE}^2 = \text{sd}^2 + (\text{mean} - c)^2$. Submissions #3 (all zeros, 0.10725) and #4 (all 0.05, 0.08956) give a public-split **mean of 0.0598 and standard deviation of 0.0890**. A symmetric distribution with that mean and spread would need negative scores, so the scores must be skewed: most tracts near 0, with a tail of large gaps. The best possible constant (0.0598) would score 0.08902.

# 5. The submitted method (v5, `S9ekqtTA`)

## 5.1 Formula and computation steps

$$\widehat{\text{gap}} = 0.035 + 0.07\,(1-\texttt{pct\_urban}) + 0.04\,\mathbf{1}[\texttt{tribal\_any}]$$

`v5_method.py` does the following:

1. Read each region's `sample-submission.csv` with `GEOID` **as text**, in the order eastern-ok, maricopa-az, northern-ca, south-central-tx, eastern-wa.
2. Left-join `pct_urban` (Census share of residents in urban areas, 0–1) and `tribal_any` (strata flag, true when the tract overlaps any legal or statistical tribal area by at least 1%) from `strata-tract-table.parquet`.
3. Where `pct_urban` is missing (the 27 zero-population tracts), fill it with its mean over all 9,794 scored tracts (0.8002), which gives a score of 0.04899.
4. Compute the formula and round to 5 decimals.
5. Write `GEOID,coverage_gap_score`, compare with the submitted file and print the SHA-256.

Scores take only four main values: urban non-tribal 0.035, urban tribal 0.075, fully rural 0.105, rural tribal 0.145. Partly urban tracts sit in between.

## 5.2 Why these numbers

* **Intercept 0.035.** It is low because most tracts score near 0. Together with the increments it puts the mean prediction (0.0526) near the leaderboard-implied mean (0.0598).
* **Rural +0.07 and tribal +0.04.** These encode the expectation, set before seeing any score, that rural and tribal tracts are less well mapped.
* **Result.** Public RMSE 0.08312, against 0.08902 for the best possible constant. Section 7.1 shows that the intercept and the overall size of the increments are near their best values.
* **What we did not do.** We did not tune further on the public split. The best gain the probe maths allows is 0.0003 (section 7.1), smaller than the plausible difference between the 30% public and 70% private splits.

## 5.3 The metric

$$\text{RMSE} = \sqrt{\tfrac{1}{n}\textstyle\sum_{i=1}^{n}(\hat y_i - y_i)^2}$$

Here $y_i$ is the organisers' score for tract $i$, $\hat y_i$ our prediction, and $n$ the number of tracts in the split. Lower is better, and every tract counts equally regardless of population.

\needspace{22\baselineskip}

# 6. Edge cases

Each row gives the count over the 9,794 scored tracts (`water_tracts.py`, `component_table.py`, `analysis.py`).


| Case | Count | How we handled it, and why |
|--------------------|----------|--------------------------------------------------------|
| **Zero-population tracts** | 27 | 17 special-use `98xx` tracts (parks, airports and similar), 2 water `99xx` tracts and 8 ordinarily coded tracts with no residents (14 in south-central-tx, 11 in maricopa-az, 1 each in eastern-ok and eastern-wa). With no residents there is no `pct_urban`, so we impute its mean (0.800), giving 0.04899: a typical value rather than an extreme. A region-median fill (0.97–1.00) would give 0.035–0.037, a change of at most 0.014 on 27 rows. They are excluded from every per-resident and per-home measure (denominator 0). Examples: `04005980100`, `04013216858`, `48201324102` |
| **Water-dominated tracts** | 43 (>50%) | The tract files carry land area `ALAND` but no water area. We compute water share = 1 $-$ `ALAND` ÷ polygon area (polygon measured in equal-area EPSG:5070; `water_tracts.py`). 171 tracts are >25% water, 43 >50% (40 in south-central-tx, 2 northern-ca, 1 eastern-ok; 136,310 residents), 3 >90%. The most extreme populated tracts are `48061012305` (93%, Cameron Co., TX), `48355006205` (87%, Nueces), `48007950200` (87%, Aransas) and `06033000502` (76%, Lake Co., CA). **v5 does nothing special for them**: they are scored on `pct_urban` and `tribal_any` like any tract (mean 0.0475). **Every per-area measure uses land area** (`km2` = `ALAND` / 1,000,000), so open water never dilutes a density. Only the 2 fully water tracts lack Overture data (next rows); the other 41 all have buildings and places, and 6 of them have no major road |
| **Fully water tracts (`99xx`)** | 2 | `48039990000`, `48057990000`: zero land, zero residents, and no Overture buildings, places or roads. The README drops tracts with no reference data (7 such `99xx` tracts in Texas), so these 2 must have at least one defined component (probably a bridge or causeway highway; inferred). Predicted with the zero-population fill |
| **Tracts with no Overture data, by layer** | 2 (all layers) | Buildings: 2 tracts. Places: 2. Roads of any class: 2. All three empty: the same 2 water tracts. Major roads (motorway–secondary): 137 (130 populated). Fire-department places: 6,912; EMS: 9,078; schools: 2,100; none of the three: 1,612. **Handling**: source shares are left undefined (NaN) and excluded, never imputed. A zero major-road count could mean "no highway" (component undefined) or "highway missing" (gap = 1). We cannot tell which, so roads carry no weight in v5 |
| Zero housing units | 82 | Buildings per home undefined; excluded from that ratio and from the building stand-in |
| `eastern-wa` | 415 | Added to the bucket on 8 Sep 2026 (the challenge page still describes four regions). Zindi scores it: our first submission without it was rejected, and every later one includes it |
| `GEOID` as text | all | Read with `dtype={"GEOID": str}` everywhere. Arizona's state code is `04`, and reading GEOID as a number drops the leading zero and breaks joins |
| Cross-state tracts | 3 | `35023970000` (New Mexico, in maricopa-az); `40013795900` and `40085094200` (Oklahoma, eastern-ok only). Treated as ordinary members, as the README specifies |
| Missing SVI / CVI | 88 / 2 | 61 of the 88 are populated. Excluded from both sides of SVI or CVI comparisons and from regressions (9,706 complete rows). Not used by v5 |
| Sliver tribal overlaps | 61 | `aiannh_name` is set but the overlap is below 1% (e.g. `53041972000`, Yakama Nation, 0.13%), so `tribal_any = False` as shipped. We follow the flag |
| Region edge | all | `frac_inside_aoi` = 1.0 for every tract, so no clipping correction is needed |

# 7. Alternative weightings, and why we kept ours

## 7.1 Sensitivity of the v5 coefficients (leaderboard-probe maths)

**The idea in plain terms.** The leaderboard gives one number per submission: how far its predictions are from the hidden scores. Expand the squared error and each submission's number reveals one fact about the hidden scores: how strongly they line up with that submission's predictions. All zeros reveals their average square; a constant reveals their average; v5 reveals how strongly they line up with v5. Any *new* rule that is a mix of rules already submitted (a constant plus a multiple of v5) can then have its RMSE computed exactly, with no new submission. In symbols, with $y$ the hidden scores and $q$ a submitted prediction: $E[qy] = \big(E[q^2] + E[y^2] - \text{RMSE}(q)^2\big)/2$, and $\text{RMSE}(p)^2 = E[p^2] - 2E[py] + E[y^2]$.

**The one approximation.** We do not know which ~30% of tracts are public, so $E[p^2]$ is averaged over all 9,794 tracts. Repeating each calculation on 2,000 random 30% subsets moves the answers by at most $\pm 0.001$ (`band95` in `v5_sensitivity.csv`). Changing only the rural *or* only the tribal coefficient is **not** identified, because the leaderboard tells us only about their combination. For those we show the range allowed by scores lying between 0 and 1.

\needspace{14\baselineskip}

| Variant | Mean prediction | Predicted public RMSE | Reading |
|----------------------------------|-------------|--------------------|---------------------------|
| **v5 as submitted** | 0.053 | **0.08312** (check: equals the leaderboard) | |
| constant 0.035 (intercept only) | 0.035 | 0.09241 | rural/tribal terms are worth 0.009 |
| best constant 0.0598 | 0.060 | 0.08902 | |
| intercept × 0.5 (0.0175) | 0.035 | 0.08642 | worse |
| intercept × 1.5 (0.0525) | 0.070 | 0.08343 | slightly worse |
| rural + tribal increments × 0.5 | 0.044 | 0.08610 | worse |
| rural + tribal increments × 1.5 | 0.061 | 0.08384 | slightly worse |
| rural + tribal increments × 2 | 0.070 | 0.08817 | worse |
| best $a + b\cdot$v5 ($a$ = 0.0037, $b$ = 1.07) | 0.060 | 0.08278 | optimum; only 0.0003 better |
| rural coefficient × 0.5 / × 1.5 | 0.046 / 0.060 | 0.075–0.088 / 0.081–0.093 | not identified |
| tribal coefficient × 0.5 / × 1.5 / 0 | 0.051 / 0.054 / 0.049 | 0.081–0.093 / 0.073–0.086 / 0.079–0.102 | not identified |

**Why we kept the submitted weights.** The intercept and the overall strength of the rural/tribal signal sit at a minimum: halving or doubling either makes the public RMSE worse, and the best rescaling gains only 0.0003. That gain is too small to justify fitting to 30% of tracts. The split between the rural and tribal terms cannot be pinned down without new probes. The ranges show it could matter (tribal × 1.5 might reach 0.073), but they include worse outcomes too, so we kept the prior.

## 7.2 Tract- vs population-weighting

These are stratum ratios (stratum mean ÷ mean of all other tracts; `alt_weighting.csv`) for v5 and for the measured share of non-OSM buildings.

| Stratum | v5, by tract | v5, by population | non-OSM share, by tract | non-OSM share, by population |
|-----------------------|------|------|------|------|
| Rural | 2.80 | 2.79 | 2.09 | 2.08 |
| Tribal (any overlap) | 2.33 | 2.39 | 2.03 | 2.11 |
| High SVI ($\geq 0.75$) | 0.91 | 0.94 | 1.18 | 1.21 |
| High CVI (top 25%) | 1.07 | 1.08 | 1.49 | 1.55 |
| Winter drought (top 25%) | 0.86 | 0.86 | 0.62 | 0.62 |
| Wildfire hazard (top 25%) | 1.63 | 1.60 | 1.25 | 1.23 |
| Summer heat (top 25%) | 0.77 | 0.80 | 1.22 | 1.33 |
| Hazard + high SVI | 0.97 | 0.99 | 1.10 | 1.15 |

Weighting by population instead of by tract moves each ratio by at most 0.11, so conclusions do not depend on it. *What* is measured matters more: v5 has no social-vulnerability gradient by construction (SVI ratio 0.91), while the measured source mix does (1.18).

## 7.3 Ways of combining components (illustrative stand-ins)

To show how the combination rule changes results, `weightings.py` builds one stand-in per component from Overture proxies. Each compares a tract with the median of tracts in the same region and population-density quintile (median $m$):

$$s_{\text{building}} = \operatorname{clip}\Big(1 - \frac{\text{buildings per home}}{m},\,0,\,1\Big),\qquad
s_{\text{places}} = \operatorname{clip}\Big(1 - \frac{\text{places per 1,000 residents}}{m},\,0,\,1\Big),$$
$$s_{\text{roads}} = \operatorname{clip}\Big(1 - \frac{\text{major-road km per km}^2\text{ of land}}{m},\,0,\,1\Big)$$

They are undefined, respectively, with 0 homes, 0 residents or 0 km of major road. That covers 1.8% of tracts, against 21–55% for the official components. They are **not** estimates of the official components and were never validated or submitted.

| Stratum | A. mean of defined (official rule) | B. undefined counted as 0 | C. worst component | D. buildings weighted × 2 |
|-----------------------|------|------|------|------|
| Rural | 0.82 | 0.81 | 0.84 | 0.73 |
| Tribal (any overlap) | 0.89 | 0.88 | 0.86 | 0.85 |
| High SVI ($\geq 0.75$) | 0.83 | 0.83 | 0.86 | 0.89 |
| High CVI (top 25%) | 0.86 | 0.86 | 0.87 | 0.86 |
| Winter drought (top 25%) | 1.04 | 1.04 | 1.04 | 1.00 |
| Wildfire hazard (top 25%) | 0.99 | 0.98 | 0.96 | 0.91 |
| Summer heat (top 25%) | 1.08 | 1.09 | 1.08 | 1.14 |
| Hazard + high SVI | 0.88 | 0.88 | 0.90 | 0.94 |

**How to read these ratios.** Values below 1 do *not* mean rural or tribal tracts are better mapped. Each stand-in compares a tract only with tracts of similar density in its own region, which removes rurality by design. The table shows only how the combination rule moves results once density is held fixed.

* *A* is the official rule.
* *B* treats "nothing to compare" as "fully mapped". With the official undefined rates (up to 55%) it would lower scores most in rural tracts without highways.
* *C* emphasises single failures, such as a missing fire station, which suits an emergency-response reading.
* *D* weights buildings 0.5 and roads and places 0.25 each, renormalised over defined components, because buildings drive heat and fire exposure counts.

The rule moves ratios by up to 0.11 (rural: 0.73–0.84). We kept rule A because it is what the leaderboard scores.

# 8. Reproducibility

**Environment.** Python 3.12 with pinned packages (`requirements.txt`: pandas 3.0.6, numpy 2.5.4, geopandas 1.2.0, pyarrow 26.0.0, shapely 2.2.0, pyproj 3.8.0, scipy 1.18.1, matplotlib 3.11.2). No credentials, GPU, DuckDB or paid service is needed. The pipeline is deterministic: there is no model training, and every bootstrap uses seed 20261014.

**Steps.** (1) Clone at tag `v1.0`. (2) `pip install -r reports/requirements.txt`. (3) `bash reports/get_data.sh` downloads the 35 inputs and verifies their SHA-256 sums. (4) `bash reports/run_all.sh` runs these in order (about 6 minutes; no step over about 70 s; \* = once per region):

| Step | Script | Output | What it does |
|----|------------------------|----------------------------|---------------------------------|
| 1\* | `poi_counts.py`, `road_km.py`, `poi_attrs.py`, `poi_source_address.py`, `bld_lineage.py --tract` | `cache/<region>-*` | place counts, road km by class, place attributes and sources; building sources, vintage, attributes |
| 2 | `build_master.py` | `cache/master.parquet` | one table of 9,794 tracts × 255 columns; drops the 26 USFS/CarbonPlan count columns |
| 3 | `v5_method.py` | `cache/v5_reproduced.csv` | the submitted scores, byte-identical, SHA-256 printed |
| 4 | `analysis.py` | `tables/*.csv`, `report_numbers.csv` | every number in the Bias Discovery report |
| 5 | `weightings.py` | `alt_weighting.csv`, `composite_weightings.csv` | sections 7.2–7.3 |
| 6 | `component_table.py` | `component_proxies.csv`, `no_overture_counts.csv` | section 4 table and section 6 counts |
| 7 | `water_tracts.py` | `water_tracts.csv`, `water_summary.csv` | water-dominated tracts (section 6) |
| 8 | `v5_sensitivity.py` | `v5_sensitivity.csv`, `lb_scored_column_check.csv` | section 7.1 and the section 2 note |
| 9 | `area_floor.py`, `figures.py`, `maps.py` | `tables/footprint_area_*`, `fig/*.png` | figures for the Bias Discovery report |

**Assignment rules.** Each building goes to the tract containing the centre of its bounding box, and each place to the tract containing its point. Road length is the exact length of each segment inside each tract, in the equal-area projection EPSG:5070. Shared definitions (strata, border counties, statistics) live in one file, `common.py`.

# 9. Limitations

* **No labels.** Component accuracy cannot be assessed. The only performance evidence is public RMSE on an unknown 30% split.
* **Hand-set coefficients.** v5 is a transparent prior, not an estimated model, and may behave differently on the private 70%.
* **Assumed component form.** $1-\min(1, O/R)$ is stated only for the facility types; we assume it for the others.
* **Leaderboard column handling is inferred** (section 2 note). If both files were matched by column position, the probe numbers describe the road component.
* **Places reflect commerce as well as mapping**, which affects the establishments half of `poi_gap`.
* **Mixed vintages.** ACS 2020–24, Overture 2026-08, SVI 2022, CVI on 2010 tracts. Fast-changing tracts (burned or newly built) are the least reliable.
