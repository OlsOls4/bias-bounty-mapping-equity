"""Footprint-area histogram by upstream source (evidence for the documented 10 m2 floor on ML footprints), northern-ca.
Area computed in EPSG:5070 (equal-area). Run from project root."""
import numpy as np, pandas as pd, pyarrow.parquet as pq, shapely, pyproj, sys
r=sys.argv[1] if len(sys.argv)>1 else "northern-ca"
f=pq.ParquetFile(f"data/{r}/{r}-overture-buildings.parquet")
tr=pyproj.Transformer.from_crs(4326,5070,always_xy=True)
out=[]
for b in f.iter_batches(batch_size=300000,columns=["sources","geometry"]):
    src=[(x[0]["dataset"] if x else "none") for x in b.column("sources").to_pylist()]
    g=shapely.from_wkb(b.column("geometry").to_numpy(zero_copy_only=False))
    g=shapely.transform(g,lambda xy: np.column_stack(tr.transform(xy[:,0],xy[:,1])))
    out.append(pd.DataFrame({"src":src,"area":shapely.area(g)}))
D=pd.concat(out,ignore_index=True)
bins=[0,2,4,6,8,10,12,14,16,18,20,25,30,1e12]
H=pd.crosstab(pd.cut(D.area,bins,right=False),D.src)
print(H.to_string())
S=D.groupby("src").area.agg(n="size",min="min",p01=lambda a:np.quantile(a,0.001),lt10=lambda a:(a<10).mean(),lt15=lambda a:(a<15).mean())
print(S.to_string())
H.to_csv(f"reports/tables/footprint_area_hist_{r}.csv"); S.to_csv(f"reports/tables/footprint_area_summary_{r}.csv")
