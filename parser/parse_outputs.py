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
    r"(?P<kind>TOTAL|LOAD|RFO|PREFETCH|WRITE|TRANSLATION)(?P<origin>_I|_D)?\s+"
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

FRONTEND_STALL_RE = re.compile(r"^(?P<label>L1I_MISS|NO_INSTR_TO_FETCH|BACKEND_FULL):\s*(?P<count>\d+)")

FRONTEND_STALL_LABELS = {
    "L1I_MISS": "frontend_stall_l1i_miss",
    "NO_INSTR_TO_FETCH": "frontend_stall_no_instr_to_fetch",
    "BACKEND_FULL": "frontend_stall_backend_full",
}

# @Minchan's pre-existing dispatch-stage stall breakdown (ROB/LQ/SQ full).
# Distinct from FRONTEND_STALL_* above: this is the true backend (post-decode,
# pre-execute) stall, while FRONTEND_STALL_* covers fetch->decode promotion.
BACKEND_STALL_RE = re.compile(r"^(?P<label>ROB_STALL|LQ_STALL|SQ_STALL):\s*(?P<count>\d+)")

BACKEND_STALL_LABELS = {
    "ROB_STALL": "backend_stall_rob",
    "LQ_STALL": "backend_stall_lq",
    "SQ_STALL": "backend_stall_sq",
}

# ROB_STALL sub-breakdown. The ChampSim log prints Average/Total/Counts blocks;
# metrics.csv uses the Total block because the top-level ROB/LQ/SQ stall fields
# are also cycle counts.
ROB_STALL_RE = re.compile(r"^(?P<label>ADDR_TRANS|REPLAY_LOAD|NON_REPLAY_LOAD):\s*(?P<count>\d+)")

ROB_STALL_LABELS = {
    "ADDR_TRANS": "rob_stall_addr_trans",
    "REPLAY_LOAD": "rob_stall_replay_load",
    "NON_REPLAY_LOAD": "rob_stall_non_replay_load",
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
    "l1i_mpki",
    "l1d_mpki",
    "l2c_mpki",
    "l2i_mpki",
    "l2d_mpki",
    "llc_mpki",
    "lli_mpki",
    "lld_mpki",
    "stlb_mpki",
    "on_chip_traffic_mpki",
    "off_chip_traffic_mpki",
    "l1i_load_access",
    "l1i_load_miss",
    "l1i_rfo_access",
    "l1i_rfo_miss",
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
    "frontend_stall_l1i_miss",
    "frontend_stall_no_instr_to_fetch",
    "frontend_stall_backend_full",
    "frontend_stall_l1i_miss_pct",
    "frontend_stall_no_instr_to_fetch_pct",
    "frontend_stall_backend_full_pct",
    "backend_stall_rob",
    "backend_stall_lq",
    "backend_stall_sq",
    "backend_stall_rob_pct",
    "backend_stall_lq_pct",
    "backend_stall_sq_pct",
    "rob_stall_addr_trans",
    "rob_stall_replay_load",
    "rob_stall_non_replay_load",
    "rob_stall_addr_trans_pct",
    "rob_stall_replay_load_pct",
    "rob_stall_non_replay_load_pct",
    "frontend_instruction_fetch_stall",
    "frontend_instruction_fetch_stall_pct",
    "backend_instruction_stall",
    "backend_instruction_stall_pct",
    "backend_data_stall",
    "backend_data_stall_pct",
]


def normalize_cache_name(name):
    if "_" in name and name.startswith("cpu"):
        name = name.split("_", 1)[1]
    split_l2_aliases = {
        "L2IC": "L2I",
        "L2DC": "L2D",
    }
    return split_l2_aliases.get(name, name)


def to_float(value):
    if value in ("", None):
        return ""
    return float(value)


def mpki(misses, instructions):
    if not instructions:
        return ""
    return misses / instructions * 1000


def cache_demand_stats(cache_stats, cache, suffix=""):
    load = cache_stats.get((cache, f"load{suffix}"))
    rfo = cache_stats.get((cache, f"rfo{suffix}"))
    if load is None and rfo is None:
        return None

    return {
        "load_access": (load or {}).get("access", 0),
        "load_miss": (load or {}).get("miss", 0),
        "rfo_access": (rfo or {}).get("access", 0),
        "rfo_miss": (rfo or {}).get("miss", 0),
    }


