"""Documentation report, section 'Alternative weightings': how stratum disparity ratios move under
(a) tract- vs population-weighting and (b) different ways of combining components.
The official components cannot be computed (their reference layers were removed), so (b) uses three ILLUSTRATIVE
Overture-only stand-ins. They are NOT estimates of the official components and were never validated:
  building stand-in  = clip(1 - bld_per_hu / median bld_per_hu in the same region x density quintile, 0, 1); undefined if 0 housing units
  places stand-in    = clip(1 - places_per_1k / median in the same region x density quintile, 0, 1);       undefined if 0 residents
  transport stand-in = clip(1 - major-road km per km2 / median (tracts with >0 km) in region x density quintile, 0, 1);
                       undefined if the tract has 0 km of Overture major road (read as 'no highway to compare')
Run from the project root after analysis.py -> reports/tables/alt_weighting.csv, reports/tables/composite_weightings.csv"""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import *

M, P = load(); S = strata(P)
P["dq"] = P.groupby("region").log10_density.transform(lambda x: pd.qcut(x, 5, labels=False, duplicates="drop"))
def standin(val, ok):
    v = val.where(ok); med = v.groupby([P.region, P.dq]).transform("median")
    return (1 - v/med).clip(0, 1)
P["c_bld"] = standin(P.bld_per_hu, P.housing_units > 0)
P["c_poi"] = standin(P.poi_per_1k, P.pop_total > 0)
P["major_km_per_km2"] = P.km_major / P.km2.replace(0, np.nan)
P["c_tr"] = standin(P.major_km_per_km2, P.km_major > 0)
C = P[["c_tr", "c_bld", "c_poi"]]
P["A_mean_defined"] = C.mean(axis=1, skipna=True)                       # official rule
P["B_zero_fill"] = C.fillna(0).mean(axis=1)                              # undefined counted as 0 gap
P["C_max_defined"] = C.max(axis=1, skipna=True)                         # worst component
w = np.array([0.25, 0.5, 0.25]); D = C.notna().values * w
P["D_building_weighted"] = np.nansum(C.values * w, axis=1) / D.sum(axis=1)   # 0.25/0.5/0.25, renormalised over defined
v5 = pd.read_csv("reports/cache/v5_reproduced.csv", dtype={"GEOID": str}).set_index("GEOID").coverage_gap_score
P["v5"] = P.GEOID.map(v5); P["nonosm"] = 1 - P.sh_osm
rows = []
for col in ["v5", "nonosm", "A_mean_defined", "B_zero_fill", "C_max_defined", "D_building_weighted"]:
    for s in SCORECARD:
        m = S[s]; x = P[col]; ok = x.notna() & m.notna()
        i, o = ok & (m == 1), ok & (m == 0)
        rows.append({"score": col, "stratum": s, "tract_wt": x[i].mean()/x[o].mean(),
                     "pop_wt": np.average(x[i], weights=P.pop_total[i]) / np.average(x[o], weights=P.pop_total[o])})
R = pd.DataFrame(rows)
R[R.score.isin(["v5", "nonosm"])].pivot(index="stratum", columns="score", values=["tract_wt", "pop_wt"]).reindex(SCORECARD).to_csv("reports/tables/alt_weighting.csv")
R.to_csv("reports/tables/composite_weightings.csv", index=False)
und = C.isna()
print("tracts with >=1 undefined stand-in:", round(und.any(axis=1).mean(), 3), "| undefined by component:", und.mean().round(3).to_dict())
print("max |tract_wt - pop_wt| (v5, nonosm):", round((R[R.score.isin(['v5','nonosm'])].tract_wt - R[R.score.isin(['v5','nonosm'])].pop_wt).abs().max(), 3))
print(R.pivot(index="stratum", columns="score", values="tract_wt").reindex(SCORECARD).round(2).to_string())
pd.DataFrame({"key": ["standin_any_undefined", "standin_tr_undefined", "standin_bld_undefined", "standin_poi_undefined"],
              "value": [und.any(axis=1).mean(), und.c_tr.mean(), und.c_bld.mean(), und.c_poi.mean()]}).to_csv("reports/tables/weightings_numbers.csv", index=False)
