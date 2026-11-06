import pandas as pd
import matplotlib.pyplot as plt
import sys

THRESHOLD_K = int(sys.argv[1]) if len(sys.argv) > 1 else 3

df = pd.read_csv("empirical_results.csv")
degraded_rate = df.groupby("k")["verdict"].apply(lambda s: (s == "DEGRADED").mean())
mean_latency = df.groupby("k")["elapsed_ms"].mean()

print("Degraded rate by k:")
print(degraded_rate)
print()
print("Mean elapsed_ms by k:")
print(mean_latency)

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(degraded_rate.index, degraded_rate.values, marker="o", label="Empirical degraded rate")
ax.axvline(x=THRESHOLD_K, color="red", linestyle="--", label=f"Formal threshold k*={THRESHOLD_K}")
ax.set_xlabel("Adversary capability k")
ax.set_ylabel("Fraction of runs classified DEGRADED")
ax.set_title("Formal threshold vs. empirical degraded rate")
ax.legend()
fig.tight_layout()
fig.savefig("threshold_comparison.png", dpi=200)
print("Saved threshold_comparison.png")
