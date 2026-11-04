"""Round-3: does Overture list fewer emergency and service facilities on reservations than in comparable rural tracts?
Coverage (not just attributes): Overture places per 1,000 residents in fire/police/EMS, school and health categories, and the
share of tracts with no fire, police or EMS place at all. Core reservation tracts (tribal_legal_pct >= 0.5) are compared with
density-matched rural tracts in the same region that do not overlap any tribal land (tribal_any == False): for each core tract
the 5 nearest such tracts on log10 population density. Paired differences are averaged over core tracts; 95% intervals come
from a bootstrap that resamples reservations (aiannh_name), 2,000 draws, seed 20261014.
Run after poi_category_address.py and analysis.py:  python reports/reservation_facilities.py
-> reports/tables/reservation_facilities.csv, keys 'fac_*' in report_numbers.csv"""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from numbers_util import Numbers

M, P = load()
fac = Numbers("fac_")
PC = pd.concat([pd.read_parquet(f"reports/cache/{r}-poicat.parquet") for r in REGIONS])
CATS = {"emerg": {"fire_department", "police_department", "ambulance_and_ems_services", "fire_protection_service"},
        "school": {"elementary_school", "middle_school", "high_school", "school", "public_school", "private_school"},
        "health": {"hospital", "childrens_hospital", "medical_center", "public_health_clinic", "community_health_center",
                   "urgent_care_clinic", "walk_in_clinic", "emergency_room", "pharmacy"}}
for k, s in CATS.items():
    P = P.merge(PC[PC.cat.isin(s)].groupby("GEOID").n.sum().rename(f"n_{k}"), left_on="GEOID", right_index=True, how="left")
    P[f"n_{k}"] = P[f"n_{k}"].fillna(0); P[f"{k}_1k"] = 1000*P[f"n_{k}"]/P.pop_total
P["no_emerg"] = (P.n_emerg == 0).astype(float)
P["core_res"] = P.reservation & (P.tribal_legal_pct >= 0.5)
core = P[P.core_res].copy()
pool = P[P.rural & ~P.tribal_any.astype(bool)]
OUTC = ["emerg_1k", "school_1k", "health_1k", "no_emerg", "poi_per_1k"]
diffs, matches = [], []
for _, r in core.iterrows():
    c = pool[pool.region == r.region]
    m = c.iloc[np.argsort(np.abs(c.log10_density.values - r.log10_density))[:5]]
    matches.append(m.GEOID.tolist())
    diffs.append({"GEOID": r.GEOID, "nation": r.aiannh_name, "region": r.region, "pop": r.pop_total, "density": r.density,
                  "match_density": m.density.median(), **{f"{o}_res": r[o] for o in OUTC}, **{f"{o}_match": m[o].mean() for o in OUTC}})
D = pd.DataFrame(diffs)
for o in OUTC: D[f"{o}_diff"] = D[f"{o}_res"] - D[f"{o}_match"]
D.to_csv("reports/tables/reservation_facilities.csv", index=False)
rng = np.random.default_rng(SEED); nat = D.nation.values; u = np.unique(nat); idx = {n: np.where(nat == n)[0] for n in u}
fac("core_tracts", len(D), "core reservation tracts compared"); fac("match_pool", len(pool), "rural non-tribal tracts available as matches")
fac("matched_unique", len({g for m in matches for g in m}), "distinct matched tracts used")
fac("core_density_median", D.density.median(), "core tracts: median residents per km2"); fac("match_density_median", D.match_density.median(), "matches: median of their median density")
for o in OUTC:
    est = D[f"{o}_diff"].mean(); bs = []
    for _ in range(2000):
        s = np.concatenate([idx[n] for n in rng.choice(u, len(u))]); bs.append(D[f"{o}_diff"].values[s].mean())
    fac(f"{o}_res", D[f"{o}_res"].mean(), f"core reservation tracts: mean {o}"); fac(f"{o}_match", D[f"{o}_match"].mean(), f"density-matched rural non-tribal: mean {o}")
    fac(f"{o}_diff", est, f"paired difference (reservation - matched) in {o}")
    fac(f"{o}_lo", np.quantile(bs, .025), "95% CI low (reservation bootstrap)"); fac(f"{o}_hi", np.quantile(bs, .975), "95% CI high")
fac("core_no_emerg_n", int((D.no_emerg_res == 1).sum()), "core tracts with no fire/police/EMS place in Overture")
fac("core_no_emerg_pop", int(D.pop[D.no_emerg_res == 1].sum()), "their residents")
fac.publish()
print(D[[c for c in D if c.endswith(("_res", "_match"))]].mean().round(3).to_string())
print(D[D.no_emerg_res == 1][["GEOID", "nation", "pop"]].to_string())
