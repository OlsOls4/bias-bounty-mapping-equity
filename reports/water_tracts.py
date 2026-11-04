"""Documentation report, edge cases: water-dominated tracts.
The challenge tract files ship ALAND (land area, m2) and the tract polygon, but no AWATER column. Water area is therefore
  water_share = 1 - ALAND / polygon area,   polygon area measured in the equal-area projection EPSG:5070,
clipped to [0, 1] (Census polygons include inland and coastal water inside the tract boundary).
Run from the project root after build_master.py and v5_method.py.
Writes reports/tables/water_tracts.csv (every scored tract with water_share >= 0.25) and
       reports/tables/water_summary.csv (counts by threshold + Overture presence)."""
import os, numpy as np, pandas as pd, geopandas as gpd
from shapely import wkb

R = ["eastern-ok", "eastern-wa", "maricopa-az", "northern-ca", "south-central-tx"]
rows = []
for r in R:
    t = pd.read_parquet(f"data/{r}/{r}-census-tracts.parquet", columns=["GEOID", "NAMELSAD", "ALAND", "geometry"])
    g = gpd.GeoDataFrame(t.drop(columns="geometry"), geometry=t.geometry.apply(wkb.loads), crs="OGC:CRS84").to_crs(5070)
    g["area_m2"] = g.area
    g["region"] = r
    rows.append(pd.DataFrame(g.drop(columns="geometry")))
T = pd.concat(rows, ignore_index=True)
sub = pd.concat([pd.read_csv(f"data/{r}/{r}-sample-submission.csv", dtype={"GEOID": str})[["GEOID"]] for r in R])
T = T[T.GEOID.isin(sub.GEOID)].copy()
T["water_share"] = (1 - T.ALAND / T.area_m2).clip(0, 1)

M = pd.read_parquet("reports/cache/master.parquet", columns=["GEOID", "pop_total", "n_bld", "n_poi", "km_major", "km_tert", "km_minor"])
v5 = pd.read_csv("reports/cache/v5_reproduced.csv", dtype={"GEOID": str})
T = T.merge(M, on="GEOID", how="left").merge(v5, on="GEOID", how="left")
T["county5"] = T.GEOID.str[:5]

out = T[T.water_share >= 0.25].sort_values("water_share", ascending=False)
out[["GEOID", "region", "NAMELSAD", "water_share", "ALAND", "area_m2", "pop_total", "n_bld", "n_poi", "km_major",
     "coverage_gap_score"]].round({"water_share": 4, "area_m2": 0}).to_csv("reports/tables/water_tracts.csv", index=False)

summ = []
for thr in [0.25, 0.5, 0.9, 0.999]:
    s = T[T.water_share > thr]
    summ.append({"threshold": f">{thr:g}", "tracts": len(s), "residents": int(s.pop_total.fillna(0).sum()),
                 "zero_population": int((s.pop_total.fillna(0) == 0).sum()), "no_overture_buildings": int((s.n_bld == 0).sum()),
                 "no_overture_places": int((s.n_poi == 0).sum()), "no_major_road": int((s.km_major == 0).sum()),
                 "mean_v5": round(s.coverage_gap_score.mean(), 5)})
S = pd.DataFrame(summ)
S.to_csv("reports/tables/water_summary.csv", index=False)
print(S.to_string(index=False))
print("by region (>50% water):", T[T.water_share > 0.5].region.value_counts().to_dict())
print(out.head(12)[["GEOID", "region", "water_share", "pop_total", "n_bld", "n_poi", "km_major", "coverage_gap_score"]].to_string(index=False))
for g in ["48061012305", "48355006205", "48007950200", "06033000502"]:
    print(g, T.loc[T.GEOID == g, ["water_share", "pop_total", "n_bld"]].round(3).values.tolist())
