"""
analyze_paper_figures.py
========================
Reproduces Table 3 and Figure 1 from the paper:
  "Formal Verification and Empirical Validation of IEC 61850 GOOSE
   Failover Timing Safety Under a Bounded Active Adversary"

Usage:
    python3 analyze_paper_figures.py \
        [--strict  PATH/TO/results_strict_boundary_only.csv] \
        [--aligned PATH/TO/results_aligned_verdict.csv]

Defaults to ../data/results_strict_boundary_only.csv and
../data/results_aligned_verdict.csv (relative to this script).

Outputs:
    - Table 3 printed to stdout (95% Wilson intervals)
    - threshold_comparison.png  (Figure 1 from the paper)
"""

import sys
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# ---------------------------------------------------------------------------
# Wilson score confidence interval
# ---------------------------------------------------------------------------
def wilson_ci(successes, n, z=1.96):
    if n == 0:
        return 0.0, 0.0, 0.0
    phat = successes / n
    denom = 1 + z ** 2 / n
    center = (phat + z ** 2 / (2 * n)) / denom
    margin = (z * ((phat * (1 - phat) / n + z ** 2 / (4 * n ** 2)) ** 0.5)) / denom
    return phat, max(0.0, center - margin), min(1.0, center + margin)


def coarse_summary(csv_path):
    df = pd.read_csv(csv_path)
    sub = df[df["sweep"] == "coarse"]
    rows = []
    for k, g in sub.groupby("k"):
        n = len(g)
        degraded = (g["verdict"] == "DEGRADED").sum()
        phat, lo, hi = wilson_ci(degraded, n)
        rows.append({"k": int(k), "n": n, "rate": phat, "ci_lo": lo, "ci_hi": hi})
    return pd.DataFrame(rows).sort_values("k").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(here, "..", "data")

    parser = argparse.ArgumentParser()
    parser.add_argument("--strict",  default=os.path.join(data_dir, "results_strict_boundary_only.csv"))
    parser.add_argument("--aligned", default=os.path.join(data_dir, "results_aligned_verdict.csv"))
    args = parser.parse_args()

    strict  = coarse_summary(args.strict)
    aligned = coarse_summary(args.aligned)

    # -- Table 3 ----------------------------------------------------------------
    print("Table 3: Effect of verdict precision on measured failure rate")
    print(f"{'k':>3}  {'Strict boundary only':>24}  {'Strict + precise timestamp':>28}  {'n':>5}")
    print("-" * 70)
    for _, rs, ra in zip(strict["k"], strict.itertuples(), aligned.itertuples()):
        s = f"{rs.rate:.3f} [{rs.ci_lo:.3f}, {rs.ci_hi:.3f}]"
        a = f"{ra.rate:.3f} [{ra.ci_lo:.3f}, {ra.ci_hi:.3f}]"
        print(f"{rs.k:>3}  {s:>24}  {a:>28}  {rs.n:>5}")

    # -- Figure 1 ---------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4.5))

    # Grey triangles – strict boundary only
    ax.errorbar(
        strict["k"], strict["rate"] * 100,
        yerr=[(strict["rate"] - strict["ci_lo"]) * 100,
              (strict["ci_hi"] - strict["rate"]) * 100],
        marker="^", markersize=7, linestyle="--", color="gray", capsize=4,
        label="Strict boundary only (n = 200)",
    )

    # Dark-red squares – aligned verdict
    ax.errorbar(
        aligned["k"], aligned["rate"] * 100,
        yerr=[(aligned["rate"] - aligned["ci_lo"]) * 100,
              (aligned["ci_hi"] - aligned["rate"]) * 100],
        marker="s", markersize=7, linestyle="-", color="darkred", capsize=4,
        label="Strict boundary + precise timestamp (n = 200)",
    )

    # Formal threshold
    ax.axvline(x=5, color="black", linestyle=":", linewidth=1.2, label="$k^* = 5$")
    ax.text(5.08, 95, "$k^* = 5$", fontsize=9, va="top")

    ax.set_xlabel("Adversary capability $k$")
    ax.set_ylabel("Degraded rate (%)")
    ax.set_xticks([0, 1, 2, 3, 4, 5])
    ax.set_ylim(-2, 108)
    ax.legend(fontsize=9, loc="upper left")
    ax.set_title("")

    fig.tight_layout()
    out = "threshold_comparison.png"
    fig.savefig(out, dpi=200)
    print(f"\nFigure saved to {out}")


if __name__ == "__main__":
    main()
