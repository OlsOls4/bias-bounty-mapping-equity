"""Figures 1-5 for the Bias Discovery report (maps are in maps.py). Run from the project root after analysis.py.
Colour-blind-safe Okabe-Ito palette. -> reports/fig/fig1..fig5*.png"""
import os, sys, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
sys.path.insert(0, os.path.dirname(__file__))
from common import *
os.makedirs("reports/fig", exist_ok=True)
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
OI = {"blue": "#0072B2", "orange": "#E69F00", "verm": "#D55E00", "green": "#009E73", "sky": "#56B4E9", "grey": "#999999", "purple": "#CC79A7"}
M, P = load()
SRC = "Source: Overture Maps 2026-08-19.0 extracts shipped with the challenge."

# ---------- Fig 1: lineage by region x urban/rural
L = pd.read_csv("reports/tables/lineage_region_urban.csv")
REG = {"eastern-ok": "E. OK", "eastern-wa": "E. WA", "maricopa-az": "AZ", "northern-ca": "N. CA", "south-central-tx": "S.-C. TX"}
fmt = lambda n: f"{n/1e6:.1f}M" if n >= 1e6 else f"{n/1e3:.0f}k"
lab = [f"{REG[r]}\n{u}\n{fmt(b)} bldgs" for r, u, b in zip(L.region, L.ur_class, L.buildings)]
fig, ax = plt.subplots(figsize=(7.6, 3.6)); bot = np.zeros(len(L)); x = np.arange(len(L))
for col, name, c in [("OSM", "OpenStreetMap (human-mapped)", OI["blue"]), ("Esri", "Esri Community Maps (human-mapped)", OI["sky"]),
                     ("Microsoft ML", "Microsoft (machine-detected)", OI["orange"]), ("Google OB", "Google Open Buildings (machine-detected)", OI["verm"])]:
    ax.bar(x, 100*L[col], bottom=bot, color=c, label=name, width=0.75); bot += 100*L[col].values
for i, v in enumerate(100*L.OSM): ax.text(i, v/2, f"{v:.0f}%", ha="center", va="center", color="white", fontsize=7, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=6.5); ax.set_ylabel("% of Overture building footprints"); ax.set_ylim(0, 100)
ax.legend(fontsize=6.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.30), frameon=False)
ax.set_title("Rural tracts are mapped mostly by machine detection, not by people", fontsize=9, loc="left")
plt.tight_layout(); plt.savefig("reports/fig/fig1_building_lineage.png", dpi=200); plt.close()

