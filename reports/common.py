"""Shared definitions and statistics for the analysis scripts (run everything from the project root).

Definitions used everywhere (one place, so the reports never mix definitions):
  * populated tract       : pop_total > 0  (9,767 of the 9,794 scored tracts)
  * South Texas border seam: tracts in the 9 study-area Texas counties that touch the US-Mexico border
                             (geographic, county-level; NOT defined from any Overture value, so it is not circular)
  * Arizona contrast       : tracts in the 4 Arizona border counties + the one New Mexico border tract in maricopa-az
  * Google-present (N2)    : Google Open Buildings > 5% of a tract's footprints (descriptive only: it is a lineage value)
Statistics: OLS with region fixed effects; CR1 standard errors clustered by county; wild-cluster restricted bootstrap
(Webb weights) p-values; county-cluster bootstrap CIs for stratum ratios; Holm / Benjamini-Hochberg adjustment."""
import warnings, numpy as np, pandas as pd, scipy.sparse as sp
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

REGIONS = ["eastern-ok", "eastern-wa", "maricopa-az", "northern-ca", "south-central-tx"]
TX_BORDER = {"48061": "Cameron", "48215": "Hidalgo", "48427": "Starr", "48505": "Zapata", "48479": "Webb",
             "48323": "Maverick", "48271": "Kinney", "48465": "Val Verde", "48443": "Terrell"}
AZ_BORDER = {"04027": "Yuma", "04019": "Pima", "04023": "Santa Cruz", "04003": "Cochise", "35023": "Hidalgo (NM)"}
SEED = 20261014


def load():
    M = pd.read_parquet("reports/cache/master.parquet")
    P = M[M.pop_total.fillna(0) > 0].copy()
    P["county5"] = P.GEOID.str[:5]
    P["density"] = P.pop_total / P.km2.replace(0, np.nan)
    P["log10_density"] = np.log10(P.density.clip(lower=0.1))
    P["tx_border"] = P.county5.isin(TX_BORDER)
    P["az_border"] = P.county5.isin(AZ_BORDER)
    P["rural"] = P.ur_class.eq("Rural")
    P["reservation"] = P.tribal_legal.astype(bool)
    P["tribal_statistical"] = P.tribal_any.astype(bool) & ~P.reservation
    P["cl_res"] = np.where(P.reservation, "R:" + P.aiannh_name.fillna("?"), P.county5)
    return M, P


def _q(P, c, p=0.75):
    x = P[c]; return (x >= x.quantile(p)).astype(float).where(x.notna())


def strata(P):
    """Each stratum is a float Series: 1 = in, 0 = rest, NaN = undefined (excluded from BOTH sides)."""
    svi_hi = (P.svi_overall >= 0.75).astype(float).where(P.svi_overall.notna())
    haz = ((_q(P, "usdm_winter_dsci") == 1) | (_q(P, "usfs_WHP_mean") == 1) | (_q(P, "epht_heat_days_summer") == 1)).astype(float)
    b = lambda s: s.astype(float)
    return {
        "Rural": b(P.rural),
        "Tribal (any overlap)": b(P.tribal_any.astype(bool)),
        "High SVI (>=0.75)": svi_hi,
        "High CVI (top 25%)": _q(P, "cvi_overall"),
        "Winter drought (top 25%)": _q(P, "usdm_winter_dsci"),
        "Wildfire hazard (WHP top 25%)": _q(P, "usfs_WHP_mean"),
        "Summer heat (top 25%)": _q(P, "epht_heat_days_summer"),
        "Hazard + high SVI": (haz * svi_hi).where(svi_hi.notna()),
        "N1 Reservation / trust land": b(P.reservation),
        "N2 Google-present (>5% of footprints)": b(P.sh_gob.fillna(0) > 0.05),
        "N2b South Texas border seam (9 counties)": b(P.tx_border),
        "N3 Minority-majority (SVI minority >=0.90)": (P.svi_minority >= 0.90).astype(float).where(P.svi_minority.notna()),
        "N4 Weather-station desert (>10 km)": (P.ghcn_any_nearest_km > 10).astype(float).where(P.ghcn_any_nearest_km.notna()),
        "N5 Housing/transport burden (SVI theme 4 >=0.75)": (P.svi_housing_transport >= 0.75).astype(float).where(P.svi_housing_transport.notna()),
        "N6 Burned since 2018 (>=30% of land)": b((P.nifc_wildfire_burned_pct_land >= 30) & (P.nifc_wildfire_last_year >= 2018)),
    }

SCORECARD = ["Rural", "Tribal (any overlap)", "High SVI (>=0.75)", "High CVI (top 25%)", "Winter drought (top 25%)",
             "Wildfire hazard (WHP top 25%)", "Summer heat (top 25%)", "Hazard + high SVI"]


def design(P, terms, fe=True):
    X = pd.DataFrame({t: P[t].astype(float) for t in terms})
    if fe:
        for r in REGIONS[1:]: X["fe_" + r] = P.region.eq(r).astype(float)
    return X


