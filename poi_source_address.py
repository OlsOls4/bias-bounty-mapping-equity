"""Stage 1d (per region): place counts and street-address counts per tract AND upstream place source
(sources[0].dataset: meta, microsoft, foursquare, ...). Used to test whether the reservation address gap is a
place-provider effect. Usage: python reports/poi_source_address.py <region> -> reports/cache/<region>-poisrc.parquet"""
import sys, pandas as pd, geopandas as gpd
r = sys.argv[1]; D = f"data/{r}"
t = gpd.read_parquet(f"{D}/{r}-census-tracts.parquet")[["GEOID", "geometry"]]
p = gpd.read_parquet(f"{D}/{r}-overture-pois.parquet", columns=["sources", "addresses", "geometry"])
p["src"] = [(s[0]["dataset"] if s is not None and len(s) > 0 else "none") for s in p.sources]
p["addr"] = p.addresses.map(lambda v: v is not None and len(v) > 0 and bool((v[0].get("freeform") or "").strip()))
p = p.drop(columns=["sources", "addresses"])
j = gpd.sjoin(p, t, predicate="within", how="inner")
g = j.groupby(["GEOID", "src"]).agg(n=("addr", "size"), n_addr=("addr", "sum")).reset_index()
g.to_parquet(f"reports/cache/{r}-poisrc.parquet"); print(r, g.groupby("src")[["n", "n_addr"]].sum().to_dict())
