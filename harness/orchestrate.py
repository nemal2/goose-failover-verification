import subprocess, csv, re, time, os

NETNS_PRIMARY = "relay_primary"
NETNS_BACKUP  = "relay_backup"
IFACE_PRIMARY = "veth-primary"
DEADLINE_MS   = 10          # matches the model's T from Part 5
CAPACITY_VALUES = [0, 1, 2, 3, 4, 5]   # matches N in the formal sweep
RUNS_PER_VALUE = 200        # 200 trials per capability level (matches the paper)
FIFO_PATH = "/tmp/fault_sync"

def set_netem(loss_percent):
    subprocess.run(["ip","netns","exec",NETNS_PRIMARY,
                     "tc","qdisc","del","dev",IFACE_PRIMARY,"root"],
                    stderr=subprocess.DEVNULL)
    subprocess.run(["ip","netns","exec",NETNS_PRIMARY,
                     "tc","qdisc","add","dev",IFACE_PRIMARY,"root",
                     "netem","loss", f"{loss_percent}%"])

def capacity_to_loss_percent(k, n):
    return round(100 * k / n)

def run_once(k):
    # CHANGED: a fresh FIFO per run, created before either process starts,
    # so relay_primary can signal relay_backup the instant the fault begins
    # (see relay_primary.c / relay_backup.c). Without this, backup's
    # deadline clock is not aligned to the real fault event at all.
    if os.path.exists(FIFO_PATH):
        os.remove(FIFO_PATH)
    os.mkfifo(FIFO_PATH)

    backup = subprocess.Popen(
        ["ip","netns","exec",NETNS_BACKUP,
         "./relay_backup","veth-backup",str(DEADLINE_MS),FIFO_PATH],
        stdout=subprocess.PIPE, text=True)
    time.sleep(0.05)  # let the subscriber bind before the publisher starts
    primary = subprocess.Popen(
        ["ip","netns","exec",NETNS_PRIMARY,
         "./relay_primary","veth-primary",FIFO_PATH],
        stdout=subprocess.PIPE, text=True)
    primary.wait()
    out, _ = backup.communicate(timeout=5)
    os.remove(FIFO_PATH)

    m = re.search(r"RESULT,(\w+),elapsed_ms=(\d+)", out)
    return (m.group(1), int(m.group(2))) if m else (None, None)

def main():
    with open("empirical_results.csv","w",newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["k","run","verdict","elapsed_ms"])
        for k in CAPACITY_VALUES:
            set_netem(capacity_to_loss_percent(k, max(CAPACITY_VALUES)))
            for run_idx in range(RUNS_PER_VALUE):
                verdict, elapsed = run_once(k)
                writer.writerow([k, run_idx, verdict, elapsed])
                print(f"k={k} run={run_idx} verdict={verdict} elapsed_ms={elapsed}")

if __name__ == "__main__":
    main()
