"""Flag lower-confidence tracts for Recommendation R5 -> reports/tables/flagged_tracts.csv"""
import pandas as pd
m = pd.read_parquet('reports/cache/master.parquet')
m = m[m.pop_total > 0].copy()
seam_cty = {'48061','48215','48427','48505','48479','48323','48271','48465','48443'}
m['cty'] = m.GEOID.str[:5]
reasons = []
for _, r in m.iterrows():
    f = []
    if pd.notna(r.sh_osm) and r.sh_osm < 0.05: f.append('<5% human-mapped (OSM) footprints')
    if r.tribal_legal == 1 and pd.notna(r.poi_addr) and r.poi_addr < 0.70: f.append('reservation tract, <70% places addressed')
    if r.cty in seam_cty: f.append('South Texas border seam')
    reasons.append('; '.join(f))
m['flag_reason'] = reasons
out = m[m.flag_reason != ''][['GEOID','region','COUNTYFP','aiannh_name','pop_total','sh_osm','sh_gob','poi_addr','svi_overall','flag_reason']]
out = out.rename(columns={'pop_total':'residents','sh_osm':'osm_share','sh_gob':'google_share','poi_addr':'places_with_address_share'})
out.sort_values(['region','GEOID']).to_csv('reports/tables/flagged_tracts.csv', index=False)
print(len(out), 'flagged tracts')
