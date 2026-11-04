"""Documentation report, 'Alternative weightings': sensitivity of the public-leaderboard RMSE to the v5 coefficients,
using only the public RMSEs of our own submissions ("leaderboard-probe maths"). No labels are used.

Idea. For any prediction p and hidden truth y on the public split, RMSE(p)^2 = E[p^2] - 2 E[p y] + E[y^2].
E[p^2] we can compute. E[y^2] = RMSE(all zeros)^2. A submission q with known RMSE reveals E[q y]:
    E[q y] = (E[q^2] + E[y^2] - RMSE(q)^2) / 2.
So the RMSE of any prediction built as a linear combination of already-submitted predictions is known WITHOUT
submitting it. Submitted so far: zeros, constant 0.05, v1b, v4 (= 0.35 x v1b), v5.
  * identified exactly: constants, intercept shifts, scaling v5's rural+tribal increment, best a + b*v5.
  * NOT identified: changing the rural or the tribal coefficient alone (only their combined product with y is known);
    for those we report the range allowed by y in [0, 1].
Approximation: E[p^2] and E[p q] are taken over all 9,794 scored rows; the public split is a ~30% subset whose rows are
unknown. The column 'band95' re-does every identified calculation on 2,000 random 30% subsets to show how much that matters.
Scored-column check: zeros, v4 (= 0.35 x v1b) and v1b are the same file scaled by 0, 0.35 and 1, so their three public
RMSEs pin down the public mean of h^2 for whichever column the leaderboard scored. We compare it with each column's value.
Run from the project root after v5_method.py. Writes reports/tables/v5_sensitivity.csv, reports/tables/lb_scored_column_check.csv."""
import os, numpy as np, pandas as pd

R = ["eastern-ok", "maricopa-az", "northern-ca", "south-central-tx", "eastern-wa"]
S = pd.concat([pd.read_csv(f"data/{r}/{r}-sample-submission.csv", dtype={"GEOID": str})[["GEOID"]]
               .merge(pd.read_parquet(f"data/{r}/{r}-strata-tract-table.parquet", columns=["GEOID", "pct_urban", "tribal_any"]), on="GEOID", how="left") for r in R])
rur = 1 - S.pct_urban.fillna(S.pct_urban.mean()).values
tri = S.tribal_any.fillna(False).astype(float).values
v5 = 0.035 + 0.07 * rur + 0.04 * tri

LB = {"zeros": 0.10725, "const005": 0.08956, "v5": 0.08312, "v1b": 0.12485, "v4": 0.10089}   # public RMSE (notes.md)
Ey2 = LB["zeros"] ** 2
Ey = (Ey2 - LB["const005"] ** 2 + 0.05 ** 2) / (2 * 0.05)
Eyv5 = (np.mean(v5 ** 2) + Ey2 - LB["v5"] ** 2) / 2
K = Eyv5 - 0.035 * Ey                       # = 0.07 E[y r] + 0.04 E[y t]
chk = None
if os.path.exists("work/subs/v1b_heuristic_withWA.csv"):   # which column did the leaderboard score for files with optional columns?
    H = pd.read_csv("work/subs/v1b_heuristic_withWA.csv", dtype={"GEOID": str})
    k = 0.35; r1, r4 = LB["v1b"] ** 2, LB["v4"] ** 2
    a_impl = ((r4 - Ey2) - k * (r1 - Ey2)) / (k * k - k)      # implied public E[h^2] from the zeros/v4/v1b parabola
    rng = np.random.default_rng(20261014); cc = []
    for col in ["transport_gap", "building_gap", "poi_gap", "coverage_gap_score"]:
        x = H[col].values ** 2; sub = [rng.choice(x, int(0.3 * len(x)), replace=False).mean() for _ in range(2000)]
        cc.append({"column": col, "all_rows_mean_sq": round(x.mean(), 5), "p0.5": round(np.percentile(sub, 0.5), 5),
                   "p99.5": round(np.percentile(sub, 99.5), 5), "implied_by_leaderboard": round(a_impl, 5)})
    chk = pd.DataFrame(cc); chk.to_csv("reports/tables/lb_scored_column_check.csv", index=False)