# ---------- Fig 2: hexbin OSM share vs density
fig, ax = plt.subplots(figsize=(6.4, 3.9))
hb = ax.hexbin(P.log10_density, 100*P.sh_osm, gridsize=(45, 25), cmap="viridis", norm=LogNorm(), mincnt=1, linewidths=0)
cb = plt.colorbar(hb, ax=ax, pad=0.01); cb.set_label("tracts per hexagon", fontsize=7)
ax.axhline(5, ls="--", lw=0.9, color="k"); ax.axvline(3, ls=":", lw=0.9, color="k")
ax.set_xticks(range(0, 5)); ax.set_xticklabels(["1", "10", "100", "1,000", "10,000"]); ax.set_xlim(-0.5, 4.6)
ax.set_xlabel("residents per km² (log scale)"); ax.set_ylabel("% of footprints from OpenStreetMap")
u = P[P.ur_class.eq("Urban") & (P.sh_osm < 0.05)]
ax.annotate(f"{len(u)} urban tracts below 5% OSM\n({u.pop_total.sum()/1e6:.1f}M residents; {int((u.county5=='48215').sum())} in Hidalgo Co., TX)",
            xy=(3.3, 2), xytext=(-0.3, 22), fontsize=7, arrowprops=dict(arrowstyle="->", lw=0.8),
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.5", lw=0.5))
ax.text(3.03, 97, "1,000 / km²", fontsize=6.5, va="top")
ax.set_title(f"Human mapping is split in two, even in dense places (n = {len(P):,} populated tracts)", fontsize=9, loc="left")
plt.tight_layout(); plt.savefig("reports/fig/fig2_osm_vs_density.png", dpi=200); plt.close()

# ---------- Fig 3: address completeness by stratum (dot plot + gap with 95% CI)
S = strata(P); cl = P.county5.values
rows = []
order = ["Rural", "Tribal (any overlap)", "High SVI (>=0.75)", "High CVI (top 25%)", "Winter drought (top 25%)", "Wildfire hazard (WHP top 25%)",
         "Summer heat (top 25%)", "Hazard + high SVI", "N1 Reservation / trust land", "N2b South Texas border seam (9 counties)",
         "N3 Minority-majority (SVI minority >=0.90)", "N4 Weather-station desert (>10 km)", "N5 Housing/transport burden (SVI theme 4 >=0.75)",
         "N6 Burned since 2018 (>=30% of land)"]
nice = {"Rural": "Rural", "Tribal (any overlap)": "Overlaps tribal land", "High SVI (>=0.75)": "High social vulnerability",
        "High CVI (top 25%)": "High climate vulnerability", "Winter drought (top 25%)": "Winter drought", "Wildfire hazard (WHP top 25%)": "Wildfire hazard",
        "Summer heat (top 25%)": "Summer heat", "Hazard + high SVI": "Hazard + high SVI", "N1 Reservation / trust land": "N1 Reservation / trust land",
        "N2b South Texas border seam (9 counties)": "N2 South Texas border seam", "N3 Minority-majority (SVI minority >=0.90)": "N3 Minority-majority",
        "N4 Weather-station desert (>10 km)": "N4 Weather-station desert", "N5 Housing/transport burden (SVI theme 4 >=0.75)": "N5 Housing/transport burden",
        "N6 Burned since 2018 (>=30% of land)": "N6 Burned since 2018"}
for s in order:
    r = cluster_boot_ratio(P.poi_addr.values, np.ones(len(P)), S[s].values.astype(float), cl); rows.append({"s": nice[s], **r})
az = P.region.eq("maricopa-az"); azs = P.reservation.astype(float).where(az)
r = cluster_boot_ratio(P.poi_addr.values, np.ones(len(P)), azs.values, cl); rows.append({"s": "Arizona reservations\n(vs rest of AZ region)", **r})
D = pd.DataFrame(rows).iloc[::-1].reset_index(drop=True)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.8, 4.6), gridspec_kw={"width_ratios": [1.25, 1]}, sharey=True)
y = np.arange(len(D))
for i, rr in D.iterrows():
    hl = rr.s.startswith(("N1", "Arizona", "N6"))
    a1.plot([rr.rest*100, rr.in_*100], [i, i], color=OI["grey"], lw=1)
    a1.scatter(rr.rest*100, i, color=OI["grey"], s=18, zorder=3); a1.scatter(rr.in_*100, i, color=OI["verm"] if hl else OI["blue"], s=22, zorder=3)
    a2.barh(i, rr["diff"]*100, color=OI["verm"] if hl else OI["blue"], height=0.6)
    a2.plot([rr.diff_lo*100, rr.diff_hi*100], [i, i], color="k", lw=0.8)
    a2.text(3.0, i, f"{rr['diff']*100:+.1f}", va="center", ha="left", fontsize=6.5)
a1.set_yticks(y); a1.set_yticklabels([f"{s}  (n={n:,})" for s, n in zip(D.s, D.n_in)], fontsize=6.5)
a1.set_xlim(60, 100); a1.set_xlabel("% of places with a street address\n(axis starts at 60%; grey = rest of study area)")
a2.axvline(0, color="k", lw=0.8); a2.set_xlim(-30, 8); a2.set_xlabel("gap in percentage points (zero-based)\nlines = 95% county-cluster bootstrap CI")
a1.scatter([], [], color=OI["blue"], label="in stratum"); a1.scatter([], [], color=OI["grey"], label="rest"); a1.legend(fontsize=6.5, loc="lower left", frameon=False)
fig.suptitle("Places on reservations and recently burned land are the ones missing street addresses", fontsize=9, x=0.02, ha="left")
plt.tight_layout(); plt.savefig("reports/fig/fig3_address_by_stratum.png", dpi=200); plt.close()

