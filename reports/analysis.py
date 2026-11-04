"""Stage 3: every table and number cited in the two reports (except figures, maps, area floor and weightings, which
have their own scripts). Run from the project root after build_master.py:
    python reports/analysis.py   -> reports/tables/*.csv, reports/tables/results.json, reports/tables/report_numbers.csv

Uses ONLY: Overture 2026-08-19.0 extracts, ACS B25001 housing units, census tract polygons/attributes and strata tables
shipped by the challenge. No removed reference layer (TIGER roads, Microsoft footprints, HIFLD/USGS facilities, CBP) is
read or reconstructed; USFS/CarbonPlan building/housing count columns are dropped in build_master.py."""
import json, os, sys, itertools, numpy as np, pandas as pd
from scipy.stats import spearmanr, norm
sys.path.insert(0, os.path.dirname(__file__))
from common import *

os.makedirs("reports/tables", exist_ok=True)
M, P = load()
OUT, NUM = {}, []
def num(key, value, desc):
    v = value.item() if hasattr(value, "item") else value
    NUM.append({"key": key, "value": v, "description": desc}); return v

# ---------------------------------------------------------------- 0. counts and edge cases
num("scored_tracts", len(M), "scored tracts (all 5 sample submissions)")
num("populated_tracts", len(P), "scored tracts with population > 0")
for r in REGIONS: num(f"tracts_{r}", int((M.region == r).sum()), f"scored tracts in {r}")
num("buildings_total", int(M.n_bld.sum()), "Overture building footprints assigned to scored tracts")
num("places_total", int(M.n_poi.sum()), "Overture places assigned to scored tracts")
edge = {"zero_pop": int((M.pop_total.fillna(0) == 0).sum()), "zero_hu": int((M.housing_units.fillna(0) == 0).sum()),
        "no_buildings": int((M.n_bld == 0).sum()), "no_places": int((M.n_poi == 0).sum()),
        "no_major_road": int((M.km_major <= 0).sum()), "water_99xx": M.loc[M.GEOID.str[5:7] == "99", "GEOID"].tolist(),
        "special_98xx": int((M.GEOID.str[5:7] == "98").sum()), "svi_missing_all": int(M.svi_overall.isna().sum()),
        "svi_missing_populated": int(P.svi_overall.isna().sum()), "cvi_missing": int(M.cvi_overall.isna().sum()),
        "populated_no_places_no_buildings": int(((P.n_poi == 0) & (P.n_bld == 0)).sum()),
        "populated_no_places": int((P.n_poi == 0).sum()), "populated_no_buildings": int((P.n_bld == 0).sum()),
        "pct_urban_missing": int(M.pct_urban.isna().sum()),
        "tribal_flag_inconsistent": M.loc[M.aiannh_name.notna() & ~M.tribal_any.astype(bool), "GEOID"].tolist()}
for k, v in edge.items():
    if not isinstance(v, list): num(f"edge_{k}", v, f"edge case count: {k}")
OUT["edge"] = edge

# ---------------------------------------------------------------- 1. lineage
L = P.groupby(["region", "ur_class"]).apply(lambda d: pd.Series({
    "tracts": len(d), "buildings": d.n_bld.sum(),
    "OSM": d.b_osm.sum()/d.n_bld.sum(), "Microsoft ML": d.b_ms.sum()/d.n_bld.sum(),
    "Esri": d.b_esri.sum()/d.n_bld.sum(), "Google OB": d.b_gob.sum()/d.n_bld.sum(),
    "semantic_attr": (d.bld_sem_share*d.n_bld).sum()/d.n_bld.sum()}), include_groups=False)
L.to_csv("reports/tables/lineage_region_urban.csv"); OUT["lineage"] = L.round(4).reset_index().to_dict(orient="records")
src = pd.concat([pd.read_csv(f"reports/cache/{r}-bldsrc.csv") for r in REGIONS]); src.to_csv("reports/tables/building_source_attributes.csv", index=False)
num("ml_attr_max_pct", float(src.loc[src.src.isin(["Microsoft ML Buildings", "Google Open Buildings"]), ["cls_pct", "name_pct", "fl_pct"]].max().max()),
    "max % of ML (Microsoft/Google) footprints with class, name or floors, any region")
