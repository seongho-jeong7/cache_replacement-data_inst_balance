#!/usr/bin/env python3
import argparse
import csv
from collections import defaultdict
from pathlib import Path


METRICS = [
    "ipc",
    "branch_mpki",
    "l1i_mpki",
    "l1d_mpki",
    "l2i_mpki",
    "l2d_mpki",
    "l2c_mpki",
    "llc_mpki",
    "lli_mpki",
    "lld_mpki",
    "stlb_mpki",
    "on_chip_traffic_mpki",
    "off_chip_traffic_mpki",
    "fdip_l1i_covered_pct",
    "fdip_l1i_miss_pct",
    "frontend_stall_l1i_miss_pct",
    "frontend_stall_no_instr_to_fetch_pct",
    "frontend_stall_backend_full_pct",
]


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values):
    values = [value for value in values if value is not None]
    if not values:
        return None
    return sum(values) / len(values)


def fmt(value, width=8, precision=3):
    if value is None:
        return " " * (width - 1) + "-"
    return f"{value:{width}.{precision}f}"


def load_rows(metrics_csv):
    with metrics_csv.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def summarize(rows):
    grouped = defaultdict(list)
    for row in rows:
        key = (row.get("trace_set", ""), row.get("trace_group", ""))
        grouped[key].append(row)
    return grouped


def print_table(metrics_csv, mode="full"):
    rows = load_rows(metrics_csv)
    grouped = summarize(rows)
    ok_total = sum(1 for row in rows if row.get("status") == "ok")
    fail_total = len(rows) - ok_total

    header = "| Trace Set  | Group      | Total | OK  | Fail |"
    if mode == "minimal":
        header += " Avg IPC | L1I MPKI | L1D MPKI | L2I MPKI | L2D MPKI | LLI MPKI | LLD MPKI |"
    elif mode == "fdip":
        header += " FDIP Cov | L1I Miss | OnChip MPKI | OffChip MPKI |"
    elif mode == "frontend":
        header += " Avg IPC | L1I MPKI | L2I MPKI | L2D MPKI | L1I Stall% | NoFetch% | BackendFull% |"
    else:
        header += " Avg IPC | Br MPKI | L1I MPKI | L1D MPKI | L2C MPKI | LLC MPKI | STLB MPKI |"
    width = len(header)

    print(f"ChampSim Summary: {metrics_csv}")
    print(f"Traces: {len(rows)} total, {ok_total} ok, {fail_total} failed")
    print("-" * width)
    print(header)
    print("-" * width)

    for (trace_set, trace_group), group_rows in sorted(grouped.items()):
        ok_rows = [row for row in group_rows if row.get("status") == "ok"]
        values = {
            metric: mean(to_float(row.get(metric)) for row in ok_rows)
            for metric in METRICS
        }
        print(
            f"| {trace_set[:10]:<10} | {trace_group[:10]:<10} |"
            f" {len(group_rows):5d} | {len(ok_rows):3d} | {len(group_rows) - len(ok_rows):4d} |",
            end="",
        )
        if mode == "minimal":
            print(
                f"{fmt(values['ipc'], 8, 3)} |"
                f"{fmt(values['l1i_mpki'], 9, 2)} |"
                f"{fmt(values['l1d_mpki'], 9, 2)} |"
                f"{fmt(values['l2i_mpki'], 9, 2)} |"
                f"{fmt(values['l2d_mpki'], 9, 2)} |"
                f"{fmt(values['lli_mpki'], 9, 2)} |"
                f"{fmt(values['lld_mpki'], 9, 2)} |"
            )
        elif mode == "fdip":
            print(
                f"{fmt(values['fdip_l1i_covered_pct'], 9, 2)} |"
                f"{fmt(values['fdip_l1i_miss_pct'], 8, 2)} |"
                f"{fmt(values['on_chip_traffic_mpki'], 12, 2)} |"
                f"{fmt(values['off_chip_traffic_mpki'], 13, 2)} |"
            )
        elif mode == "frontend":
            print(
                f"{fmt(values['ipc'], 8, 3)} |"
                f"{fmt(values['l1i_mpki'], 9, 2)} |"
                f"{fmt(values['l2i_mpki'], 9, 2)} |"
                f"{fmt(values['l2d_mpki'], 9, 2)} |"
                f"{fmt(values['frontend_stall_l1i_miss_pct'], 11, 2)} |"
                f"{fmt(values['frontend_stall_no_instr_to_fetch_pct'], 9, 2)} |"
                f"{fmt(values['frontend_stall_backend_full_pct'], 13, 2)} |"
            )
        else:
            print(
                f"{fmt(values['ipc'], 8, 3)} |"
                f"{fmt(values['branch_mpki'], 8, 2)} |"
                f"{fmt(values['l1i_mpki'], 9, 2)} |"
                f"{fmt(values['l1d_mpki'], 9, 2)} |"
                f"{fmt(values['l2c_mpki'], 9, 2)} |"
                f"{fmt(values['llc_mpki'], 9, 2)} |"
                f"{fmt(values['stlb_mpki'], 9, 2)} |"
            )

    print("-" * width)


def main():
    parser = argparse.ArgumentParser(description="Print a summary table from metrics.csv.")
    parser.add_argument("metrics_csv", help="Path to metrics.csv")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--minimal",
        action="store_true",
        help="Print only Trace Set/Group/Total/OK/Fail/Avg IPC/L1I MPKI/L1D MPKI columns.",
    )
    mode_group.add_argument(
        "--fdip",
        action="store_true",
        help="Print only Trace Set/Group/Total/OK/Fail/FDIP Cov/L1I Miss columns.",
    )
    mode_group.add_argument(
        "--frontend",
        action="store_true",
        help="Print only Trace Set/Group/Total/OK/Fail/Avg IPC/L1I MPKI/frontend stall breakdown (L1I Stall%%/NoFetch%%/BackendFull%%) columns.",
    )
    args = parser.parse_args()

    metrics_csv = Path(args.metrics_csv)
    if not metrics_csv.is_file():
        raise SystemExit(f"metrics.csv not found: {metrics_csv}")

    mode = "minimal" if args.minimal else "fdip" if args.fdip else "frontend" if args.frontend else "full"
    print_table(metrics_csv, mode=mode)


if __name__ == "__main__":
    main()