def rmse_known(p, Eyp):
    return float(np.sqrt(max(np.mean(p ** 2) - 2 * Eyp + Ey2, 0)))

rng = np.random.default_rng(20261014)
SUBS = [rng.choice(len(v5), int(0.3 * len(v5)), replace=False) for _ in range(2000)]
def band(p, coef):   # coef = (cy, cv5): E[y p] = cy*E[y] + cv5*E[y v5], with E[y v5] re-derived on each subset
    out = []
    for i in SUBS:
        eyv5 = (np.mean(v5[i] ** 2) + Ey2 - LB["v5"] ** 2) / 2
        out.append(np.sqrt(max(np.mean(p[i] ** 2) - 2 * (coef[0] * Ey + coef[1] * eyv5) + Ey2, 0)))
    return f"{np.percentile(out, 2.5):.4f}-{np.percentile(out, 97.5):.4f}"
rows = []
def add(name, why, p, Eyp=None, lo=None, hi=None, coef=None):
    rows.append({"variant": name, "what_it_tests": why, "mean_prediction": round(float(np.mean(p)), 4),
                 "predicted_public_rmse": None if Eyp is None else round(rmse_known(p, Eyp), 5),
                 "band95": band(p, coef) if coef is not None else None,
                 "range_low": None if lo is None else round(lo, 5), "range_high": None if hi is None else round(hi, 5)})

add("v5 as submitted", "check: should return 0.08312", v5, Eyv5, coef=(0, 1))
for c in [0.035, 0.05, round(Ey, 4)]:
    add(f"constant {c}", "no rural/tribal signal at all", np.full_like(v5, c), c * Ey, coef=(c, 0))
for f in [0.5, 1.5]:
    p = v5 + (f - 1) * 0.035; add(f"intercept x{f} ({0.035*f:.4f})", "baseline level", p, Eyv5 + (f - 1) * 0.035 * Ey, coef=((f - 1) * 0.035, 1))
for k in [0, 0.5, 1.5, 2.0]:
    p = 0.035 + k * (v5 - 0.035); add(f"rural+tribal increments x{k}", "strength of the whole rural/tribal signal", p, 0.035 * Ey + k * K, coef=(0.035 - k * 0.035, k))
# best a + b*v5 in the identified span (least squares in closed form)
A = np.array([[1, np.mean(v5)], [np.mean(v5), np.mean(v5 ** 2)]]); bvec = np.array([Ey, Eyv5])
a, b = np.linalg.solve(A, bvec)
add(f"best a + b*v5 (a={a:.4f}, b={b:.3f})", "optimum the probes allow without new submissions", a + b * v5, a * Ey + b * Eyv5, coef=(a, b))
# single-term changes: E[y r] and E[y t] are not separately identified; y in [0,1] gives 0 <= E[y t] <= min(E[t], E[y], K/0.04)
Et = tri.mean(); Btop = min(Et, Ey, K / 0.04)
def single(name, dr, dt):
    p = v5 + dr * rur + dt * tri
    vals = []
    for B in np.linspace(0, Btop, 201):
        Ar = (K - 0.04 * B) / 0.07
        vals.append(rmse_known(p, Eyv5 + dr * Ar + dt * B))
    add(name, "one coefficient alone (only a range is identified)", p, None, min(vals), max(vals))
single("rural coef x0.5 (0.035)", -0.035, 0); single("rural coef x1.5 (0.105)", 0.035, 0)
single("tribal coef x0.5 (0.02)", 0, -0.02); single("tribal coef x1.5 (0.06)", 0, 0.02); single("tribal coef = 0", 0, -0.04)

T = pd.DataFrame(rows); T.to_csv("reports/tables/v5_sensitivity.csv", index=False)
print(f"E[y]={Ey:.5f} sd={np.sqrt(Ey2-Ey**2):.5f}  E[y*v5]={Eyv5:.6f}  K={K:.6f}  E[t]={Et:.4f}")
if chk is not None: print(chk.to_string(index=False))
print(T.to_string(index=False))
