#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from pathlib import Path


IPC_RE = re.compile(
    r"CPU\s+(?P<cpu>\d+)\s+cumulative IPC:\s+(?P<ipc>[0-9.]+)\s+"
    r"instructions:\s+(?P<instructions>\d+)\s+cycles:\s+(?P<cycles>\d+)"
)
BRANCH_RE = re.compile(
    r"CPU\s+(?P<cpu>\d+)\s+Branch Prediction Accuracy:\s+"
    r"(?P<accuracy>[0-9.]+)%\s+MPKI:\s+(?P<mpki>[0-9.]+)"
)
CACHE_RE = re.compile(
    r"(?:cpu\d+->)?(?P<cache>[A-Za-z0-9_]+)\s+"
    r"(?P<kind>TOTAL|LOAD|RFO|PREFETCH|WRITE|TRANSLATION)\s+"
    r"ACCESS:\s+(?P<access>\d+)\s+HIT:\s+(?P<hit>\d+)\s+"
    r"MISS:\s+(?P<miss>\d+)\s+(?:MISS_MERGE|MSHR_MERGE):\s+(?P<miss_merge>\d+)"
)
FDIP_BREAKDOWN_RE = re.compile(r"^(?P<label>L1I .+?)\s*:\s*(?P<count>\d+)")

FDIP_LABELS = {
    "L1I Hit (FDIP Covered)": "fdip_l1i_hit_covered",
    "L1I Hit (Non-Prefetch)": "fdip_l1i_hit_non_prefetch",
    "L1I Late Prefetch (Merge)": "fdip_l1i_late_prefetch_merge",
    "L1I Merge (Non-Prefetch)": "fdip_l1i_merge_non_prefetch",
    "L1I Miss": "fdip_l1i_miss",
}


FIELDNAMES = [
    "run_id",
    "config",
    "trace_set",
    "trace_group",
    "trace",
    "status",
    "reason",
    "ipc",
    "instructions",
    "cycles",
    "branch_accuracy",
    "branch_mpki",
    "l1d_mpki",
    "l2c_mpki",
    "llc_mpki",
    "stlb_mpki",
    "on_chip_traffic_mpki",
    "off_chip_traffic_mpki",
    "l1d_load_access",
    "l1d_load_miss",
    "l1d_rfo_access",
    "l1d_rfo_miss",
    "l2c_load_access",
    "l2c_load_miss",
    "l2c_rfo_access",
    "l2c_rfo_miss",
    "llc_total_access",
    "llc_total_miss",
    "llc_load_access",
    "llc_load_miss",
    "llc_rfo_access",
    "llc_rfo_miss",
    "stlb_total_access",
    "stlb_total_miss",
    "fdip_l1i_hit_covered",
    "fdip_l1i_hit_non_prefetch",
    "fdip_l1i_late_prefetch_merge",
    "fdip_l1i_merge_non_prefetch",
    "fdip_l1i_miss",
    "fdip_l1i_total",
    "fdip_l1i_covered_pct",
    "fdip_l1i_miss_pct",
]


def normalize_cache_name(name):
    if "_" in name and name.startswith("cpu"):
        return name.split("_", 1)[1]
    return name


def to_float(value):
    if value in ("", None):
        return ""
    return float(value)


def mpki(misses, instructions):
    if not instructions:
        return ""
    return misses / instructions * 1000


def pct(part, total):
    if not total:
        return ""
    return part / total * 100


def read_config_signature(run_dir):
    for directory in (run_dir, *run_dir.parents):
        signature_file = directory / "config_signature.txt"
        if signature_file.exists():
            return signature_file.read_text(encoding="utf-8").strip()
    return "unknown"


def get_run_id(run_dir):
    if run_dir.parent.name == "raw" and run_dir.name.startswith("fdip_"):
        return run_dir.parent.parent.name
    return run_dir.name


def parse_log_path(run_dir, log_path, default_config):
    rel = log_path.relative_to(run_dir)
    parts = rel.parts

    trace_set = parts[0] if len(parts) > 2 else ""
    trace_group = parts[1] if len(parts) > 2 else ""
    filename = log_path.name

    if "---" in filename:
        config, trace = filename.split("---", 1)
    else:
        config, trace = default_config, filename

    if trace.endswith(".log"):
        trace = trace[:-4]

    return {
        "run_id": get_run_id(run_dir),
        "config": config,
        "trace_set": trace_set,
        "trace_group": trace_group,
        "trace": trace,
    }


