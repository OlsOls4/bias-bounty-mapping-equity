"""Stage 1a (per region): Overture place counts per tract (all places; fire / EMS / school categories as named in the
challenge README). Usage: python reports/poi_counts.py <region>  -> reports/cache/<region>-poi.parquet"""
import geopandas as gpd, pandas as pd, pyarrow.parquet as pq, sys
r=sys.argv[1]; D=f"data/{r}"
t=gpd.read_parquet(f"{D}/{r}-census-tracts.parquet")[["GEOID","geometry"]]
p=gpd.read_parquet(f"{D}/{r}-overture-pois.parquet",columns=["geometry","categories","confidence"])
p["cat"]=p["categories"].map(lambda c: c.get("primary") if isinstance(c,dict) else None)
p=p.drop(columns="categories")
j=gpd.sjoin(p,t,predicate="within",how="inner")
S={'elementary_school','middle_school','high_school','school','private_school','public_school'}
j["fire"]=j.cat.eq("fire_department"); j["ems"]=j.cat.eq("ambulance_and_ems_services"); j["school"]=j.cat.isin(S); j["hi"]=j.confidence>=0.7
g=j.groupby("GEOID").agg(n_poi=("cat","size"),n_fire=("fire","sum"),n_ems=("ems","sum"),n_school=("school","sum"),n_poi_hi=("hi","sum"),conf_mean=("confidence","mean")).reset_index()
g=t[["GEOID"]].merge(g,on="GEOID",how="left").fillna({"n_poi":0,"n_fire":0,"n_ems":0,"n_school":0,"n_poi_hi":0})
g.to_parquet(f"reports/cache/{r}-poi.parquet"); print(r,len(p),g[["n_poi","n_fire","n_ems","n_school"]].sum().to_dict())