osm = src[src.src == "OpenStreetMap"]; num("osm_class_pct_min", float(osm.cls_pct.min()), "min % of OSM footprints with a class (by region)")
num("osm_class_pct_max", float(osm.cls_pct.max()), "max % of OSM footprints with a class (by region)")
rur = P.rural
num("rural_osm_share_tractmean", P.sh_osm[rur].mean(), "rural tracts: mean of tract OSM share")
num("nonrural_osm_share_tractmean", P.sh_osm[~rur].mean(), "non-rural tracts: mean of tract OSM share")
num("rural_osm_share_pooled", P.b_osm[rur].sum()/P.n_bld[rur].sum(), "rural: OSM footprints / all footprints (pooled)")
num("nonrural_osm_share_pooled", P.b_osm[~rur].sum()/P.n_bld[~rur].sum(), "non-rural: pooled OSM share")
sem_n = P.bld_sem_share*P.n_bld
a, b = sem_n[rur].sum()/P.n_bld[rur].sum(), sem_n[~rur].sum()/P.n_bld[~rur].sum()
num("rural_sem_pooled", a, "rural: share of footprints with class/name/floors (pooled)")
num("nonrural_sem_pooled", b, "non-rural: same (pooled)"); num("sem_pooled_ratio", b/a, "non-rural / rural semantic share (pooled)")
num("rural_sem_tractmean", P.bld_sem_share[rur].mean(), "rural: tract-mean semantic share")
num("nonrural_sem_tractmean", P.bld_sem_share[~rur].mean(), "non-rural: tract-mean semantic share")

# ---------------------------------------------------------------- 2. strata with county-cluster bootstrap
S = strata(P); cl = P.county5.values
IND = {  # name: (numerator, denominator, label)
    "osm":      (P.sh_osm.values, np.ones(len(P)), "OSM share of footprints (tract mean)"),
    "nonosm":   ((1-P.sh_osm).values, np.ones(len(P)), "non-OSM share of footprints (tract mean)"),
    "sem":      (P.bld_sem_share.values, np.ones(len(P)), "footprints with class/name/floors (tract mean)"),
    "poi1k":    (1000*P.n_poi.values.astype(float), P.pop_total.values.astype(float), "places per 1,000 residents (pooled)"),
    "addr":     (P.poi_addr.values, np.ones(len(P)), "places with street address (tract mean)"),
    "addr_pw":  (P.n_addr_all.values.astype(float), P.n_poi.values.astype(float), "places with street address (place-weighted)"),
    "noaddr":   ((1-P.poi_addr).values, np.ones(len(P)), "places without street address (tract mean)"),
    "web":      (P.poi_web.values, np.ones(len(P)), "places with website (tract mean)"),
    "nosem":    ((1-P.bld_sem_share).values, np.ones(len(P)), "footprints without class/name/floors (tract mean)"),
    "ms":       (P.sh_ms.values, np.ones(len(P)), "Microsoft-ML share of footprints (tract mean)"),
    "lowconf":  (P.poi_lowconf.values, np.ones(len(P)), "places with confidence < 0.5 (tract mean)"),
}
IND["addr_pw"][0][P.n_poi.values == 0] = np.nan
rows = []
for sname, m in S.items():
    for k, (nu, de, lab) in IND.items():
        r = cluster_boot_ratio(nu.astype(float), de.astype(float), m.values.astype(float), cl)
        rows.append({"stratum": sname, "indicator": k, "label": lab, **r, "pop_in": int(P.pop_total[m == 1].sum())})
ST = pd.DataFrame(rows)
tested = ST.indicator.isin(["osm", "sem", "poi1k", "addr", "addr_pw", "web"])   # complements / scorecard-only columns are not re-tested
ST.loc[tested, "q_bh"] = bh(ST.loc[tested, "p_boot"].values)
ST.to_csv("reports/tables/strata_indicators.csv", index=False); OUT["strata"] = ST.round(4).to_dict(orient="records")
num("strata_tests", int(tested.sum()), "stratum x indicator tests in the strata table (BH family)")
num("strata_tests_q05", int((ST.q_bh < 0.05).sum()), "of those, BH q < 0.05")

# ---------------------------------------------------------------- 3. regressions (county-clustered + wild bootstrap)
TERMS = ["rural", "reservation", "tribal_statistical", "svi_overall", "tx_border", "az_border", "log10_density"]
X = design(P, TERMS)
P["log_poi1k"] = np.log(P.poi_per_1k.clip(lower=0.5))
models = {"OSM share of footprints": (P.sh_osm, None), "log places per 1k residents": (P.log_poi1k, None),
          "share of places with address": (P.poi_addr, None), "share of places with website": (P.poi_web, None),
          "share of places with address (place-weighted)": (P.poi_addr, P.n_poi.astype(float))}
