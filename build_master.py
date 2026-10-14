"""Stage 2: assemble one tract table (all 5 regions, 9,794 scored tracts) from provided data only.
Inputs: data/<region>/ (challenge files) + reports/cache/<region>-{bldtract,poi,poi2,poisrc,road}.parquet from stage 1.
Output: reports/cache/master.parquet

Data-audit rule: the strata tables ship some USFS Wildfire-Risk and CarbonPlan columns that count buildings, housing
units or people. Those counts are plausibly derived from Microsoft building footprints (a removed reference layer), so
they are DROPPED HERE, at build time, and never reach any analysis. Only the hazard rasters we use (USFS WHP etc.) stay."""
import warnings, pandas as pd, numpy as np
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
R = ["eastern-ok", "eastern-wa", "maricopa-az", "northern-ca", "south-central-tx"]
SRC = {"Microsoft ML Buildings": "ms", "OpenStreetMap": "osm", "Esri Community Maps": "esri", "Google Open Buildings": "gob"}
KEEP_USFS = {"usfs_WHP_mean", "usfs_BP_mean", "usfs_CFL_mean", "usfs_FLEP4_mean", "usfs_FLEP8_mean", "usfs_covered", "usfs_edition"}
def drop_proxies(st):
    bad = [c for c in st.columns if (c.startswith("usfs_") and c not in KEEP_USFS) or c.startswith("carbonplan_")]
    return st.drop(columns=bad), bad
out = []
for r in R:
    s = pd.read_csv(f"data/{r}/{r}-sample-submission.csv", dtype={"GEOID": str})[["GEOID"]]
    st, dropped = drop_proxies(pd.read_parquet(f"data/{r}/{r}-strata-tract-table.parquet"))
    hu = pd.read_parquet(f"data/{r}/{r}-census-acs-housing.parquet", columns=["GEOID", "housing_units"])
    tr = pd.read_parquet(f"data/{r}/{r}-census-tracts.parquet", columns=["GEOID", "NAMELSAD"])
    T = pd.read_parquet(f"reports/cache/{r}-bldtract.parquet")
    T["s"] = T.src.map(SRC).fillna("other")
    b = T.pivot_table(index="GEOID", columns="s", values="n", aggfunc="sum", fill_value=0).add_prefix("b_")
    b["n_bld"] = b.sum(axis=1)
    g = T.groupby("GEOID").agg(attr=("attr", "sum"), sem=("sem", "sum"), yr_sum=("yr_sum", "sum"), new=("new", "sum"), n=("n", "sum"))
    b["bld_attr_share"] = g.attr/g.n; b["bld_sem_share"] = g["sem"]/g.n; b["bld_mean_year"] = g.yr_sum/g.n; b["bld_new_share"] = g.new/g.n
    poi = pd.read_parquet(f"reports/cache/{r}-poi.parquet"); poi2 = pd.read_parquet(f"reports/cache/{r}-poi2.parquet")
    rd = pd.read_parquet(f"reports/cache/{r}-road.parquet")
    ps = pd.read_parquet(f"reports/cache/{r}-poisrc.parquet"); ps["meta"] = ps.src.eq("meta")
    pa = ps.assign(n_meta=ps.n*ps.meta, addr_meta=ps.n_addr*ps.meta, n_other=ps.n*~ps.meta, addr_other=ps.n_addr*~ps.meta, n_addr_all=ps.n_addr) \
           .groupby("GEOID")[["n_meta", "addr_meta", "n_other", "addr_other", "n_addr_all"]].sum().reset_index()
    m = (s.merge(tr, on="GEOID", how="left").merge(st, on="GEOID", how="left").merge(hu, on="GEOID", how="left")
          .merge(b.reset_index(), on="GEOID", how="left").merge(poi, on="GEOID", how="left")
          .merge(poi2, on="GEOID", how="left").merge(rd, on="GEOID", how="left").merge(pa, on="GEOID", how="left"))
    m["region"] = r; out.append(m)
M = pd.concat(out, ignore_index=True)
for c in [c for c in M if c.startswith(("b_", "psrc_"))]+["n_bld", "n_poi", "n_fire", "n_ems", "n_school", "km_major", "km_minor", "km_tert",
          "n_meta", "addr_meta", "n_other", "addr_other", "n_addr_all"]:
    M[c] = M[c].fillna(0)
for k in ["ms", "osm", "esri", "gob"]: M[f"sh_{k}"] = M[f"b_{k}"]/M.n_bld.replace(0, np.nan)
M["km2"] = M.ALAND/1e6
M["bld_per_hu"] = M.n_bld/M.housing_units.replace(0, np.nan)
M["poi_per_1k"] = 1000*M.n_poi/M.pop_total.replace(0, np.nan)
M["poi_per_hu"] = M.n_poi/M.housing_units.replace(0, np.nan)
ps = [c for c in M if c.startswith("psrc_")]
M["poi_meta_share"] = M.psrc_meta/M[ps].sum(axis=1).replace(0, np.nan)
M["major_km_per_1k"] = 1000*M.km_major/M.pop_total.replace(0, np.nan)
M["minor_km_per_hu"] = M.km_minor/M.housing_units.replace(0, np.nan)
assert not [c for c in M if c.startswith("carbonplan_") or c in ("usfs_BuildingCount_sum", "usfs_HUCount_sum")]
M = M.copy(); M.to_parquet("reports/cache/master.parquet")
print(M.shape, M.groupby("region").size().to_dict()); print("dropped at build time:", dropped)
