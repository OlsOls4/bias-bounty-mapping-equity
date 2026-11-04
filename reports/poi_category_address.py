"""Stage 1e (per region): place counts and street-address counts per tract x Overture primary category x Meta/other source.
Used to show WHICH kinds of places lack an address on reservations (clinics, schools, government/community offices,
fire/police, stores and fuel used as relief points). Same address test as poi_attrs.py (first address has a non-empty
freeform string). Reads the place file in row groups so the large Texas file fits in ~1 GB of memory.
Usage: python reports/poi_category_address.py <region> -> reports/cache/<region>-poicat.parquet"""
import sys, pandas as pd, geopandas as gpd, pyarrow.parquet as pq, shapely
r = sys.argv[1]; D = f"data/{r}"
t = gpd.read_parquet(f"{D}/{r}-census-tracts.parquet")[["GEOID", "geometry"]]
f = pq.ParquetFile(f"{D}/{r}-overture-pois.parquet")
parts = []
for i in range(f.metadata.num_row_groups):
    b = f.read_row_group(i, columns=["categories", "sources", "addresses", "geometry"]).to_pydict()
    cat = [(c or {}).get("primary") or "(none)" for c in b["categories"]]
    meta = [bool(s) and s[0]["dataset"] == "meta" for s in b["sources"]]
    addr = [bool(a) and bool(((a[0] or {}).get("freeform") or "").strip()) for a in b["addresses"]]
    g = gpd.GeoDataFrame({"cat": cat, "meta": meta, "addr": addr}, geometry=shapely.from_wkb(b["geometry"]), crs=t.crs)
    j = gpd.sjoin(g, t, predicate="within", how="inner")
    parts.append(j.groupby(["GEOID", "cat", "meta"]).agg(n=("addr", "size"), n_addr=("addr", "sum")).reset_index())
    del b, g, j
g = pd.concat(parts).groupby(["GEOID", "cat", "meta"], as_index=False)[["n", "n_addr"]].sum()
g.to_parquet(f"reports/cache/{r}-poicat.parquet"); print(r, f.metadata.num_rows, int(g.n.sum()), int(g.n_addr.sum()))
