"""Stage 1c (per region): POI lineage & attribute completeness per tract, from Overture places only.
Usage: python reports/poi_attrs.py <region>  -> reports/cache/<region>-poi2.parquet"""
import sys, numpy as np, pandas as pd, geopandas as gpd, pyarrow.parquet as pq
r=sys.argv[1]; D=f"data/{r}"
t=gpd.read_parquet(f"{D}/{r}-census-tracts.parquet")[["GEOID","geometry"]]
cols=["sources","websites","phones","addresses","brand","confidence","operating_status","geometry"]
p=gpd.read_parquet(f"{D}/{r}-overture-pois.parquet",columns=cols)
p["src"]=[(s[0]["dataset"] if s is not None and len(s)>0 else "none") for s in p.sources]
p["web"]=p.websites.map(lambda v: v is not None and len(v)>0)
p["phone"]=p.phones.map(lambda v: v is not None and len(v)>0)
p["addr"]=p.addresses.map(lambda v: v is not None and len(v)>0 and bool((v[0].get("freeform") or "").strip()))
p["brand_"]=p.brand.map(lambda b: isinstance(b,dict) and (b.get("wikidata") is not None or (b.get("names") or {}).get("primary") is not None))
p["lowconf"]=p.confidence<0.5
p=p.drop(columns=["sources","websites","phones","addresses","brand"])
j=gpd.sjoin(p,t,predicate="within",how="inner")
g=j.groupby("GEOID").agg(poi_web=("web","mean"),poi_phone=("phone","mean"),poi_addr=("addr","mean"),poi_brand=("brand_","mean"),poi_lowconf=("lowconf","mean"))
sx=pd.crosstab(j.GEOID,j.src).add_prefix("psrc_")
out=t[["GEOID"]].merge(g.join(sx,how="outer").reset_index(),on="GEOID",how="left")
out.to_parquet(f"reports/cache/{r}-poi2.parquet"); print(r,len(p),out.filter(like="psrc_").sum().to_dict())
