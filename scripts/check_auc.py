"""Grid + Cortes-Mohri checks for every AUC reported in the paper.

Inputs: hard-code the reported (auc, decimals, n_pos, n_neg,
reported_se_or_ci) tuples below from the paper / supplement.
Outputs: out/auc_grid.csv with one row per reported AUC.
"""
from math import comb
import csv, os, sys

OUT = "out/auc_grid.csv"
os.makedirs("out", exist_ok=True)

# (label, auc, decimals, n_pos, n_neg, reported_se_or_half_ci)
REPORTED = [
    # Fill in from the paper:
    # ("Table 2 / Method X / DatasetA", 0.913, 3, 12, 30, None),
]

def on_grid(value, denom, decimals):
    tol = 0.5 * 10 ** (-decimals) + 1e-12
    k = max(0, min(denom, round(value * denom)))
    return abs(k / denom - value) <= tol, k, k / denom

def cortes_mohri(auc, m, n):
    """Distribution-independent E[A] and sigma(A) given (k, m, n).
    Solves for k from auc: k approx (1 - auc) * (m + n).
    """
    N = m + n
    k = round((1 - auc) * N)
    if k < 0 or k > min(m, n):
        return None, None
    S_k   = sum(comb(N + 1, x) for x in range(k + 1))
    S_km1 = sum(comb(N, x)     for x in range(k))
    Ea = 1 - k / N - ((n - m) ** 2 * (N + 1)) / (4 * m * n) * (k / N - S_km1 / S_k)

    # Corollary 1 of Cortes & Mohri (2004). Simplified summation form.
    def Z(i):
        num = sum(comb(N + 1 - i, x) for x in range(k - i + 1))
        den = sum(comb(N + 1,     x) for x in range(k + 1))
        return num / den
    T = 3 * ((m - n) ** 2 + m + n) + 2
    Z1, Z2, Z3, Z4 = Z(1), Z(2), Z(3), Z(4)
    Q1 = (T * k**3 + 3 * (m - 1) * T * k**2
          + ((-3 * n**2 + 3 * m * n - 3 * m + 8) * T - 6 * (6*m*n + m + n)) * k
          + (-3 * m**2 + 7 * (m + n) + 3 * m * n) * T - 2 * (6*m*n + m + n))
    Q0 = ((N + 1) * T * k**2
          + ((-3*n**2 + 3*m*n + 3*m + 1) * T - 12 * (3*m*n + m + n) - 8) * k
          + (-3*m**2 + 7*m + 10*n + 3*m*n + 10) * T - 4 * (3*m*n + m + n + 1))
    var = (
        (N + 1) * N * (N - 1) * T * ((N - 2) * Z4 - (2*m - n + 3*k - 10) * Z3) / (72 * m**2 * n**2)
        + (N + 1) * N * T * (m**2 - n*m + 3*k*m - 5*m + 2*k**2 - n*k + 12 - 9*k) * Z2 / (48 * m**2 * n**2)
        - (N + 1)**2 * (m - n)**4 * Z1**2 / (16 * m**2 * n**2)
        - (N + 1) * Q1 * Z1 / (72 * m**2 * n**2)
        + k * Q0 / (144 * m**2 * n**2)
    )
    return Ea, max(var, 0) ** 0.5

with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["label", "auc", "d", "n_pos", "n_neg",
                "on_grid", "nearest_grid",
                "EA_indep", "sigma_indep",
                "min_95CI_halfwidth", "reported_halfwidth",
                "CI_consistent"])
    for label, auc, d, n_pos, n_neg, rep_hw in REPORTED:
        ok, _, grid = on_grid(auc, 2 * n_pos * n_neg, d)
        EA, sigma = cortes_mohri(auc, n_pos, n_neg)
        min_hw = 1.96 * sigma if sigma else None
        ci_ok = (rep_hw is None) or (rep_hw + 1e-12 >= min_hw)
        w.writerow([label, auc, d, n_pos, n_neg, ok, round(grid, d + 2),
                    None if EA is None else round(EA, 4),
                    None if sigma is None else round(sigma, 4),
                    None if min_hw is None else round(min_hw, 4),
                    rep_hw, ci_ok])

print(f"wrote {OUT}; rows={len(REPORTED)}")