R = []
for name, (y, w) in models.items():
    o = cluster_ols(y, X, P.county5.values, w=w, boot_terms=TERMS); o.insert(0, "model", name); R.append(o)
REG = pd.concat(R); REG = REG[~REG.term.str.startswith("fe_") & (REG.term != "const")].reset_index(drop=True)
REG["p_cr1"] = 2*norm.sf(np.abs(REG.t_cr1))
fam = ~REG.model.str.contains("weighted")
REG.loc[fam, "p_holm"] = holm(REG.loc[fam, "p_wcr"].values); REG.loc[fam, "q_bh"] = bh(REG.loc[fam, "p_wcr"].values)
REG.to_csv("reports/tables/regressions.csv", index=False); OUT["reg"] = REG.round(4).to_dict(orient="records")
num("reg_family_terms", int(fam.sum()), "regression terms in the Holm/BH family (4 outcomes x 7 terms)")
num("reg_n", int(REG.n.iloc[0]), "tracts in the regressions (populated, complete covariates)")
num("reg_clusters", int(REG.clusters.iloc[0]), "county clusters")
def g(model, term, col): return float(REG[(REG.model == model) & (REG.term == term)][col].iloc[0])
for mshort, mname in [("osm", "OSM share of footprints"), ("poi", "log places per 1k residents"), ("addr", "share of places with address"),
                      ("web", "share of places with website"), ("addrpw", "share of places with address (place-weighted)")]:
    for t in TERMS:
        for col in ["coef", "t_cr1", "p_wcr"] + (["p_holm"] if mshort != "addrpw" else []):
            num(f"reg_{mshort}_{t}_{col}", g(mname, t, col), f"{mname}: {t} {col}")
# robustness: reservation clustering and place-source controls for the address gap
o = cluster_ols(P.poi_addr, X, P.cl_res.values, boot_terms=["reservation"])
num("addr_res_clres_t", float(o.set_index("term").t_cr1["reservation"]), "address ~ reservation, clustered by reservation-or-county: t")
num("addr_res_clres_p", float(o.set_index("term").p_wcr["reservation"]), "same: wild-cluster bootstrap p")
P["log_n_poi"] = np.log(P.n_poi.clip(lower=1))
X2 = design(P, TERMS + ["poi_meta_share", "log_n_poi"])
o = cluster_ols(P.poi_addr, X2, P.county5.values, boot_terms=["reservation"]).set_index("term")
num("addr_res_srcctrl_coef", float(o.coef["reservation"]), "address ~ reservation + Meta share + log(n places): coef")
num("addr_res_srcctrl_t", float(o.t_cr1["reservation"]), "same: clustered t"); num("addr_res_srcctrl_p", float(o.p_wcr["reservation"]), "same: WCR p")
# Meta-only address rate: is the reservation gap inside Meta's listings?
P["addr_meta_rate"] = P.addr_meta/P.n_meta.replace(0, np.nan)
o = cluster_ols(P.addr_meta_rate, X, P.county5.values, w=P.n_meta.astype(float), boot_terms=["reservation"]).set_index("term")
num("addr_meta_res_coef", float(o.coef["reservation"]), "Meta places only, place-weighted address ~ reservation: coef")
num("addr_meta_res_t", float(o.t_cr1["reservation"]), "same: clustered t"); num("addr_meta_res_p", float(o.p_wcr["reservation"]), "same: WCR p")

