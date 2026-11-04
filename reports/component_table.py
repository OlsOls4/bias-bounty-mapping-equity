"""Documentation report, 'How each component was computed': the observable Overture proxies we measured for each
official component, with coverage (tracts where the layer is empty) and how each relates to the submitted v5 score.
The official components cannot be computed: their denominators (TIGER S1100/S1200 km, Microsoft footprint counts,
USGS/HIFLD facility counts, CBP establishments) were removed from the package and are prohibited.
Run from the project root after build_master.py and v5_method.py.
Writes reports/tables/component_proxies.csv and reports/tables/no_overture_counts.csv."""
import numpy as np, pandas as pd

M = pd.read_parquet("reports/cache/master.parquet")
v5 = pd.read_csv("reports/cache/v5_reproduced.csv", dtype={"GEOID": str}).set_index("GEOID").coverage_gap_score
M["v5"] = M.GEOID.map(v5)
M["km_all"] = M.km_major + M.km_tert + M.km_minor
M["n_facility"] = M.n_fire + M.n_ems + M.n_school
M["sh_ml"] = (M.b_ms + M.b_gob) / M.n_bld.replace(0, np.nan)
M["major_km_per_km2"] = M.km_major / M.km2.replace(0, np.nan)          # km2 = ALAND / 1e6 (land area)
pop = M.pop_total.fillna(0) > 0
rural = M.ur_class.eq("Rural")

P = [  # component, proxy column, plain description
    ("transport_gap", "km_major", "Overture motorway+trunk+primary+secondary km in tract (the official numerator)"),
    ("transport_gap", "km_motorway", "of which motorway km"),
    ("transport_gap", "km_primary", "of which primary km"),
    ("transport_gap", "km_secondary", "of which secondary km"),
    ("transport_gap", "major_km_per_km2", "major-road km per km2 of land (ALAND)"),
    ("transport_gap", "km_all", "all Overture road km (major+tertiary+minor)"),
    ("building_gap", "n_bld", "Overture building count (the official numerator)"),
    ("building_gap", "sh_osm", "share of footprints from OpenStreetMap (human-mapped)"),
    ("building_gap", "sh_ms", "share from Microsoft ML (same lineage as the removed reference)"),
    ("building_gap", "sh_gob", "share from Google Open Buildings ML"),
    ("building_gap", "bld_per_hu", "buildings per ACS housing unit (sanity check only, as in the official rule)"),
    ("poi_gap", "n_fire", "places with primary category fire_department"),
    ("poi_gap", "n_ems", "places with primary category ambulance_and_ems_services"),
    ("poi_gap", "n_school", "places in the six README school categories"),
    ("poi_gap", "n_poi", "all Overture places (official numerator of the establishments half)"),
    ("poi_gap", "poi_per_1k", "places per 1,000 residents"),
    ("poi_gap", "poi_addr", "share of places with a street address"),
]
rows = []
for comp, c, desc in P:
    x = M[c]
    rows.append({
        "component": comp, "proxy": c, "description": desc,
        "tracts_zero": int((x == 0).sum()), "tracts_undefined": int(x.isna().sum()),
        "median_populated": round(float(x[pop].median()), 3),
        "rural_median": round(float(x[pop & rural].median()), 3), "urban_median": round(float(x[pop & ~rural].median()), 3),
        "spearman_with_v5": round(float(x[pop].corr(M.v5[pop], method="spearman")), 2),
    })
T = pd.DataFrame(rows)
T.to_csv("reports/tables/component_proxies.csv", index=False)
print(T.drop(columns="description").to_string(index=False))

N = pd.DataFrame([
    ("buildings", int((M.n_bld == 0).sum()), int(((M.n_bld == 0) & pop).sum())),
    ("places (any)", int((M.n_poi == 0).sum()), int(((M.n_poi == 0) & pop).sum())),
    ("roads (any class)", int((M.km_all == 0).sum()), int(((M.km_all == 0) & pop).sum())),
    ("major roads (motorway-secondary)", int((M.km_major == 0).sum()), int(((M.km_major == 0) & pop).sum())),
    ("fire_department places", int((M.n_fire == 0).sum()), int(((M.n_fire == 0) & pop).sum())),
    ("EMS places", int((M.n_ems == 0).sum()), int(((M.n_ems == 0) & pop).sum())),
    ("school places", int((M.n_school == 0).sum()), int(((M.n_school == 0) & pop).sum())),
    ("no fire, EMS or school place", int((M.n_facility == 0).sum()), int(((M.n_facility == 0) & pop).sum())),
    ("all three layers empty", int(((M.n_bld == 0) & (M.n_poi == 0) & (M.km_all == 0)).sum()), int(((M.n_bld == 0) & (M.n_poi == 0) & (M.km_all == 0) & pop).sum())),
], columns=["layer", "tracts_with_none", "of_which_populated"])
N.to_csv("reports/tables/no_overture_counts.csv", index=False)
print(N.to_string(index=False))
print("submitted columns:", open("work/subs/v5_rural.csv").readline().strip() if __import__("os").path.exists("work/subs/v5_rural.csv") else "n/a")
