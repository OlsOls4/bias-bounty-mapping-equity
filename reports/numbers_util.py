"""Helper for the round-3 scripts: add (or replace) a block of keys in reports/tables/report_numbers.csv without touching
the keys written by analysis.py. Each script owns one key prefix; re-running a script replaces only its own rows."""
import pandas as pd

PATH = "reports/tables/report_numbers.csv"


class Numbers:
    def __init__(self, prefix):
        self.prefix, self.rows = prefix, []

    def __call__(self, key, value, desc):
        v = value.item() if hasattr(value, "item") else value
        self.rows.append({"key": f"{self.prefix}{key}", "value": v, "description": desc}); return v

    def publish(self):
        old = pd.read_csv(PATH)
        old = old[~old.key.astype(str).str.startswith(self.prefix)]
        pd.concat([old, pd.DataFrame(self.rows)]).to_csv(PATH, index=False)
        print(f"{len(self.rows)} numbers written under '{self.prefix}'")