# ---------------------------------------------------------------- 4. reservation address gap
res = P.reservation
num("res_tracts", int(res.sum()), "populated tracts flagged as legal reservation / trust land (N1)")
num("res_nations", int(P.loc[res, "aiannh_name"].nunique()), "distinct reservation / trust-land areas among them")
num("res_counties", int(P.loc[res, "county5"].nunique()), "counties containing them")
num("res_pop", int(P.pop_total[res].sum()), "residents of N1 tracts")
num("res_addr_tract", P.poi_addr[res].mean(), "N1: tract-mean address share"); num("nonres_addr_tract", P.poi_addr[~res].mean(), "rest: tract-mean address share")
num("res_addr_place", P.n_addr_all[res].sum()/P.n_poi[res].sum(), "N1: place-weighted address share")
num("nonres_addr_place", P.n_addr_all[~res].sum()/P.n_poi[~res].sum(), "rest: place-weighted address share")
num("res_places_median", float(P.n_poi[res].median()), "N1: median places per tract"); num("res_places_min", int(P.n_poi[res].min()), "N1: min places per tract")
az = P.region.eq("maricopa-az")
num("az_res_tracts", int((az & res).sum()), "maricopa-az N1 tracts")
num("az_res_addr", P.poi_addr[az & res].mean(), "maricopa-az N1 tract-mean address share"); num("az_nonres_addr", P.poi_addr[az & ~res].mean(), "maricopa-az rest")
azr = az & rur
num("az_rural_res_addr", P.poi_addr[azr & res].mean(), "rural maricopa-az, N1"); num("az_rural_nonres_addr", P.poi_addr[azr & ~res].mean(), "rural maricopa-az, rest")
num("az_rural_res_tracts", int((azr & res).sum()), "rural maricopa-az N1 tracts")
num("urban_addr_tractmean", P.poi_addr[P.ur_class.eq("Urban")].mean(), "urban tracts: tract-mean address share")
# who supplies the places without an address
tot_missing = (P.n_poi - P.n_addr_all).sum(); meta_missing = (P.n_meta - P.addr_meta).sum()
num("missing_addr_meta_share", meta_missing/tot_missing, "share of all address-less places that come from Meta")
num("meta_place_share_all", P.n_meta.sum()/P.n_poi.sum(), "share of all places that come from Meta")
for lab, m in [("res", res), ("nonres", ~res)]:
    num(f"{lab}_meta_share", P.n_meta[m].sum()/P.n_poi[m].sum(), f"{lab}: share of places from Meta (pooled)")
    num(f"{lab}_meta_addr", P.addr_meta[m].sum()/P.n_meta[m].sum(), f"{lab}: address share of Meta places (pooled)")
    num(f"{lab}_other_addr", P.addr_other[m].sum()/P.n_other[m].sum(), f"{lab}: address share of non-Meta places (pooled)")
srcmix = pd.concat([pd.read_parquet(f"reports/cache/{r}-poisrc.parquet") for r in REGIONS]).merge(P[["GEOID", "reservation"]], on="GEOID")
SM = srcmix.groupby(["reservation", "src"])[["n", "n_addr"]].sum().reset_index()
SM["share_of_places"] = SM.n/SM.groupby("reservation").n.transform("sum"); SM["address_rate"] = SM.n_addr/SM.n
SM.to_csv("reports/tables/reservation_place_sources.csv", index=False); OUT["res_place_sources"] = SM.round(4).to_dict(orient="records")
# example tables (N1-flagged only) with Wilson 95% CIs
def ex(df):
    df = df.copy(); df["addr_n"] = (df.poi_addr*df.n_poi).round().astype(int)
    ci = [wilson(k, n) for k, n in zip(df.addr_n, df.n_poi.astype(int))]
    df["addr_lo"], df["addr_hi"] = [c[0] for c in ci], [c[1] for c in ci]
    df["meta_share"] = df.n_meta/df.n_poi; return df
cols = ["GEOID", "region", "aiannh_name", "pop_total", "n_poi", "poi_addr", "poi_web", "n_meta", "ghcn_any_nearest_km", "sh_ms", "svi_overall"]
EXR = ex(P[res & (P.pop_total >= 500)].nsmallest(8, "poi_addr")[cols]); EXR.to_csv("reports/tables/examples_reservation_low_address.csv", index=False)
EXW = ex(P[res & P.region.eq("eastern-wa") & (P.pop_total >= 500)].nsmallest(3, "poi_addr")[cols]); EXW.to_csv("reports/tables/examples_reservation_wa.csv", index=False)
EXO = P[P.tribal_statistical & P.region.eq("eastern-ok") & (P.pop_total >= 1000)].nsmallest(4, "poi_per_1k")[cols + ["poi_per_1k"]]
EXO.to_csv("reports/tables/examples_ok_statistical_low_places.csv", index=False)
OUT["examples_res"] = EXR.round(3).astype(object).where(EXR.notna(), None).to_dict(orient="records")

