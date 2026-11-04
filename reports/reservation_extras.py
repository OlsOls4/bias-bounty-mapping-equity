"""Round-3 robustness for Finding 1 (reservation place addresses) and 95% CIs for the headline regression terms.
Run from the project root after analysis.py (needs reports/cache/<region>-poicat.parquet from poi_category_address.py).
    python reports/reservation_extras.py
Writes reports/tables/headline_ci.csv, reservation_overlap_robustness.csv, reservation_place_categories.csv and adds keys
'ci_*' and 'rx_*' to reports/tables/report_numbers.csv.

* Core reservation tracts: tribal_legal == True AND tribal_legal_pct >= 0.5 (at least half the tract's area is legal
  reservation / trust land, strata column `tribal_legal_pct`). The headline N1 set (any legal overlap) includes tracts
  such as 04001970202 (Apache County 9702.02, 1.5% overlap with Zuni trust land) whose residents mostly live off-reservation.
* Place categories are Overture `categories.primary`. "Natural features, parks and landmarks" are places that normally have
  no street address (lakes, mountains, trails, parks, landmarks...); the address gap is re-estimated without them."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from numbers_util import Numbers

M, P = load()
TERMS = ["rural", "reservation", "tribal_statistical", "svi_overall", "tx_border", "az_border", "log10_density"]

# ------------------------------------------------------------------ A. 95% CIs (CR1, county-clustered) for headline terms
ci = Numbers("ci_")
REG = pd.read_csv("reports/tables/regressions.csv")
REG["lo"], REG["hi"] = REG.coef - 1.96*REG.se_cr1, REG.coef + 1.96*REG.se_cr1
REG.to_csv("reports/tables/headline_ci.csv", index=False)
for k, (m, t) in {"addr_res": ("share of places with address", "reservation"), "addr_svi": ("share of places with address", "svi_overall"),
                  "addr_rural": ("share of places with address", "rural"),
                  "osm_txb": ("OSM share of footprints", "tx_border"), "osm_azb": ("OSM share of footprints", "az_border"),
                  "osm_rural": ("OSM share of footprints", "rural"), "osm_svi": ("OSM share of footprints", "svi_overall"),
                  "osm_res": ("OSM share of footprints", "reservation"),
                  "poi_txb": ("log places per 1k residents", "tx_border"), "web_txb": ("share of places with website", "tx_border"),
                  "addrpw_res": ("share of places with address (place-weighted)", "reservation")}.items():
    r = REG[(REG.model == m) & (REG.term == t)].iloc[0]
    if m.startswith("log"):
        ci(f"{k}_pct", np.exp(r.coef) - 1, f"{m} ~ {t}: % effect"); ci(f"{k}_pct_lo", np.exp(r.lo) - 1, "95% CI low (exp of CR1 CI)")
        ci(f"{k}_pct_hi", np.exp(r.hi) - 1, "95% CI high")
    else:
        ci(f"{k}_coef", r.coef, f"{m} ~ {t}: coef"); ci(f"{k}_lo", r.lo, "95% CI low (coef - 1.96 se_cr1)"); ci(f"{k}_hi", r.hi, "95% CI high")
for k in ["bph_osm"]:   # buildings per HU (from report_numbers, recomputed CI needs se: rerun the model)
    H = P[(P.housing_units >= 50) & (P.n_bld > 0)].copy(); H["log_bph"] = np.log(H.bld_per_hu)
    o = cluster_ols(H.log_bph, design(H, ["sh_osm", "rural", "svi_overall", "log10_density"]), H.county5.values).set_index("term")
    b, s = o.coef["sh_osm"], o.se_cr1["sh_osm"]
    ci("bph_osm_pct", np.exp(b) - 1, "buildings/HU ~ OSM share (0->100%): % effect"); ci("bph_osm_pct_lo", np.exp(b - 1.96*s) - 1, "95% CI low")
    ci("bph_osm_pct_hi", np.exp(b + 1.96*s) - 1, "95% CI high")
ci.publish()

# ------------------------------------------------------------------ B. overlap robustness
rx = Numbers("rx_")
P["core_res"] = P.reservation & (P.tribal_legal_pct >= 0.5)
P["partial_res"] = P.reservation & ~P.core_res
z = P[P.GEOID == "04001970202"].iloc[0]
rx("zuni_tract_overlap", z.tribal_legal_pct, "04001970202: share of tract area that is legal reservation/trust land (tribal_legal_pct)")
rx("core_tracts", int(P.core_res.sum()), "core reservation tracts (>=50% legal overlap)"); rx("core_pop", int(P.pop_total[P.core_res].sum()), "their residents")
rx("core_nations", int(P.aiannh_name[P.core_res].nunique()), "distinct reservation areas among them")
rx("partial_tracts", int(P.partial_res.sum()), "N1 tracts with <50% legal overlap"); rx("partial_pop", int(P.pop_total[P.partial_res].sum()), "their residents")
rx("core_addr", P.poi_addr[P.core_res].mean(), "core: tract-mean address share"); rx("rest_addr", P.poi_addr[~P.reservation].mean(), "non-reservation tracts: tract-mean")
rx("partial_addr", P.poi_addr[P.partial_res].mean(), "partial-overlap N1 tracts: tract-mean address share")
rows = []
for lab, samp, var in [("core (>=50%) vs non-reservation; partial-overlap tracts dropped", ~P.partial_res, "core_res"),
                       ("core (>=50%) flag; partial-overlap tracts kept as non-reservation", np.ones(len(P), bool), "core_res"),
                       ("headline: any legal overlap", np.ones(len(P), bool), "reservation")]:
    Q = P[samp].copy(); Q["resv"] = Q[var].astype(float)
    t_ = [t if t != "reservation" else "resv" for t in TERMS]
    o = cluster_ols(Q.poi_addr, design(Q, t_), Q.county5.values, boot_terms=["resv"]).set_index("term").loc["resv"]
    rows.append({"spec": lab, "coef": o.coef, "lo": o.coef - 1.96*o.se_cr1, "hi": o.coef + 1.96*o.se_cr1, "t": o.t_cr1, "p_wcr": o.p_wcr, "n": o.n})
OR = pd.DataFrame(rows); OR.to_csv("reports/tables/reservation_overlap_robustness.csv", index=False)
for i, k in enumerate(["core_drop", "core_keep"]):
    for c in ["coef", "lo", "hi", "t", "p_wcr"]: rx(f"{k}_{c}", OR.iloc[i][c], f"address ~ {OR.iloc[i].spec}: {c}")

# ------------------------------------------------------------------ C. which kinds of places lack an address
PC = pd.concat([pd.read_parquet(f"reports/cache/{r}-poicat.parquet") for r in REGIONS])
NATURAL = {"lake", "structure_and_geography", "mountain", "hiking_trail", "river", "beach", "bridge", "national_park", "forest",
           "waterfall", "mountain_bike_trails", "park", "landmark_and_historical_building", "monument", "campground",
           "wildlife_sanctuary", "state_park", "nature_reserve", "canyon", "desert", "island", "reservoir", "hot_springs", "cave", "dam",
           "lookout", "scenic_point", "trail", "mountain_pass", "valley"}
GROUPS = {
    "Health (hospitals, clinics, pharmacies)": {"hospital", "childrens_hospital", "medical_center", "public_health_clinic", "community_health_center",
        "urgent_care_clinic", "walk_in_clinic", "health_and_medical", "dialysis_clinic", "pharmacy", "emergency_room", "mobile_clinic", "home_health_care"},
    "Fire, police, EMS": {"fire_department", "police_department", "ambulance_and_ems_services", "fire_protection_service"},
    "Schools": {"elementary_school", "middle_school", "high_school", "school", "public_school", "private_school", "education", "college_university", "preschool"},
    "Government and community (incl. chapter houses)": {"central_government_office", "public_service_and_government", "community_center", "town_hall",
        "post_office", "library", "community_services_non_profits", "courthouse", "social_service_organizations", "senior_citizen_services", "charity_organization"},
    "Food, fuel and supplies": {"grocery_store", "convenience_store", "gas_station", "truck_gas_station", "discount_store", "supermarket", "shopping",
        "department_store", "hardware_store", "general_store"},
    "Churches and worship": {"church_cathedral", "religious_organization", "baptist_church", "catholic_church", "pentecostal_church", "evangelical_church",
        "anglican_church", "methodist_church", "mosque", "synagogue", "buddhist_temple", "hindu_temple"},
}
def grp(c):
    if c in NATURAL: return "Natural features, parks, landmarks"
    for g_, s in GROUPS.items():
        if c in s: return g_
    return "Other businesses and services"
PC["grp"] = PC.cat.map(grp)
PC = PC.merge(P[["GEOID", "core_res", "reservation", "partial_res"]], on="GEOID")
PC["zone"] = np.where(PC.core_res, "core", np.where(PC.partial_res, "partial", "rest"))
T = PC[PC.zone != "partial"].groupby(["grp", "zone"])[["n", "n_addr"]].sum().unstack("zone")
T.columns = [f"{a}_{b}" for a, b in T.columns]
T["miss_core"] = T.n_core - T.n_addr_core; T["rate_core"] = T.n_addr_core/T.n_core; T["rate_rest"] = T.n_addr_rest/T.n_rest
T = T.sort_values("miss_core", ascending=False); T.to_csv("reports/tables/reservation_place_categories.csv")
miss = T.miss_core.sum()
rx("core_places", int(T.n_core.sum()), "places in core reservation tracts"); rx("core_missing", int(miss), "of which without a street address")
rx("core_missing_natural_share", T.loc["Natural features, parks, landmarks", "miss_core"]/miss, "share of address-less core places that are natural features/parks/landmarks")
relief = list(GROUPS)
rx("core_missing_relief", int(T.loc[relief, "miss_core"].sum()), "address-less core places in the six relief-relevant groups")
rx("core_relief_places", int(T.loc[relief, "n_core"].sum()), "core places in the six relief-relevant groups")
rx("core_relief_rate", T.loc[relief, "n_addr_core"].sum()/T.loc[relief, "n_core"].sum(), "address rate, relief-relevant places, core reservation")
rx("rest_relief_rate", T.loc[relief, "n_addr_rest"].sum()/T.loc[relief, "n_rest"].sum(), "address rate, relief-relevant places, non-reservation")
for g_ in T.index:
    k = g_.split()[0].lower().strip(",")
    rx(f"grp_{k}_n_core", int(T.loc[g_, "n_core"]), f"{g_}: places, core"); rx(f"grp_{k}_miss_core", int(T.loc[g_, "miss_core"]), f"{g_}: address-less, core")
    rx(f"grp_{k}_rate_core", T.loc[g_, "rate_core"], f"{g_}: address rate core"); rx(f"grp_{k}_rate_rest", T.loc[g_, "rate_rest"], f"{g_}: address rate non-reservation")
# address gap without natural features: tract-level share of non-natural places with an address
A = PC[PC.grp != "Natural features, parks, landmarks"].groupby("GEOID")[["n", "n_addr"]].sum()
P = P.merge((A.n_addr/A.n).rename("addr_built"), left_on="GEOID", right_index=True, how="left")
Rl = PC[PC.grp.isin(relief)].groupby("GEOID")[["n", "n_addr"]].sum()
P = P.merge((Rl.n_addr/Rl.n).rename("addr_relief"), left_on="GEOID", right_index=True, how="left")
for y, k in [("addr_built", "built"), ("addr_relief", "relief")]:
    Q = P[~P.partial_res].copy(); Q["resv"] = Q.core_res.astype(float)
    t_ = [t if t != "reservation" else "resv" for t in TERMS]
    o = cluster_ols(Q[y], design(Q, t_), Q.county5.values, boot_terms=["resv"]).set_index("term").loc["resv"]
    rx(f"{k}_coef", o.coef, f"{y} ~ core reservation (+controls, partial dropped): coef"); rx(f"{k}_lo", o.coef - 1.96*o.se_cr1, "95% CI low")
    rx(f"{k}_hi", o.coef + 1.96*o.se_cr1, "95% CI high"); rx(f"{k}_p", o.p_wcr, "WCR p"); rx(f"{k}_n", int(o.n), "tracts")
    rx(f"{k}_core_mean", Q[y][Q.core_res].mean(), f"{y}: core tract mean"); rx(f"{k}_rest_mean", Q[y][~Q.core_res].mean(), f"{y}: non-reservation tract mean")
# named examples: address-less relief-relevant places in the lowest-address core tracts
EX = PC[PC.grp.isin(relief) & PC.core_res].assign(miss=lambda d: d.n - d.n_addr).groupby(["GEOID", "grp"]).miss.sum().unstack(fill_value=0)
EX["total_relief_missing"] = EX.sum(axis=1)
EX = EX.join(P.set_index("GEOID")[["aiannh_name", "pop_total", "poi_addr", "addr_built"]]).sort_values("total_relief_missing", ascending=False)
EX.to_csv("reports/tables/reservation_relief_places_missing.csv")
for gid in ["04019941100", "04009940500", "04017940100", "04005945100"]:
    if gid in EX.index:
        rx(f"ex_{gid}_relief_missing", int(EX.loc[gid, "total_relief_missing"]), f"{gid}: address-less relief-relevant places")
        rx(f"ex_{gid}_addr_built", EX.loc[gid, "addr_built"], f"{gid}: address share excluding natural features")
rx.publish()
print(OR.round(4).to_string()); print(T[["n_core", "miss_core", "rate_core", "rate_rest"]].round(3).to_string()); print(EX.head(8).to_string())