def demand_misses(stats):
    return stats["load_miss"] + stats["rfo_miss"]


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
    frontend_stall_stats = {}
    in_frontend_stall_breakdown = False
    backend_stall_stats = {}
    in_backend_stall_breakdown = False
    rob_stall_stats = {}
    in_rob_stall_breakdown = False
    rob_stall_section = ""

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
            origin = cache_match.group("origin")
            if origin:
                kind += origin.lower()
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

        if stripped == "====Frontend Stall Breakdown====":
            in_frontend_stall_breakdown = True
            continue

        if in_frontend_stall_breakdown:
            frontend_stall_match = FRONTEND_STALL_RE.search(stripped)
            if frontend_stall_match:
                field = FRONTEND_STALL_LABELS.get(frontend_stall_match.group("label"))
                if field:
                    frontend_stall_stats[field] = int(frontend_stall_match.group("count"))
                continue

            if stripped == "":
                in_frontend_stall_breakdown = False

        if stripped == "====Backend Stall Breakdown====":
            in_backend_stall_breakdown = True
            continue

        if in_backend_stall_breakdown:
            backend_stall_match = BACKEND_STALL_RE.search(stripped)
            if backend_stall_match:
                field = BACKEND_STALL_LABELS.get(backend_stall_match.group("label"))
                if field:
                    backend_stall_stats[field] = int(backend_stall_match.group("count"))
                continue

            if stripped == "":
                in_backend_stall_breakdown = False

        if stripped == "====ROB Stall Breakdown====":
            in_rob_stall_breakdown = True
            rob_stall_section = ""
            continue

        if in_rob_stall_breakdown:
            if stripped.startswith("===="):
                in_rob_stall_breakdown = False
                rob_stall_section = ""
            elif stripped.startswith("==") and stripped.endswith("=="):
                rob_stall_section = stripped.strip("= ").lower()
                continue
            elif rob_stall_section == "total":
                rob_stall_match = ROB_STALL_RE.search(stripped)
                if rob_stall_match:
                    field = ROB_STALL_LABELS.get(rob_stall_match.group("label"))
                    if field:
                        rob_stall_stats[field] = int(rob_stall_match.group("count"))
                    continue

    instructions = int(row["instructions"]) if row["instructions"] else 0
    cycles = int(row["cycles"]) if row["cycles"] else 0

    for cache in ("L1I", "L1D", "L2C", "LLC"):
        cache_key = cache.lower()
        demand = cache_demand_stats(cache_stats, cache) or {
            "load_access": "",
            "load_miss": "",
            "rfo_access": "",
            "rfo_miss": "",
        }

        if cache == "L2C" and demand["load_access"] == "":
            l2i_demand = cache_demand_stats(cache_stats, "L2I")
            l2d_demand = cache_demand_stats(cache_stats, "L2D")
            if l2i_demand is not None or l2d_demand is not None:
                l2i_demand = l2i_demand or {"load_access": 0, "load_miss": 0, "rfo_access": 0, "rfo_miss": 0}
                l2d_demand = l2d_demand or {"load_access": 0, "load_miss": 0, "rfo_access": 0, "rfo_miss": 0}
                demand = {
                    key: l2i_demand[key] + l2d_demand[key]
                    for key in ("load_access", "load_miss", "rfo_access", "rfo_miss")
                }

        row[f"{cache_key}_load_access"] = demand["load_access"]
        row[f"{cache_key}_load_miss"] = demand["load_miss"]
        row[f"{cache_key}_rfo_access"] = demand["rfo_access"]
        row[f"{cache_key}_rfo_miss"] = demand["rfo_miss"]
        if demand["load_miss"] == "":
            row[f"{cache_key}_mpki"] = ""
        else:
            row[f"{cache_key}_mpki"] = mpki(demand_misses(demand), instructions)

    # Origin-split demand MPKI. FDIP logs report instruction/data origins as
    # L2C LOAD_I/LOAD_D (always printed, zeroed when that origin is fully
    # bypassed). Split-L2 logs report the same meaning as separate physical
    # L2I/L2D caches, but a fully-bypassed side (0 ways) never gets its own
    # cache object, so its section is entirely absent from the log rather
    # than zeroed. Treat that absence as zero traffic -- not blank -- so
    # MPKI/delta math stays comparable between the two builds.
    l2_split_sources = {
        "i": ("l2i_mpki", "L2I"),
        "d": ("l2d_mpki", "L2D"),
    }
    is_split_l2_log = any(cache_demand_stats(cache_stats, split_cache) is not None for _, split_cache in l2_split_sources.values())
    for origin, (field, split_cache) in l2_split_sources.items():
        demand = cache_demand_stats(cache_stats, "L2C", f"_{origin}")
        if demand is None:
            demand = cache_demand_stats(cache_stats, split_cache)
        if demand is None and is_split_l2_log:
            demand = {"load_access": 0, "load_miss": 0, "rfo_access": 0, "rfo_miss": 0}
        row[field] = "" if demand is None else mpki(demand_misses(demand), instructions)

    for origin, field in {"i": "lli_mpki", "d": "lld_mpki"}.items():
        demand = cache_demand_stats(cache_stats, "LLC", f"_{origin}")
        row[field] = "" if demand is None else mpki(demand_misses(demand), instructions)

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

    for field in FRONTEND_STALL_LABELS.values():
        row[field] = frontend_stall_stats.get(field, "")
        row[f"{field}_pct"] = pct(frontend_stall_stats[field], cycles) if field in frontend_stall_stats else ""

    for field in BACKEND_STALL_LABELS.values():
        row[field] = backend_stall_stats.get(field, "")
        row[f"{field}_pct"] = pct(backend_stall_stats[field], cycles) if field in backend_stall_stats else ""

    for field in ROB_STALL_LABELS.values():
        row[field] = rob_stall_stats.get(field, "")
        row[f"{field}_pct"] = pct(rob_stall_stats[field], cycles) if field in rob_stall_stats else ""

    # User-facing combined stall classes for the current experiment notes.
    frontend_instruction_fetch = frontend_stall_stats.get("frontend_stall_l1i_miss")
    if frontend_instruction_fetch is not None:
        row["frontend_instruction_fetch_stall"] = frontend_instruction_fetch
        row["frontend_instruction_fetch_stall_pct"] = pct(frontend_instruction_fetch, cycles)

    backend_instruction_stall_parts = [
        backend_stall_stats.get("backend_stall_lq"),
        backend_stall_stats.get("backend_stall_sq"),
        rob_stall_stats.get("rob_stall_addr_trans"),
        rob_stall_stats.get("rob_stall_replay_load"),
    ]
    if any(value is not None for value in backend_instruction_stall_parts):
        backend_instruction_stall = sum(value or 0 for value in backend_instruction_stall_parts)
        row["backend_instruction_stall"] = backend_instruction_stall
        row["backend_instruction_stall_pct"] = pct(backend_instruction_stall, cycles)

    backend_data_stall = rob_stall_stats.get("rob_stall_non_replay_load")
    if backend_data_stall is not None:
        row["backend_data_stall"] = backend_data_stall
        row["backend_data_stall_pct"] = pct(backend_data_stall, cycles)

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
