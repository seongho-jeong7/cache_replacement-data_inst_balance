#!/usr/bin/env python3
import argparse
import csv
from collections import defaultdict
from pathlib import Path


METRICS = [
    "ipc",
    "branch_mpki",
    "l1d_mpki",
    "l2c_mpki",
    "llc_mpki",
    "stlb_mpki",
    "off_chip_traffic_mpki",
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


def print_table(metrics_csv):
    rows = load_rows(metrics_csv)
    grouped = summarize(rows)
    ok_total = sum(1 for row in rows if row.get("status") == "ok")
    fail_total = len(rows) - ok_total

    print(f"ChampSim Summary: {metrics_csv}")
    print(f"Traces: {len(rows)} total, {ok_total} ok, {fail_total} failed")
    print("-" * 112)
    print(
        "| Trace Set  | Group      | Total | OK  | Fail |"
        " Avg IPC | Br MPKI | L1D MPKI | L2C MPKI | LLC MPKI | STLB MPKI | OffChip |"
    )
    print("-" * 112)

    for (trace_set, trace_group), group_rows in sorted(grouped.items()):
        ok_rows = [row for row in group_rows if row.get("status") == "ok"]
        values = {
            metric: mean(to_float(row.get(metric)) for row in ok_rows)
            for metric in METRICS
        }
        print(
            f"| {trace_set[:10]:<10} | {trace_group[:10]:<10} |"
            f" {len(group_rows):5d} | {len(ok_rows):3d} | {len(group_rows) - len(ok_rows):4d} |"
            f"{fmt(values['ipc'], 8, 3)} |"
            f"{fmt(values['branch_mpki'], 8, 2)} |"
            f"{fmt(values['l1d_mpki'], 9, 2)} |"
            f"{fmt(values['l2c_mpki'], 9, 2)} |"
            f"{fmt(values['llc_mpki'], 9, 2)} |"
            f"{fmt(values['stlb_mpki'], 9, 2)} |"
            f"{fmt(values['off_chip_traffic_mpki'], 8, 2)} |"
        )

    print("-" * 112)


def main():
    parser = argparse.ArgumentParser(description="Print a summary table from metrics.csv.")
    parser.add_argument("metrics_csv", help="Path to metrics.csv")
    args = parser.parse_args()

    metrics_csv = Path(args.metrics_csv)
    if not metrics_csv.is_file():
        raise SystemExit(f"metrics.csv not found: {metrics_csv}")

    print_table(metrics_csv)


if __name__ == "__main__":
    main()
