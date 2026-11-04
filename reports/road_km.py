"""Stage 1b (per region): Overture road length per tract by class (km, EPSG:5070).
major = motorway/trunk/primary/secondary (the classes the challenge compares); tert = tertiary; minor = residential/unclassified.
Each road is cut by the tract polygons (spatial-index candidate pairs + exact shapely intersection), so a road crossing
tracts is split between them. Usage: python reports/road_km.py <region>  -> reports/cache/<region>-road.parquet"""
import sys, numpy as np, pandas as pd, geopandas as gpd, shapely
r = sys.argv[1]; D = f"data/{r}"
t = gpd.read_parquet(f"{D}/{r}-census-tracts.parquet")[["GEOID", "geometry"]].to_crs(5070)
GROUPS = {"major": ["motorway", "trunk", "primary", "secondary"], "tert": ["tertiary"], "minor": ["residential", "unclassified"]}
keep = sum(GROUPS.values(), [])
rd = gpd.read_parquet(f"{D}/{r}-overture-roads.parquet", columns=["class", "geometry"], filters=[("class", "in", keep)])
rd = rd.to_crs(5070).reset_index(drop=True)
TG, RG = t.geometry.values, rd.geometry.values
shapely.prepare(TG)                                   # prepared tract polygons make the predicates fast
ti, ri = shapely.STRtree(RG).query(TG, predicate="intersects")
inside = shapely.contains_properly(TG[ti], RG[ri])    # road wholly inside the tract: length = full road length
L = shapely.length(RG[ri]) / 1000
cut = np.flatnonzero(~inside)                         # roads crossing a tract edge: exact clip
L[cut] = shapely.length(shapely.intersection(RG[ri[cut]], TG[ti[cut]])) / 1000
X = pd.DataFrame({"GEOID": t.GEOID.values[ti], "class": rd["class"].values[ri], "len": L})
out = t[["GEOID"]].copy()
for name, cls in GROUPS.items():
    out = out.merge(X[X["class"].isin(cls)].groupby("GEOID")["len"].sum().rename(f"km_{name}").reset_index(), on="GEOID", how="left")
for c in GROUPS["major"]:
    out = out.merge(X[X["class"] == c].groupby("GEOID")["len"].sum().rename(f"km_{c}").reset_index(), on="GEOID", how="left")
out = out.fillna(0); out.to_parquet(f"reports/cache/{r}-road.parquet")
print(r, out.drop(columns="GEOID").sum().round(0).to_dict(), round((out.km_major == 0).mean(), 4))
