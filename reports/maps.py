"""Figure 0: three inset maps drawn from the challenge's own tract polygons (data/<region>/<region>-census-tracts.parquet)
joined to reports/cache/master.parquet. No basemap or external geometry is used.
 (a) South Texas border seam: OSM share of footprints; seam counties outlined
 (b) Arizona: share of places with a street address; reservation / trust-land tracts outlined
 (c) Hidalgo County, TX: OSM share; urban tracts with <5% OSM outlined
-> reports/fig/fig0_maps.png"""
import os, sys, numpy as np, pandas as pd, geopandas as gpd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from common import *
plt.rcParams.update({"font.size": 7})
M, P = load()
def tracts(r):
    g = gpd.read_parquet(f"data/{r}/{r}-census-tracts.parquet")[["GEOID", "geometry"]].to_crs(5070)
    g["geometry"] = g.geometry.simplify(80)
    return g.merge(M[["GEOID", "sh_osm", "poi_addr", "ur_class", "tribal_legal", "aiannh_name", "pop_total"]], on="GEOID", how="left")
tx, az = tracts("south-central-tx"), tracts("maricopa-az")
tx["c5"] = tx.GEOID.str[:5]
fig, axs = plt.subplots(2, 2, figsize=(7.8, 7.6), gridspec_kw={"hspace": 0.12, "wspace": 0.04, "left": 0.01, "right": 0.99, "top": 0.94, "bottom": 0.03})
axA, axB, axC, axD = axs.ravel()
kw = dict(cmap="cividis", vmin=0, vmax=1, linewidth=0)
# (a) South Texas seam + neighbouring counties
seam = tx[tx.c5.isin(TX_BORDER)]
x0, y0, x1, y1 = seam.total_bounds; pad = 40_000
A = tx.cx[x0-pad:x1+pad, y0-pad:y1+pad]
A.plot(column="sh_osm", ax=axA, missing_kwds={"color": "lightgrey"}, **kw)
co = seam.dissolve("c5"); co.boundary.plot(ax=axA, color="#D55E00", linewidth=0.9)
for c5, rr in co.iterrows():
    p = rr.geometry.representative_point(); dx = -45_000 if c5 == "48427" else 0
    axA.text(p.x + dx, p.y, TX_BORDER[c5], fontsize=6, ha="center", color="white",
                                                     bbox=dict(boxstyle="round,pad=0.15", fc="#D55E00", ec="none", alpha=0.85))
axA.set_xlim(x0-pad, x1+pad); axA.set_ylim(y0-pad, y1+pad); axA.set_axis_off()
axA.set_title("(a) South Texas border seam\norange outline = the 9 seam counties; colour = OSM share", fontsize=7, loc="left")
# (b) Arizona: address share, reservations outlined
az.plot(column="poi_addr", ax=axB, cmap="cividis", vmin=0.4, vmax=1, linewidth=0, missing_kwds={"color": "lightgrey"})
res = az[az.tribal_legal.fillna(False).astype(bool)]
res.dissolve("aiannh_name").boundary.plot(ax=axB, color="#D55E00", linewidth=0.7)
LBL = {"Navajo Nation Reservation": "Navajo Nation", "Tohono O'odham Nation Reservation": "Tohono O'odham Nation",
       "San Carlos Reservation": "San Carlos Apache", "Fort Apache Reservation": "White Mountain Apache\n(Fort Apache)", "Zuni Reservation": "Pueblo of Zuni"}
for nm, lab in LBL.items():
    g = res[res.aiannh_name == nm]
    if len(g):
        p = g.dissolve().geometry.iloc[0].representative_point()
        axB.annotate(lab, (p.x, p.y), fontsize=5.8, ha="center", color="black", bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="#D55E00", lw=0.5, alpha=0.9))
axB.set_axis_off()
axB.set_title("(b) Arizona region\norange outline = reservation / trust land; colour = places with address", fontsize=7, loc="left")
# (c) Hidalgo County
H = tx[tx.c5 == "48215"]
H.plot(column="sh_osm", ax=axC, missing_kwds={"color": "lightgrey"}, **kw)
ml = H[(H.ur_class == "Urban") & (H.sh_osm < 0.05) & (H.pop_total > 0)]
ml.boundary.plot(ax=axC, color="#D55E00", linewidth=0.5)
ux0, uy0, ux1, uy1 = H[H.ur_class == "Urban"].total_bounds; axC.set_xlim(ux0-3000, ux1+3000); axC.set_ylim(uy0-3000, uy1+3000)
axC.set_axis_off()
nU = int(((H.ur_class == "Urban") & (H.pop_total > 0)).sum())
axC.set_title(f"(c) Hidalgo County, TX (urban core)\n{len(ml)} of {nU} urban tracts below 5% OSM (orange outline)", fontsize=7, loc="left")
axD.set_axis_off()
c1 = axD.inset_axes([0.08, 0.62, 0.84, 0.07]); c2 = axD.inset_axes([0.08, 0.30, 0.84, 0.07])
cb = fig.colorbar(plt.cm.ScalarMappable(cmap="cividis", norm=plt.Normalize(0, 1)), cax=c1, orientation="horizontal")
cb.set_ticks([0, 0.25, 0.5, 0.75, 1]); cb.set_ticklabels(["0%", "25%", "50%", "75%", "100%"])
c1.set_title("Panels (a), (c): share of building footprints from OpenStreetMap\n(0% = every footprint machine-detected)", fontsize=7)
cb = fig.colorbar(plt.cm.ScalarMappable(cmap="cividis", norm=plt.Normalize(0.4, 1)), cax=c2, orientation="horizontal")
cb.set_ticks([0.4, 0.6, 0.8, 1.0]); cb.set_ticklabels(["40% or less", "60%", "80%", "100%"])
c2.set_title("Panel (b): share of Overture places with a street address", fontsize=7)
axD.text(0.02, 0.05, "Tract polygons and attributes as shipped with the challenge; \nOverture 2026-08-19.0. Grey = no value.\nAlbers equal-area projection (EPSG:5070).", fontsize=6, transform=axD.transAxes)
plt.savefig("reports/fig/fig0_maps.png", dpi=200); plt.close(); print("maps written", len(ml))