# ---------------------------------------------------------------- 5. ML-only urban neighbourhoods
U = P[P.ur_class.eq("Urban")]; ml = U.sh_osm < 0.05
num("mlonly_tracts", int(ml.sum()), "urban tracts with <5% OSM footprints"); num("mlonly_pop", int(U.pop_total[ml].sum()), "their residents")
num("mlonly_svi", U.svi_overall[ml].mean(), "their mean SVI (missing SVI excluded)"); num("urban_other_svi", U.svi_overall[~ml].mean(), "other urban tracts mean SVI")
num("mlonly_minority", U.svi_minority[ml].mean(), "mean SVI minority percentile"); num("urban_other_minority", U.svi_minority[~ml].mean(), "other urban")
num("mlonly_sem", U.bld_sem_share[ml].mean(), "mean semantic share"); num("mlonly_web", U.poi_web[ml].mean(), "mean website share"); num("urban_other_web", U.poi_web[~ml].mean(), "other urban")
num("mlonly_in_txborder", int((ml & U.tx_border).sum()), "ML-only urban tracts inside the South Texas border seam")
num("mlonly_counties", int(U.county5[ml].nunique()), "counties containing ML-only urban tracts")
r_ = cluster_boot_ratio(U.svi_overall.values, np.ones(len(U)), ml.astype(float).values, U.county5.values)
num("mlonly_svi_diff_p", r_["p_boot"], "county-cluster bootstrap p, ML-only vs other urban SVI")
CN = U[ml].groupby("county5").agg(tracts=("GEOID", "size"), residents=("pop_total", "sum"), mean_svi=("svi_overall", "mean"),
        county_urban_tracts=("GEOID", "size")).sort_values("tracts", ascending=False)
CN["county_urban_tracts"] = U.groupby("county5").size().reindex(CN.index); CN["share_of_county_urban"] = CN.tracts/CN.county_urban_tracts
CN.to_csv("reports/tables/mlonly_by_county.csv"); OUT["mlonly_county"] = CN.round(3).reset_index().to_dict(orient="records")
EXU = U[ml & (U.pop_total >= 2000)].sort_values(["sh_ms", "pop_total"], ascending=False).head(8)[cols + ["n_bld", "housing_units", "bld_sem_share"]]
EXU.to_csv("reports/tables/examples_urban_ml_only.csv", index=False)
P[P.ur_class.eq("Urban") & (P.pop_total >= 2000)].nlargest(3, "bld_sem_share")[cols + ["sh_osm", "bld_sem_share"]].to_csv("reports/tables/examples_contrast_urban_osm_rich.csv", index=False)

# ---------------------------------------------------------------- 6. South Texas border seam (+ Arizona contrast)
tx = P.region.eq("south-central-tx"); azr_ = P.region.eq("maricopa-az")
P["zone"] = np.select([P.tx_border, tx, P.az_border, azr_], ["TX seam", "TX rest", "AZ border", "AZ rest"], "other")
BD = P[P.zone != "other"].groupby(["zone", "ur_class"]).apply(lambda d: pd.Series({
    "tracts": len(d), "residents": d.pop_total.sum(), "osm": d.b_osm.sum()/d.n_bld.sum(), "ms": d.b_ms.sum()/d.n_bld.sum(),
    "gob": d.b_gob.sum()/d.n_bld.sum(), "esri": d.b_esri.sum()/d.n_bld.sum(), "sem": (d.bld_sem_share*d.n_bld).sum()/d.n_bld.sum(),
    "places_per_1k": 1000*d.n_poi.sum()/d.pop_total.sum(), "web": d.poi_web.mean(), "addr": d.poi_addr.mean(), "svi": d.svi_overall.mean()}),
    include_groups=False)
BD.to_csv("reports/tables/border_seam.csv"); OUT["border"] = BD.round(4).reset_index().to_dict(orient="records")
num("txseam_tracts", int(P.tx_border.sum()), "South Texas border seam tracts (populated)"); num("txseam_pop", int(P.pop_total[P.tx_border].sum()), "their residents")
num("txseam_counties", int(P.county5[P.tx_border].nunique()), "seam counties with populated tracts")
num("txseam_svi", P.svi_overall[P.tx_border].mean(), "seam mean SVI"); num("txrest_svi", P.svi_overall[tx & ~P.tx_border].mean(), "rest of TX region mean SVI")
num("azborder_tracts", int(P.az_border.sum()), "Arizona-contrast tracts"); num("azborder_pop", int(P.pop_total[P.az_border].sum()), "their residents")
for z, m in [("txseam", P.tx_border), ("txrest", tx & ~P.tx_border), ("azborder", P.az_border), ("azrest", azr_ & ~P.az_border)]:
    num(f"{z}_osm_pooled", P.b_osm[m].sum()/P.n_bld[m].sum(), f"{z}: pooled OSM share"); num(f"{z}_gob_pooled", P.b_gob[m].sum()/P.n_bld[m].sum(), f"{z}: pooled Google share")
    num(f"{z}_poi1k_pooled", 1000*P.n_poi[m].sum()/P.pop_total[m].sum(), f"{z}: places per 1k (pooled)")
