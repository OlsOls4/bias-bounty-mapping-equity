#!/usr/bin/env bash
# One-command rebuild of every number, table and figure in both reports, in the required order.
# Run from the project root after:  pip install -r reports/requirements.txt  and  bash reports/get_data.sh
# Deterministic (fixed bootstrap seed 20261014). Total about 6 minutes on one CPU; no step needs more than ~70 s.
set -euo pipefail
mkdir -p reports/cache reports/tables reports/fig
for r in eastern-ok eastern-wa maricopa-az northern-ca south-central-tx; do
  python reports/poi_counts.py "$r"           # place counts per tract            -> reports/cache/<r>-poi.parquet
  python reports/road_km.py "$r"              # road km per tract by class        -> reports/cache/<r>-road.parquet
  python reports/poi_attrs.py "$r"            # place attributes + source mix     -> reports/cache/<r>-poi2.parquet
  python reports/poi_source_address.py "$r"   # address completeness by source    -> reports/cache/<r>-poisrc.parquet
  python reports/bld_lineage.py "$r" --tract  # building source, vintage, attrs   -> reports/cache/<r>-bldtract.parquet, <r>-bldsrc.csv
done
python reports/build_master.py               # one tract table; drops USFS/CarbonPlan count columns -> reports/cache/master.parquet
python reports/v5_method.py                   # submitted v5 scores (must precede analysis.py) -> reports/cache/v5_reproduced.csv
python reports/analysis.py                    # all tables + reports/tables/report_numbers.csv (every cited number)
python reports/weightings.py                  # alternative weightings (Documentation report)
python reports/area_floor.py northern-ca      # 10 m2 ML-footprint floor evidence
python reports/figures.py                     # Figures 1-5
python reports/maps.py                        # Figure 0 (inset maps)
echo "done: see reports/tables/ and reports/fig/"
