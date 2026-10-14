#!/usr/bin/env bash
# Fetch exactly the 7 challenge files per region that the pipeline reads (no credentials needed) into data/<region>/,
# then verify them against reports/DATA_SHA256SUMS.txt. Requires the AWS CLI. Run from the project root.
# Only Overture extracts, ACS housing, sample submissions, tract polygons and strata tables are fetched;
# none of the removed reference layers (TIGER roads, Microsoft footprints, HIFLD/USGS facilities, CBP) is used.
set -euo pipefail
B=s3://us-west-2.opendata.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge
for r in eastern-ok eastern-wa maricopa-az northern-ca south-central-tx; do
  mkdir -p data/$r
  for f in overture-buildings.parquet overture-pois.parquet overture-roads.parquet census-acs-housing.parquet sample-submission.csv; do
    aws s3 cp --no-sign-request "$B/reference/$r/$r-$f" "data/$r/"
  done
  for f in strata-tract-table.parquet census-tracts.parquet; do
    aws s3 cp --no-sign-request "$B/strata/$r/$r-$f" "data/$r/"
  done
done
sha256sum -c reports/DATA_SHA256SUMS.txt
