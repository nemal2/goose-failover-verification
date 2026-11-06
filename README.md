# Artifact: Formal Verification and Empirical Validation of IEC 61850 GOOSE Failover Timing Safety

Artifact for the paper:

> **Formal Verification and Empirical Validation of IEC 61850 GOOSE Failover Timing Safety Under a Bounded Active Adversary**  
> Nemal Perera, Faculty of Engineering, University of Ruhuna, Sri Lanka.

---

## Repository layout

```
goose-failover-verification/
├── formal/
│   └── failover.xml                         # UPPAAL timed-automata model
├── implementation/
│   ├── relay_primary.c                      # Primary relay (GOOSE publisher)
│   ├── relay_backup.c                       # Backup relay – aligned verdict
│   ├── relay_backup_original_misaligned.c   # Earlier verdict variant (see §IV-D)
│   └── Makefile                             # Builds against libiec61850
├── harness/
│   └── orchestrate.py                       # netns/netem sweep harness
├── analysis/
│   ├── analyze_basic.py                     # Simple degraded-rate summary
│   └── analyze_paper_figures.py             # Reproduces Table 3 and Fig. 1
└── data/
    ├── results_strict_boundary_only.csv     # n=200/level, strict-boundary verdict
    └── results_aligned_verdict.csv          # n=200/level, aligned verdict (Table 3 col 2)
```

---

## 1. Formal model (UPPAAL)

**Requirements:** [UPPAAL](https://uppaal.org) ≥ 4.1 or 5.0 (free for academic use).

Open `formal/failover.xml` in the UPPAAL GUI. The model contains two templates:

| Template | Role |
|---|---|
| `Process` | Combined primary/backup relay pair |
| `Adversary` | Bounded interferer (capacity parameter `k`) |

**Replicating Table 2:** For each `k ∈ {0,…,5}`, edit the global declaration `int k = <value>;`, then run the verifier query `E<> Process.Degraded`. The result is `NOT SATISFIED` for k ∈ {0,…,4} and `SATISFIED` at k = 5, establishing the threshold k* = 5.

Additional queries included in the model:
- `E<> Process.BackupActive` — reachability of safe outcome (satisfied at all k)
- `A[] not deadlock` — absence of deadlock

---

## 2. Building the C implementation

**Requirements:**
- Linux with network namespace support (`ip netns`)
- [libiec61850](https://github.com/mz-automation/libiec61850) built from source
- GCC

Clone libiec61850 as a sibling of the `implementation/` directory, or update `LIBIEC_HOME` in the Makefile:

```bash
# Directory structure expected by the Makefile:
parent/
├── libiec61850/        # built library
│   └── build/libiec61850.a
└── implementation/     # this folder
    ├── relay_primary.c
    ├── relay_backup.c
    └── Makefile
```

```bash
cd implementation
make all        # produces ./relay_primary and ./relay_backup
```

### Key parameters (top of each source file)

| Parameter | Value | Matches model |
|---|---|---|
| `TRIP_ATTEMPTS` (N) | 5 | `const int N = 5` |
| `RETRY_INTERVAL_MS` | 2 ms | `r >= 2` guard |
| `timeout_ms` (T) | 10 ms (CLI arg) | `const int T = 10` |

### Verdict-function variants

The backup relay underwent two rounds of verdict alignment (§IV-D of the paper):

| File | Verdict logic | Corresponds to |
|---|---|---|
| `relay_backup_original_misaligned.c` | Always PASS on delivery; stale elapsed_ms | Pre-alignment baseline |
| `relay_backup.c` | Strict `< T`; uses precise callback timestamp | Final aligned verdict (Table 3, col 2) |

The intermediate variant (strict boundary using the stale polling-loop elapsed_ms, Table 3 col 1) was used to generate `data/results_strict_boundary_only.csv` and is reconstructable by replacing the `trip_time`-based classification in `relay_backup.c` with the stale `elapsed_ms` from the polling loop.

---

## 3. Running the empirical sweep

**Requirements:** `tc`/`netem` (iproute2), Python ≥ 3.8, the two compiled relay binaries.

### Network namespace setup

The harness expects two pre-created namespaces connected by a veth pair:

```bash
# Create namespaces
sudo ip netns add relay_primary
sudo ip netns add relay_backup

# Create veth pair
sudo ip link add veth-primary type veth peer name veth-backup

# Move each end to its namespace
sudo ip link set veth-primary netns relay_primary
sudo ip link set veth-backup  netns relay_backup

# Bring interfaces up
sudo ip netns exec relay_primary ip link set veth-primary up
sudo ip netns exec relay_backup  ip link set veth-backup  up
```

### Running the sweep

```bash
cp implementation/relay_primary implementation/relay_backup harness/
cd harness
sudo python3 orchestrate.py   # writes empirical_results.csv, 1200 trials total
```

The harness runs 200 trials per capability level k ∈ {0,…,5}, setting `netem` loss to `round(100·k/5)%` on the primary's outbound interface. Each trial logs `k, run, verdict, elapsed_ms` to CSV.

---

## 4. Reproducing the paper figures

```bash
cd analysis
pip install pandas matplotlib
python3 analyze_paper_figures.py
# prints Table 3 to stdout and saves threshold_comparison.png
```

To use your own sweep output instead of the included data:

```bash
python3 analyze_paper_figures.py \
    --strict  ../data/results_strict_boundary_only.csv \
    --aligned ../data/results_aligned_verdict.csv
```

---

## 5. Data files

| File | Description | Rows |
|---|---|---|
| `data/results_strict_boundary_only.csv` | n=200/level, coarse (k=0–5) + fine (fractional k) sweep; strict-boundary verdict using polling-loop timestamp | 3 400 |
| `data/results_aligned_verdict.csv` | n=200/level, same sweeps; fully aligned verdict (precise callback timestamp) | 3 400 |

Both files share the schema:
```
sweep, k, loss_percent, run, verdict, elapsed_ms, trip_delivered
```

- `sweep`: `coarse` (k ∈ {0,…,5}) or `fine` (fractional loss levels 1.5–4.0)
- `verdict`: `PASS` or `DEGRADED`
- `trip_delivered`: 1 if any trip frame arrived (even after deadline), 0 if none arrived

---

## 6. libiec61850

The [libiec61850](https://github.com/mz-automation/libiec61850) library is not included in this repository due to its size. Clone it from the upstream repository and build it before compiling the relay programs:

```bash
git clone https://github.com/mz-automation/libiec61850.git
cd libiec61850
cmake -S . -B build && cmake --build build
```

This work used libiec61850 for the GOOSE publisher/subscriber API only; no modifications to the library were made.

---

## License

The source files in this repository (`relay_primary.c`, `relay_backup.c`, `orchestrate.py`, and the analysis scripts) are released under the **MIT License**. The UPPAAL model (`failover.xml`) is released under **CC BY 4.0**. The data files (`data/`) are released under **CC0 1.0** (public domain dedication).

UPPAAL itself is a separate tool available at [uppaal.org](https://uppaal.org) under its own academic license; it is not redistributed here.
