"""STEP 0 — PROVE THE ASSET IS BEATABLE (the make-or-break gate).

Deriv synthetics are algorithmically generated to be near-random. Before ANY strategy,
we test each asset's return series for EXPLOITABLE STRUCTURE. If an asset shows no
structure, we SAY SO and drop it — we do not curve-fit noise.

Four classic predictability tests on close-to-close log returns:
  1. Autocorrelation (lag 1..k)  — white-noise 95% band = +/- 1.96/sqrt(n).
       significant NEGATIVE lag-1 = mean-reversion (good for binary fade setups).
       significant POSITIVE lag-1 = trend/momentum.
  2. Runs test (Wald-Wolfowitz on sign of returns) — |Z|>1.96 => non-random ordering.
  3. Variance ratio (Lo-MacKinlay, heteroskedasticity-robust z) — VR<1 mean-revert,
       VR>1 trend, VR~1 random walk.
  4. Hurst exponent (R/S) — H<0.5 mean-revert, ~0.5 random, >0.5 trend.

VERDICT (brutally honest):
  - Count how many tests reject randomness at 95%.
  - Note the DIRECTION (mean-revert vs trend) where tests agree.
  - TRADEABLE only if >=2 independent tests reject randomness AND agree on a direction
    that one of our setup families can exploit. Otherwise -> DROP (RNG noise).
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np
from scipy import stats


@dataclass
class TestResult:
    name: str
    stat: float
    crit_or_p: float
    reject_random: bool
    direction: str   # "mean_revert" | "trend" | "none"
    note: str = ""


# ── 1. Autocorrelation ──
def autocorr_test(r: np.ndarray, max_lag: int = 5) -> TestResult:
    n = len(r)
    band = 1.96 / np.sqrt(n)
    r0 = r - r.mean()
    denom = np.sum(r0 * r0)
    acfs = []
    for lag in range(1, max_lag + 1):
        num = np.sum(r0[lag:] * r0[:-lag])
        acfs.append(num / denom)
    acfs = np.array(acfs)
    lag1 = acfs[0]
    sig_lags = np.where(np.abs(acfs) > band)[0]
    reject = len(sig_lags) > 0
    direction = "none"
    if reject:
        direction = "mean_revert" if lag1 < 0 else "trend"
    return TestResult("autocorrelation", float(lag1), float(band), reject, direction,
                      f"lag1={lag1:+.4f} band=+/-{band:.4f} sig_lags={(sig_lags+1).tolist()}")


# ── 2. Runs test (Wald-Wolfowitz) ──
def runs_test(r: np.ndarray) -> TestResult:
    signs = np.sign(r)
    signs = signs[signs != 0]
    n = len(signs)
    n_pos = int(np.sum(signs > 0))
    n_neg = int(np.sum(signs < 0))
    if n_pos == 0 or n_neg == 0:
        return TestResult("runs", 0.0, 1.0, False, "none", "degenerate (one sign)")
    runs = 1 + int(np.sum(signs[1:] != signs[:-1]))
    mu = 1 + (2 * n_pos * n_neg) / n
    var = (2 * n_pos * n_neg * (2 * n_pos * n_neg - n)) / (n * n * (n - 1))
    if var <= 0:
        return TestResult("runs", 0.0, 1.0, False, "none", "zero variance")
    z = (runs - mu) / np.sqrt(var)
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    reject = p < 0.05
    # fewer runs than expected (z<0) = persistence/trend; more runs (z>0) = mean-revert
    direction = "none"
    if reject:
        direction = "mean_revert" if z > 0 else "trend"
    return TestResult("runs", float(z), float(p), reject, direction,
                      f"runs={runs} exp={mu:.1f} z={z:+.3f} p={p:.4f}")


# ── 3. Variance ratio (Lo-MacKinlay, robust z) ──
def variance_ratio_test(r: np.ndarray, q: int = 2) -> TestResult:
    n = len(r)
    if n < q * 4:
        return TestResult(f"variance_ratio(q={q})", 1.0, 1.0, False, "none", "too few obs")
    mu = r.mean()
    # variance of 1-period returns
    var1 = np.sum((r - mu) ** 2) / (n - 1)
    # variance of q-period (overlapping) sums
    rq = np.convolve(r, np.ones(q), mode="valid")  # length n-q+1
    m = q * (n - q + 1) * (1 - q / n)
    varq = np.sum((rq - q * mu) ** 2) / m
    if var1 == 0:
        return TestResult(f"variance_ratio(q={q})", 1.0, 1.0, False, "none", "zero var")
    vr = varq / var1
    # heteroskedasticity-robust standard error (Lo-MacKinlay)
    theta = 0.0
    e2 = (r - mu) ** 2
    for k in range(1, q):
        delta = (np.sum(e2[k:] * e2[:-k]) /
                 (np.sum(e2) ** 2 / n))
        theta += ((2 * (q - k) / q) ** 2) * delta
    se = np.sqrt(theta / n) if theta > 0 else np.sqrt(2.0 * (2 * q - 1) * (q - 1) / (3 * q * n))
    z = (vr - 1) / se if se > 0 else 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    reject = p < 0.05
    direction = "none"
    if reject:
        direction = "mean_revert" if vr < 1 else "trend"
    return TestResult(f"variance_ratio(q={q})", float(vr), float(p), reject, direction,
                      f"VR={vr:.4f} z={z:+.3f} p={p:.4f}")


# ── 4. Hurst exponent (R/S analysis) ──
def hurst_test(r: np.ndarray) -> TestResult:
    n = len(r)
    if n < 128:
        return TestResult("hurst", 0.5, 0.0, False, "none", "too few obs")
    # cumulative deviation series
    series = r
    min_w, max_w = 8, n // 2
    ws, rs = [], []
    w = min_w
    while w <= max_w:
        n_chunks = n // w
        rss = []
        for c in range(n_chunks):
            chunk = series[c * w:(c + 1) * w]
            z = chunk - chunk.mean()
            cum = np.cumsum(z)
            r_range = cum.max() - cum.min()
            s = chunk.std()
            if s > 0:
                rss.append(r_range / s)
        if rss:
            ws.append(w)
            rs.append(np.mean(rss))
        w = int(w * 1.6)
    if len(ws) < 3:
        return TestResult("hurst", 0.5, 0.0, False, "none", "insufficient scales")
    logw = np.log(np.array(ws))
    logrs = np.log(np.array(rs))
    H, _ = np.polyfit(logw, logrs, 1)
    # distance from 0.5 as a rough significance proxy (no clean p; report magnitude)
    dist = abs(H - 0.5)
    reject = dist > 0.05   # >0.55 or <0.45 = meaningful departure from random walk
    direction = "none"
    if reject:
        direction = "mean_revert" if H < 0.5 else "trend"
    return TestResult("hurst", float(H), float(dist), reject, direction,
                      f"H={H:.4f} (|H-0.5|={dist:.3f})")


@dataclass
class Step0Verdict:
    symbol: str
    granularity_sec: int
    n_returns: int
    tests: list
    n_reject: int
    agreed_direction: str
    tradeable: bool
    reason: str

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def run_step0(symbol: str, granularity_sec: int, log_returns: np.ndarray) -> Step0Verdict:
    """Run all 4 tests; produce an honest tradeable/drop verdict."""
    r = np.asarray(log_returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    tests = [
        autocorr_test(r),
        runs_test(r),
        variance_ratio_test(r, q=2),
        variance_ratio_test(r, q=4),
        hurst_test(r),
    ]
    rejecters = [t for t in tests if t.reject_random]
    n_reject = len(rejecters)
    # tally direction among rejecters
    dirs = [t.direction for t in rejecters if t.direction != "none"]
    mr = dirs.count("mean_revert")
    tr = dirs.count("trend")
    if mr > tr:
        agreed = "mean_revert"
    elif tr > mr:
        agreed = "trend"
    elif mr == tr and mr > 0:
        agreed = "mixed"
    else:
        agreed = "none"

    # TRADEABLE: >=2 tests reject randomness AND a clear single direction emerges.
    tradeable = n_reject >= 2 and agreed in ("mean_revert", "trend")
    if tradeable:
        reason = (f"{n_reject}/5 tests reject randomness; consistent {agreed} structure "
                  f"-> candidate for {'fade/reversion' if agreed=='mean_revert' else 'continuation'} setups.")
    elif n_reject >= 2 and agreed == "mixed":
        reason = (f"{n_reject}/5 reject randomness but DIRECTION CONFLICTS (mr={mr} tr={tr}) "
                  f"-> ambiguous; do NOT trust, treat as DROP unless a setup-specific test passes.")
        tradeable = False
    else:
        reason = (f"only {n_reject}/5 tests reject randomness -> behaves like RNG noise. "
                  f"DROP: curve-fitting this is fooling ourselves.")
    return Step0Verdict(symbol, granularity_sec, len(r),
                        [asdict(t) for t in tests], n_reject, agreed, tradeable, reason)
