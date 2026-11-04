#!/usr/bin/env bash
# Fetch exactly the 7 challenge files per region that the pipeline reads (no credentials needed) into data/<region>/,
# then verify them against reports/DATA_SHA256SUMS.txt. Uses the AWS CLI if installed, otherwise plain curl over HTTPS
# (https://data.source.coop/..., same files). Run from the project root.
# Only Overture extracts, ACS housing, sample submissions, tract polygons and strata tables are fetched;
# none of the removed reference layers (TIGER roads, Microsoft footprints, HIFLD/USGS facilities, CBP) is used.
set -euo pipefail
B=s3://us-west-2.opendata.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge
H=https://data.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge
fetch() {  # fetch <path-in-bucket> <dest-dir>
  if command -v aws >/dev/null 2>&1; then aws s3 cp --no-sign-request "$B/$1" "$2/"
  else curl -fsSL --retry 3 -o "$2/$(basename "$1")" "$H/$1"; fi
}
for r in eastern-ok eastern-wa maricopa-az northern-ca south-central-tx; do
  mkdir -p data/$r
  for f in overture-buildings.parquet overture-pois.parquet overture-roads.parquet census-acs-housing.parquet sample-submission.csv; do
    fetch "reference/$r/$r-$f" "data/$r"
  done
  for f in strata-tract-table.parquet census-tracts.parquet; do
    fetch "strata/$r/$r-$f" "data/$r"
  done
done
sha256sum -c reports/DATA_SHA256SUMS.txt