num("gob_tracts", int((M.b_gob > 0).sum()), "scored tracts with any Google Open Buildings footprint"); num("gob_footprints", int(M.b_gob.sum()), "Google footprints")
num("gob_max_share", float(P.sh_gob.max()), "max tract Google share"); num("n2_tracts", int((P.sh_gob.fillna(0) > 0.05).sum()), "N2 tracts (Google > 5%)")
num("n2_pop", int(P.pop_total[P.sh_gob.fillna(0) > 0.05].sum()), "N2 residents")
gb = P.b_gob > 0; bc = P.county5.isin(TX_BORDER) | P.county5.isin(AZ_BORDER)
num("gob_tracts_in_border_counties", int((gb & bc).sum()), "populated Google tracts in a county on the international border")
num("gob_tracts_outside_border_counties", int((gb & ~bc).sum()), "populated Google tracts elsewhere")
OUT["gob_outside"] = P.loc[gb & ~bc, ["GEOID", "county5", "b_gob", "sh_gob"]].round(3).to_dict(orient="records")
num("gob_share_of_txseam_footprints", P.b_gob[P.tx_border].sum()/P.n_bld[P.tx_border].sum(), "Google share of seam footprints")
CNT = M[M.b_gob > 0].assign(county5=lambda d: d.GEOID.str[:5]).groupby("county5").agg(tracts_with_google=("GEOID", "size"), google_footprints=("b_gob", "sum"),
        median_google_share=("sh_gob", "median")).sort_values("google_footprints", ascending=False)
CNT["border_county"] = CNT.index.isin(list(TX_BORDER) + list(AZ_BORDER)); CNT.to_csv("reports/tables/gob_by_county.csv")
EXB = P[P.pop_total >= 1000].nlargest(6, "sh_gob")[cols + ["sh_gob", "sh_osm", "poi_per_1k"]]; EXB.to_csv("reports/tables/examples_border_high_gob.csv", index=False)
for gid in ["48323950702", "04003000902", "48323950206"]:
    rr = P[P.GEOID == gid].iloc[0]
    for c in ["pop_total", "sh_gob", "sh_osm", "poi_per_1k", "poi_addr"]: num(f"ex_{gid}_{c}", float(rr[c]), f"tract {gid}: {c}")
num("txrest_poi1k_median", float(P.poi_per_1k[tx & ~P.tx_border].median()), "rest of TX region: median places per 1k")

# ---------------------------------------------------------------- 7. is the building benchmark circular? (buildings per housing unit)
H = P[(P.housing_units >= 50) & (P.n_bld > 0)].copy()
num("ms50_tracts", int((M.sh_ms >= 0.5).sum()), "scored tracts where >=50% of Overture footprints are Microsoft ML")
num("ms50_pop", int(M.pop_total[M.sh_ms >= 0.5].sum()), "their residents")
num("ms50_share_tracts", float((M.sh_ms >= 0.5).sum()/(M.n_bld > 0).sum()), "share of tracts with buildings")
num("ms50_footprint_share", float(M.b_ms[M.sh_ms >= 0.5].sum()/M.n_bld.sum()), "share of all footprints that sit in those tracts and are MS")
num("ml50_tracts", int(((M.sh_ms + M.sh_gob) >= 0.5).sum()), "tracts >=50% ML (Microsoft + Google)")
HU = H[H.ur_class.eq("Urban")].copy()
HU["osm_bin"] = pd.cut(HU.sh_osm, [-0.01, 0.05, 0.5, 0.95, 1.0], labels=["<5%", "5-50%", "50-95%", ">95%"])
HU["dens_q"] = pd.qcut(HU.log10_density, 5, labels=False)
BPH = HU.groupby("osm_bin", observed=True).agg(tracts=("GEOID", "size"), median_bld_per_hu=("bld_per_hu", "median"),
        median_density=("density", "median"), median_svi=("svi_overall", "median"))
