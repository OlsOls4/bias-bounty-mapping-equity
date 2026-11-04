# Bias Bounty: Mapping Equity — OlsOls4

Code, tables and figures behind our Zindi "Bias Bounty: Mapping Equity" writeups
(Zindi user **OlsOls4**, leaderboard submission **S9ekqtTA**, v5_rural, public RMSE 0.0831).

- `reports/bias_discovery.pdf` — Bias Discovery report
- `reports/documentation.pdf` — Documentation report
- `reports/tables/report_numbers.csv` — every number cited in the reports, written by script
- `reports/tables/flagged_tracts.csv` — lower-confidence tracts (Recommendation R5)

## Reproduce (from the repository root)

```bash
pip install -r reports/requirements.txt
bash reports/get_data.sh      # public challenge data from source.coop, SHA-256 checked
bash reports/run_all.sh       # ~6 min on one CPU, deterministic
python reports/v5_method.py   # regenerates the leaderboard submission byte-identically
```

The scored submission uses only challenge-provided data. No removed reference layers
(TIGER roads, Microsoft Building Footprints, HIFLD/USGS facilities, CBP) or copies of them are used anywhere.
Licence: MIT.