def parse_log(run_dir, log_path, default_config):
    row = {field: "" for field in FIELDNAMES}
    row.update(parse_log_path(run_dir, log_path, default_config))

    text = log_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        row["status"] = "failed"
        row["reason"] = "empty log"
        return row

    if "Failed trace:" in text:
        row["status"] = "failed"
        row["reason"] = text.split("Failed trace:", 1)[1].splitlines()[0].strip()
    elif "Segmentation fault" in text:
        row["status"] = "failed"
        row["reason"] = "segmentation fault"
    elif "ChampSim completed all CPUs" in text:
        row["status"] = "ok"
    else:
        row["status"] = "incomplete"

    cache_stats = {}
    fdip_stats = {}
    in_fdip_breakdown = False

    for line in text.splitlines():
        stripped = line.strip()
        ipc_match = IPC_RE.search(line)
        if ipc_match:
            row["ipc"] = ipc_match.group("ipc")
            row["instructions"] = ipc_match.group("instructions")
            row["cycles"] = ipc_match.group("cycles")
            continue

        branch_match = BRANCH_RE.search(line)
        if branch_match:
            row["branch_accuracy"] = branch_match.group("accuracy")
            row["branch_mpki"] = branch_match.group("mpki")
            continue

        cache_match = CACHE_RE.search(line)
        if cache_match:
            cache = normalize_cache_name(cache_match.group("cache"))
            kind = cache_match.group("kind").lower()
            cache_stats[(cache, kind)] = {
                "access": int(cache_match.group("access")),
                "hit": int(cache_match.group("hit")),
                "miss": int(cache_match.group("miss")),
                "miss_merge": int(cache_match.group("miss_merge")),
            }

        if stripped == "==== L1I Demand Access Breakdown ====":
            in_fdip_breakdown = True
            continue

        if in_fdip_breakdown:
            fdip_match = FDIP_BREAKDOWN_RE.search(stripped)
            if fdip_match:
                field = FDIP_LABELS.get(fdip_match.group("label"))
                if field:
                    fdip_stats[field] = int(fdip_match.group("count"))
                continue

            if "Sum of Components" in stripped or stripped == "":
                in_fdip_breakdown = False

    instructions = int(row["instructions"]) if row["instructions"] else 0

    for cache in ("L1D", "L2C", "LLC"):
        cache_key = cache.lower()
        load = cache_stats.get((cache, "load"), {})
        rfo = cache_stats.get((cache, "rfo"), {})
        total_misses = load.get("miss", 0) + rfo.get("miss", 0)

        row[f"{cache_key}_load_access"] = load.get("access", "")
        row[f"{cache_key}_load_miss"] = load.get("miss", "")
        row[f"{cache_key}_rfo_access"] = rfo.get("access", "")
        row[f"{cache_key}_rfo_miss"] = rfo.get("miss", "")
        row[f"{cache_key}_mpki"] = mpki(total_misses, instructions)

    llc_total = cache_stats.get(("LLC", "total"), {})
    row["llc_total_access"] = llc_total.get("access", "")
    row["llc_total_miss"] = llc_total.get("miss", "")
    row["on_chip_traffic_mpki"] = mpki(llc_total.get("access", 0), instructions)
    row["off_chip_traffic_mpki"] = mpki(llc_total.get("miss", 0), instructions)

    stlb_total = cache_stats.get(("STLB", "total"), {})
    row["stlb_total_access"] = stlb_total.get("access", "")
    row["stlb_total_miss"] = stlb_total.get("miss", "")
    row["stlb_mpki"] = mpki(stlb_total.get("miss", 0), instructions)

    for field in FDIP_LABELS.values():
        row[field] = fdip_stats.get(field, "")

    fdip_total = sum(fdip_stats.get(field, 0) for field in FDIP_LABELS.values())
    if fdip_total:
        row["fdip_l1i_total"] = fdip_total
        row["fdip_l1i_covered_pct"] = pct(fdip_stats.get("fdip_l1i_hit_covered", 0), fdip_total)
        row["fdip_l1i_miss_pct"] = pct(fdip_stats.get("fdip_l1i_miss", 0), fdip_total)

    if row["status"] == "ok" and not row["ipc"]:
        row["status"] = "incomplete"
        row["reason"] = "missing ipc"

    return row


def iter_logs(run_dir):
    for path in sorted(run_dir.rglob("*.log")):
        if path.name == "run.log":
            continue
        yield path


def main():
    parser = argparse.ArgumentParser(description="Parse ChampSim output logs into CSV.")
    parser.add_argument("run_dir", help="Run output directory, e.g. outputs/260706_1545")
    parser.add_argument("-o", "--output", help="CSV output path. Defaults to stdout.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        raise SystemExit(f"Run directory not found: {run_dir}")

    default_config = read_config_signature(run_dir)
    rows = [parse_log(run_dir, path, default_config) for path in iter_logs(run_dir)]

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    output = open(args.output, "w", newline="", encoding="utf-8") if args.output else sys.stdout
    try:
        writer = csv.DictWriter(output, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if args.output:
            output.close()


if __name__ == "__main__":
    main()