BPH.to_csv("reports/tables/bld_per_hu_by_osm.csv"); OUT["bld_per_hu"] = BPH.round(3).reset_index().to_dict(orient="records")
for b_, rr in BPH.iterrows(): num(f"bph_urban_{b_}", float(rr.median_bld_per_hu), f"urban median buildings per housing unit, OSM share {b_}"); num(f"bph_urban_{b_}_n", int(rr.tracts), f"urban tracts, OSM share {b_}")
WD = HU.groupby(["dens_q", "osm_bin"], observed=True).bld_per_hu.median().unstack(); WD.to_csv("reports/tables/bld_per_hu_by_density_osm.csv")
num("bph_density_quintiles_osm_lower", int((WD[">95%"] < WD["<5%"]).sum()), "density quintiles where >95%-OSM tracts have fewer buildings/HU than <5%-OSM tracts")
H["log_bph"] = np.log(H.bld_per_hu)
Xb = design(H, ["sh_osm", "rural", "svi_overall", "log10_density"])
ob = cluster_ols(H.log_bph, Xb, H.county5.values, boot_terms=["sh_osm"]).set_index("term")
num("bph_osm_coef", float(ob.coef["sh_osm"]), "log(buildings/HU) ~ OSM share (+rural, SVI, density, region FE): coef")
num("bph_osm_t", float(ob.t_cr1["sh_osm"]), "same: clustered t"); num("bph_osm_p", float(ob.p_wcr["sh_osm"]), "same: WCR p"); num("bph_n", int(ob.n.iloc[0]), "tracts (HU>=50)")
Xc = Xb.drop(columns=[c for c in Xb if c.startswith("fe_")])
Xc = pd.concat([Xc, pd.get_dummies(H.county5, prefix="c", drop_first=True, dtype=float)], axis=1)
oc = cluster_ols(H.log_bph, Xc, H.county5.values, boot_terms=["sh_osm"]).set_index("term")
num("bph_osm_coef_countyfe", float(oc.coef["sh_osm"]), "same with county fixed effects: coef"); num("bph_osm_t_countyfe", float(oc.t_cr1["sh_osm"]), "county FE: t")
num("bph_osm_p_countyfe", float(oc.p_wcr["sh_osm"]), "county FE: WCR p")
num("bph_osm_pct_full", float(np.exp(ob.coef["sh_osm"]) - 1), "implied % change in buildings/HU from 0% to 100% OSM (region FE)")
num("bph_osm_pct_full_countyfe", float(np.exp(oc.coef["sh_osm"]) - 1), "same, county FE")

# ---------------------------------------------------------------- 8. fire vintage: null comparison
bF = (P.nifc_wildfire_burned_pct_land >= 30) & (P.nifc_wildfire_last_year >= 2018)
F, N = P[bF].copy(), P[~bF]
F["obs"] = F.bld_mean_year < F.nifc_wildfire_last_year
F["exp"] = [(N.loc[N.region == r, "bld_mean_year"] < y).mean() for r, y in zip(F.region, F.nifc_wildfire_last_year)]
FV = F.groupby("region").agg(tracts=("GEOID", "size"), observed=("obs", "mean"), expected_null=("exp", "mean"))
FV.loc["all"] = [len(F), F.obs.mean(), F.exp.mean()]; FV.to_csv("reports/tables/fire_vintage_null.csv"); OUT["fire"] = FV.round(3).reset_index().to_dict(orient="records")
ca = F[F.region == "northern-ca"]
z = (ca.obs.sum() - ca.exp.sum())/np.sqrt((ca.exp*(1-ca.exp)).sum())
num("fire_burned_tracts", len(F), "burned tracts (>=30% of land, last fire >=2018)"); num("fire_obs_all", F.obs.mean(), "share with mean footprint year < last fire")
num("fire_null_all", F.exp.mean(), "null expectation (same-region unburned tracts)")
num("fire_ca_n", len(ca), "northern-ca burned tracts"); num("fire_ca_obs", ca.obs.mean(), "northern-ca observed"); num("fire_ca_null", ca.exp.mean(), "northern-ca null")
num("fire_ca_p", float(2*norm.sf(abs(z))), "northern-ca: two-sided p (independent-Bernoulli approximation, ignores spatial correlation)")
num("fire_2025_share", float((F.nifc_wildfire_last_year == 2025).mean()), "share of burned tracts whose last fire was 2025")
F[["GEOID", "region", "NAMELSAD", "pop_total", "nifc_wildfire_last_year", "bld_mean_year", "bld_new_share", "obs", "exp"]].to_csv("reports/tables/fire_vintage.csv", index=False)
for gid in ["06061020200", "06033000501"]:
    rr = P[P.GEOID == gid].iloc[0]; num(f"ex_{gid}_mean_year", float(rr.bld_mean_year), f"{gid}: mean footprint source year"); num(f"ex_{gid}_new_share", float(rr.bld_new_share), f"{gid}: share 2020+")
