"""Stage 1e (per region): Overture building attribute completeness and source vintage by upstream source.
Region-level summary -> reports/cache/<region>-bldsrc.csv ; with --tract also per-tract year/attr stats
(each footprint is assigned to the tract containing the centre of its bounding box) -> reports/cache/<region>-bldtract.parquet"""
import sys, re, numpy as np, pandas as pd, pyarrow.parquet as pq
r=sys.argv[1]; tract="--tract" in sys.argv
f=pq.ParquetFile(f"data/{r}/{r}-overture-buildings.parquet")
cols=["sources","height","num_floors","class","names"]+(["bbox"] if tract else [])
agg=[]; tparts=[]
if tract:
    import geopandas as gpd
    t=gpd.read_parquet(f"data/{r}/{r}-census-tracts.parquet")[["GEOID","geometry"]]
yr=re.compile(r"(\d{4})-\d\d-\d\d")
for b in f.iter_batches(batch_size=400000,columns=cols):
    s=b.column("sources").to_pylist()
    src=[(x[0]["dataset"] if x else "none") for x in s]
    ut=[(x[0].get("update_time") if x else None) for x in s]
    y=[(int(m.group(1)) if (u and (m:=yr.search(str(u)))) else np.nan) for u in ut]
    d=pd.DataFrame({"src":src,"year":y,
        "has_h":pd.notna(b.column("height").to_numpy(zero_copy_only=False)),
        "has_fl":pd.notna(b.column("num_floors").to_numpy(zero_copy_only=False)),
        "has_cls":[c is not None for c in b.column("class").to_pylist()],
        "has_name":[n is not None and n.get("primary") is not None for n in b.column("names").to_pylist()]})
    agg.append(d.groupby("src").agg(n=("year","size"),year_med=("year","median"),h=("has_h","sum"),fl=("has_fl","sum"),cls=("has_cls","sum"),name=("has_name","sum")).reset_index())
    if tract:
        bb=b.column("bbox").to_pandas()
        d["x"]=[(q["xmin"]+q["xmax"])/2 for q in bb]; d["y"]=[(q["ymin"]+q["ymax"])/2 for q in bb]
        g=gpd.GeoDataFrame(d,geometry=gpd.points_from_xy(d.x,d.y),crs=t.crs)
        j=gpd.sjoin(g,t,predicate="within",how="inner")
        j["any_attr"]=j.has_h|j.has_cls|j.has_name|j.has_fl
        j["y2020p"]=j.year>=2020
        j["sem"]=j.has_cls|j.has_name|j.has_fl
        tparts.append(j.groupby(["GEOID","src"]).agg(n=("year","size"),yr_sum=("year","sum"),attr=("any_attr","sum"),new=("y2020p","sum"),sem=("sem","sum")).reset_index())
A=pd.concat(agg).groupby("src").agg(n=("n","sum"),year_med=("year_med","median"),h=("h","sum"),fl=("fl","sum"),cls=("cls","sum"),name=("name","sum"))
for c in ["h","fl","cls","name"]: A[c+"_pct"]=(100*A[c]/A.n).round(1)
A["region"]=r; A.to_csv(f"reports/cache/{r}-bldsrc.csv"); print(A)
if tract:
    T=pd.concat(tparts).groupby(["GEOID","src"]).sum().reset_index(); T.to_parquet(f"reports/cache/{r}-bldtract.parquet"); print(T.shape)