# ---------- Fig 4: South Texas border seam vs Arizona contrast (two panels, real units)
B = pd.read_csv("reports/tables/border_seam.csv")
B["lab"] = B.zone.map({"TX seam": "TX\nseam", "TX rest": "TX\nrest", "AZ border": "AZ\nborder", "AZ rest": "AZ\nrest"}) + "\n" + B.ur_class.str.lower()
B = B.set_index(["zone", "ur_class"]).loc[[("TX seam", "Rural"), ("TX seam", "Urban"), ("TX rest", "Rural"), ("TX rest", "Urban"),
                                           ("AZ border", "Rural"), ("AZ border", "Urban"), ("AZ rest", "Rural"), ("AZ rest", "Urban")]].reset_index()
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.8, 3.4))
x = np.arange(len(B)); bot = np.zeros(len(B))
for col, name, c in [("osm", "OpenStreetMap", OI["blue"]), ("esri", "Esri", OI["sky"]), ("ms", "Microsoft ML", OI["orange"]), ("gob", "Google ML", OI["verm"])]:
    a1.bar(x, 100*B[col], bottom=bot, color=c, label=name, width=0.75); bot += 100*B[col].values
a1.set_xticks(x); a1.set_xticklabels([f"{l}\nn={int(t):,}" for l, t in zip(B.lab, B.tracts)], fontsize=6.3, rotation=0)
a1.set_ylabel("% of building footprints"); a1.set_ylim(0, 100); a1.legend(fontsize=6, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.30), frameon=False)
a1.set_title("(a) Who drew the buildings", fontsize=8, loc="left")
cols = [OI["verm"] if z == "TX seam" else OI["grey"] for z in B.zone]
a2.bar(x, B.places_per_1k, color=cols, width=0.7)
for i, v in enumerate(B.places_per_1k): a2.text(i, v + 0.8, f"{v:.0f}", ha="center", fontsize=6.5)
a2.set_xticks(x); a2.set_xticklabels([l for l in B.lab], fontsize=6.3); a2.set_ylabel("places per 1,000 residents (pooled)")
a2.set_title("(b) Overture places per 1,000 residents", fontsize=8, loc="left")
fig.suptitle("In South Texas border counties Google's ML layer stands in for human mapping.\nArizona's border counties, taken together, look like the rest of Arizona.", fontsize=8, x=0.02, ha="left")
plt.tight_layout(); plt.savefig("reports/fig/fig4_border_seam.png", dpi=200); plt.close()

# ---------- Fig 5: buildings per housing unit vs OSM share (benchmark circularity)
H = P[(P.housing_units >= 50) & (P.n_bld > 0) & P.ur_class.eq("Urban")].copy()
H["dq"] = pd.qcut(H.log10_density, 5, labels=["lowest", "2", "3", "4", "highest"])
H["ob"] = pd.cut(H.sh_osm, [-0.01, 0.05, 0.5, 0.95, 1.0], labels=["<5%", "5-50%", "50-95%", ">95%"])
T = H.groupby(["dq", "ob"], observed=True).bld_per_hu.median().unstack()
fig, ax = plt.subplots(figsize=(6.4, 3.2)); w = 0.2
for k, (c, col) in enumerate(zip(T.columns, [OI["orange"], "#F0C060", OI["sky"], OI["blue"]])):
    ax.bar(np.arange(len(T)) + (k-1.5)*w, T[c], w, color=col, label=f"OSM share {c}")
ax.axhline(1, color="k", lw=0.6, ls=":")
ax.set_xticks(range(len(T))); ax.set_xticklabels(["Q1 (least dense)", "Q2", "Q3", "Q4", "Q5 (densest)"]); ax.set_ylabel("median buildings per housing unit"); ax.set_xlabel("population-density quintile (urban tracts)")
ax.legend(fontsize=6.5, ncol=4, loc="upper right", frameon=False)
ax.set_title(f"Machine-filled urban tracts carry more footprints per home at every density (n = {len(H):,})", fontsize=8.5, loc="left")
ax.set_ylim(0, 1.6)
plt.tight_layout(); plt.savefig("reports/fig/fig5_bld_per_hu.png", dpi=200); plt.close()
print("figures written")