pa = P[P.GEOID.str[:5].eq("06007") & P.GEOID.between("06007001703", "06007002300")]
num("paradise_new_share_min", float(pa.bld_new_share.min()), "Paradise tracts: min share of footprints with 2020+ source date")
num("paradise_new_share_max", float(pa.bld_new_share.max()), "Paradise tracts: max share 2020+")

# ---------------------------------------------------------------- 9. leaderboard scorecard comparison (directional only)
LB = {"Rural": 2.34, "Tribal (any overlap)": 2.88, "High SVI (>=0.75)": 1.23, "High CVI (top 25%)": 1.55, "Winter drought (top 25%)": 1.36,
      "Wildfire hazard (WHP top 25%)": 1.77, "Summer heat (top 25%)": 0.62, "Hazard + high SVI": 1.22}
piv = ST[ST.stratum.isin(LB)].pivot(index="stratum", columns="indicator", values="ratio").reindex(list(LB))
# The 7 indicators we tried against the scorecard (all disclosed), oriented so that higher = worse mapped
cand = {"non-OSM share": piv["nonosm"], "missing address": piv["noaddr"], "no semantic attributes": piv["nosem"],
        "Microsoft-ML share": piv["ms"], "low-confidence places": piv["lowconf"], "website (inverse)": 1/piv["web"],
        "places per 1k (inverse)": 1/piv["poi1k"]}
lb = np.array(list(LB.values())); perms = np.array(list(itertools.permutations(range(8))))
def perm_p(x):
    rho = spearmanr(lb, x).statistic; rr = np.argsort(np.argsort(x)); rl = np.argsort(np.argsort(lb))
    d = ((rl[None, :] - rr[perms])**2).sum(1); rhos = 1 - 6*d/(8*63)
    return rho, (rhos >= rho - 1e-12).mean()
AG = pd.DataFrame([{"indicator": k, "rho": perm_p(v.values)[0], "p_exact_one_sided": perm_p(v.values)[1]} for k, v in cand.items()])
AG["p_bonferroni_7"] = (AG.p_exact_one_sided*len(AG)).clip(upper=1)
AG.to_csv("reports/tables/scorecard_agreement_tests.csv", index=False); OUT["agreement"] = AG.round(4).to_dict(orient="records")
TAB = pd.DataFrame({"scorecard_ratio": LB, "nonosm_ratio": piv["nonosm"], "noaddr_ratio": piv["noaddr"]}); TAB.to_csv("reports/tables/scorecard_agreement.csv")
for _, rr in AG.iterrows():
    k = {"non-OSM share": "nonosm", "missing address": "noaddr", "no semantic attributes": "nosem", "Microsoft-ML share": "ms",
         "low-confidence places": "lowconf", "website (inverse)": "web", "places per 1k (inverse)": "poi1k"}[rr.indicator]
    num(f"agree_{k}_rho", rr.rho, f"Spearman rho vs scorecard: {rr.indicator}"); num(f"agree_{k}_p", rr.p_exact_one_sided, f"exact one-sided p: {rr.indicator}")
    num(f"agree_{k}_pbonf", rr.p_bonferroni_7, f"Bonferroni x7: {rr.indicator}")
v5 = pd.read_csv("reports/cache/v5_reproduced.csv", dtype={"GEOID": str}).rename(columns={"coverage_gap_score": "v5"})
P2 = P.merge(v5, on="GEOID", how="left"); S2 = strata(P2)
for s_ in ["High SVI (>=0.75)", "High CVI (top 25%)"]:
    m = S2[s_]; num(f"v5_ratio_{s_.split()[1]}", P2.v5[m == 1].mean()/P2.v5[m == 0].mean(), f"v5 predicted ratio, {s_}")

# ---------------------------------------------------------------- 10. reach (overlapping groups)
num("pop_rural", int(P.pop_total[rur].sum()), "residents of rural tracts"); num("pop_tribal_any", int(P.pop_total[P.tribal_any.astype(bool)].sum()), "residents of tracts overlapping tribal land")
num("pop_total_populated", int(P.pop_total.sum()), "residents of all populated scored tracts")

json.dump(OUT, open("reports/tables/results.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
NU = pd.DataFrame(NUM); NU.to_csv("reports/tables/report_numbers.csv", index=False)
print(len(NU), "numbers written"); print(REG[["model", "term", "coef", "t_cr1", "p_wcr", "p_holm"]].round(3).to_string())