def _prep(y, X, cl, w):
    d = pd.concat([y.rename("_y"), X, pd.Series(cl, index=X.index, name="_cl")] +
                  ([w.rename("_w")] if w is not None else []), axis=1).dropna()
    Xm = np.column_stack([np.ones(len(d))] + [d[c].values for c in X.columns])
    wv = d._w.values.astype(float) if w is not None else np.ones(len(d))
    u, inv = np.unique(d._cl.values, return_inverse=True)
    return d._y.values.astype(float), Xm, wv, inv, len(u)


def cluster_ols(y, X, cl, w=None, B=4999, boot_terms=None, seed=SEED):
    """WLS/OLS with CR1 cluster-robust SEs and wild-cluster restricted bootstrap p (Webb 6-point) for boot_terms."""
    yv, Xm, wv, inv, G = _prep(y, X, cl, w)
    n, k = Xm.shape
    A = np.linalg.inv((Xm * wv[:, None]).T @ Xm)
    H = A @ (Xm * wv[:, None]).T                         # b = H y
    b = H @ yv; e = yv - Xm @ b
    C = sp.csr_matrix((np.ones(n), (inv, np.arange(n))), shape=(G, n))
    S = C @ (Xm * (wv * e)[:, None]); c = G/(G-1)*(n-1)/(n-k)
    V = c * A @ (S.T @ S) @ A; se = np.sqrt(np.diag(V))
    r2 = 1 - (wv*e**2).sum()/(wv*(yv-np.average(yv, weights=wv))**2).sum()
    names = ["const"] + list(X.columns)
    out = pd.DataFrame({"term": names, "coef": b, "se_cr1": se, "t_cr1": b/se, "n": n, "clusters": G, "r2": r2})
    out["p_wcr"] = np.nan
    rng = np.random.default_rng(seed)
    WEBB = np.array([-np.sqrt(1.5), -1, -np.sqrt(.5), np.sqrt(.5), 1, np.sqrt(1.5)])
    for t in (boot_terms or []):
        j = names.index(t)
        Xr = np.delete(Xm, j, axis=1); Ar = np.linalg.inv((Xr*wv[:, None]).T @ Xr)
        br = Ar @ (Xr*wv[:, None]).T @ yv; fr = Xr @ br; er = yv - fr
        uj = Xm @ A[j]                                         # influence of obs on coef j
        hits = 0
        for s0 in range(0, B, 1000):                           # batches keep memory small
            bb = min(1000, B - s0)
            Vb = WEBB[rng.integers(0, 6, size=(G, bb))][inv]   # n x bb cluster-level weights
            Ys = fr[:, None] + er[:, None] * Vb
            Bs = H @ Ys; Es = Ys - Xm @ Bs
            Sg = C @ ((uj * wv)[:, None] * Es)
            ts = Bs[j] / np.sqrt(c * (Sg**2).sum(axis=0))
            hits += (np.abs(ts) >= abs(b[j]/se[j])).sum()
        out.loc[j, "p_wcr"] = (1 + hits) / (B + 1)
    return out


def holm(p):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p)
    adj = np.empty(m); adj[o] = np.minimum(1, np.maximum.accumulate((m - np.arange(m)) * p[o])); return adj


def bh(p):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p)
    q = p[o] * m / np.arange(1, m+1); q = np.minimum.accumulate(q[::-1])[::-1]
    adj = np.empty(m); adj[o] = np.minimum(1, q); return adj


def cluster_boot_ratio(num, den, inside, cl, B=2000, seed=SEED):
    """County-cluster bootstrap of (sum num/sum den | in) / (sum num/sum den | rest).
    num/den per tract (den=1 gives a tract mean). Rows with NaN num or NaN stratum are excluded.
    Returns point ratio, 95% percentile CI, two-sided bootstrap p for 'difference = 0', and the in/rest values."""
    ok = ~(np.isnan(num) | np.isnan(den) | np.isnan(inside))
    num, den, inside, cl = num[ok], den[ok], inside[ok].astype(bool), np.asarray(cl)[ok]
    u, inv = np.unique(cl, return_inverse=True); G = len(u)
    agg = lambda v: np.bincount(inv, weights=v, minlength=G)
    Ni, Di, No, Do = agg(num*inside), agg(den*inside), agg(num*~inside), agg(den*~inside)
    a, bb = Ni.sum()/Di.sum(), No.sum()/Do.sum()
    rng = np.random.default_rng(seed)
    W = rng.multinomial(G, np.full(G, 1/G), size=B).astype(float)   # B x G resampling counts
    with np.errstate(invalid="ignore", divide="ignore"):
        ai, ao = (W @ Ni)/(W @ Di), (W @ No)/(W @ Do)
        rat, dif = ai/ao, ai-ao
    rat, dif = rat[np.isfinite(rat)], dif[np.isfinite(dif)]
    p = min(1.0, 2*min((dif <= 0).mean(), (dif >= 0).mean()) + 1/len(dif))
    return dict(in_=a, rest=bb, ratio=a/bb, lo=np.quantile(rat, .025), hi=np.quantile(rat, .975), p_boot=p,
                diff=a-bb, diff_lo=np.quantile(dif, .025), diff_hi=np.quantile(dif, .975),
                n_in=int(inside.sum()), n_rest=int((~inside).sum()))


def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k/n; d = 1 + z*z/n; c = (p + z*z/(2*n))/d; h = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return (c - h, c + h)
