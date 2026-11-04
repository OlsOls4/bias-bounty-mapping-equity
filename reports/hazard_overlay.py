"""Round-3: where do the data gaps sit relative to climate hazards? Uses only strata-table hazard columns shipped with the
challenge. A tract is "high hazard" if it is in the top quartile of all populated scored tracts on:
  wildfire  usfs_WHP_mean           (USFS Wildfire Hazard Potential; scorecard hazard)
  drought   usdm_winter_dsci        (US Drought Monitor winter DSCI; scorecard hazard)
  heat-rel  epht_heat_days_summer   (CDC EPHT days above the local 95th-percentile heat index; scorecard hazard, RELATIVE)
  heat-abs  gehe_wbgt28_days_mean   (NASA GEHE days with wet-bulb globe temperature >= 28 C; ABSOLUTE heat stress)
Groups: core reservation tracts (tribal_legal_pct >= 0.5), South Texas border seam, ML-only urban tracts (<5% OSM footprints).
Run after analysis.py:  python reports/hazard_overlay.py -> reports/tables/hazard_overlay.csv, hazard_named_tracts.csv, keys 'hz_*'"""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from numbers_util import Numbers

M, P = load()
hz = Numbers("hz_")
HAZ = {"wildfire": "usfs_WHP_mean", "drought": "usdm_winter_dsci", "heat_rel": "epht_heat_days_summer", "heat_abs": "gehe_wbgt28_days_mean"}
for k, c in HAZ.items():
    thr = P[c].quantile(0.75); P[f"hi_{k}"] = P[c] >= thr; hz(f"thr_{k}", thr, f"top-quartile threshold for {c} (populated tracts)")
P["hi_any"] = P[[f"hi_{k}" for k in HAZ]].any(axis=1)
P["core_res"] = P.reservation & (P.tribal_legal_pct >= 0.5)
P["mlonly_urban"] = P.ur_class.eq("Urban") & (P.sh_osm < 0.05)
P["noaddr_n"] = P.n_poi - P.n_addr_all
P["ml_n"] = P.b_ms + P.b_gob
GROUPS = {"core_res": "Reservation / trust land (core, >=50% overlap)", "tx_border": "South Texas border seam", "mlonly_urban": "ML-only urban tracts (<5% OSM)"}
rows = []
for g, lab in GROUPS.items():
    G = P[P[g]]
    for k in list(HAZ) + ["any"]:
        H = G[G[f"hi_{k}"]]
        rows.append({"group": lab, "hazard": k, "tracts": len(H), "of_group_tracts": len(G), "residents": int(H.pop_total.sum()),
                     "places": int(H.n_poi.sum()), "places_no_address": int(H.noaddr_n.sum()),
                     "addr_share_tractmean": H.poi_addr.mean(), "ml_footprint_share": H.ml_n.sum()/max(H.n_bld.sum(), 1),
                     "footprints": int(H.n_bld.sum()), "footprints_ml": int(H.ml_n.sum())})
        for c in ["tracts", "residents", "places_no_address", "addr_share_tractmean", "ml_footprint_share", "footprints_ml"]:
            hz(f"{g}_{k}_{c}", rows[-1][c], f"{lab}, top-quartile {k}: {c}")
    hz(f"{g}_tracts", len(G), f"{lab}: tracts"); hz(f"{g}_pop", int(G.pop_total.sum()), f"{lab}: residents")
O = pd.DataFrame(rows); O.to_csv("reports/tables/hazard_overlay.csv", index=False)
# hazard exposure relative to the rest of the study area (share of tracts high-hazard)
for g in GROUPS:
    for k in list(HAZ) + ["any"]:
        hz(f"{g}_{k}_share", P[f"hi_{k}"][P[g]].mean(), f"{g}: share of tracts top-quartile {k}")
for k in list(HAZ) + ["any"]: hz(f"all_{k}_share", P[f"hi_{k}"].mean(), f"all populated tracts: share top-quartile {k}")
# named tracts
cols = ["GEOID", "region", "aiannh_name", "pop_total", "n_poi", "poi_addr", "sh_osm", "sh_ms", "sh_gob", "svi_overall"] + list(HAZ.values())
NT = pd.concat([
    P[P.core_res & P.hi_wildfire].nsmallest(6, "poi_addr")[cols].assign(why="reservation, top-quartile wildfire hazard"),
    P[P.core_res & P.hi_drought].nsmallest(6, "poi_addr")[cols].assign(why="reservation, top-quartile winter drought"),
    P[P.core_res & P.hi_heat_rel].nsmallest(4, "poi_addr")[cols].assign(why="reservation, top-quartile relative heat"),
    P[P.tx_border & P.hi_heat_abs & (P.pop_total >= 1000)].nsmallest(6, "sh_osm")[cols].assign(why="seam, top-quartile absolute heat (WBGT)"),
])
NT.to_csv("reports/tables/hazard_named_tracts.csv", index=False)
for gid in ["04019941100", "04017940100", "04009940500", "04017940014", "04005945100", "53077940003", "53019940000", "48215021906", "48323950702"]:
    r = P[P.GEOID == gid].iloc[0]
    for k, c in HAZ.items():
        hz(f"ex_{gid}_{k}", r[c], f"{gid}: {c}"); hz(f"ex_{gid}_{k}_hi", bool(r[f"hi_{k}"]), f"{gid}: top quartile {k}?")
    hz(f"ex_{gid}_pctile_heat_abs", (P.gehe_wbgt28_days_mean <= r.gehe_wbgt28_days_mean).mean(), f"{gid}: percentile of WBGT>=28 days")
    hz(f"ex_{gid}_pctile_wildfire", (P.usfs_WHP_mean <= r.usfs_WHP_mean).mean(), f"{gid}: percentile of WHP")
hz.publish()
print(O.round(3).to_string()); print(NT[["GEOID", "aiannh_name", "pop_total", "poi_addr", "sh_osm", "why"] + list(HAZ.values())].round(2).to_string())
