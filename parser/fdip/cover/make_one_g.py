import os
import re
import glob
import argparse
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Configuration from fdip_cover.py
LABELS = [
    'L1I Hit (FDIP Covered)',
    'L1I Hit (Non-Prefetch)',
    'L1I Merge (Non-Prefetch)',
    'L1I Late Prefetch (Merge)',
    'L1I Miss'
]

SHORT_LABELS = [
    'Hit (FDIP)',
    'Hit (Base)',
    'Merge (Base)',
    'Merge (FDIP)',
    'Miss'
]

COLORS = ['#2ca02c', '#1f77b4', '#aec7e8', '#98df8a', '#d62728']

def parse_file(filepath):
    """
    Parses a single text file to extract category percentages.
    """
    data = {}
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
        start_parsing = False
        for line in lines:
            if "Category" in line and "Percent" in line:
                start_parsing = True
                continue
            if start_parsing:
                if "TOTAL" in line or "-------" in line:
                    continue
                if not line.strip():
                    continue
                
                parts = line.split('|')
                if len(parts) >= 3:
                    category = parts[0].strip()
                    try:
                        percent_str = parts[2].strip().replace('%', '')
                        percent = float(percent_str)
                        data[category] = percent
                    except ValueError:
                        pass
            
            # Check for Average IPC (outside or inside table parsing logic, usually at end)
            if "Average IPC:" in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    try:
                        data['IPC'] = float(parts[1].strip())
                    except ValueError:
                        pass
                        
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None
    return data

def get_data_for_prefix(prefix):
    """
    Finds files matching {prefix}_fdip_*.txt in the same directory as this script.
    Returns a DataFrame indexed by FTQ Size (int).
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    files = glob.glob(os.path.join(script_dir, f"{prefix}_fdip_*.txt"))
    results = {}

    # Always include no_fdip.txt as baseline (Size 0)
    no_fdip_path = os.path.join(script_dir, "no_fdip.txt")
    if os.path.exists(no_fdip_path):
        data = parse_file(no_fdip_path)
        if data:
            row = {label: data.get(label, 0.0) for label in LABELS}
            if 'IPC' in data:
                row['IPC'] = data['IPC']
            results[0] = row # 0 represents No FDIP

    for f in files:
        # Extract size from filename: s_fdip_64.txt -> 64
        match = re.search(r'fdip_(\d+)\.txt$', f)
        if match:
            size = int(match.group(1))
            data = parse_file(f)
            if data:
                # Ensure all logical keys exist, default to 0
                row = {label: data.get(label, 0.0) for label in LABELS}
                if 'IPC' in data:
                    row['IPC'] = data['IPC']
                results[size] = row
                
    df = pd.DataFrame(results).T # Transpose: Index=Size, Cols=Categories
    if not df.empty:
        df = df.sort_index()
    return df

def get_data_from_summary(summary_dir):
    """
    Reads fdip_cover.py's .txt reports under summary_dir, keyed by L2C policy.

    run.sh writes them as either:
      summary/fdip_<n>/<policy>/fdip_<n>_<policy>.txt   (with -L2C policies)
      summary/fdip_<n>/fdip_<n>_<policy>.txt            (legacy/no -L2C, policy="legacy")
    Both filename forms carry the policy suffix, so we parse ftq size and
    policy from the filename itself rather than assuming a fixed directory
    depth.

    Returns {policy: DataFrame indexed by FTQ Size (int)}.
    """
    files = glob.glob(os.path.join(summary_dir, "fdip_*", "**", "fdip_*.txt"), recursive=True)
    by_policy = {}

    name_re = re.compile(r'^fdip_(\d+)_(.+)\.txt$')
    for f in files:
        match = name_re.match(os.path.basename(f))
        if not match:
            continue

        size = int(match.group(1))
        policy = match.group(2)
        data = parse_file(f)
        if data:
            row = {label: data.get(label, 0.0) for label in LABELS}
            if 'IPC' in data:
                row['IPC'] = data['IPC']
            by_policy.setdefault(policy, {})[size] = row

    result = {}
    for policy, results in by_policy.items():
        df = pd.DataFrame(results).T
        if not df.empty:
            df = df.sort_index()
        result[policy] = df
    return result

def plot_config_on_ax(df, config_name, ax, *, legend=True, title_fontsize=14, label_fontsize=12):
    """Draws one L1I breakdown + IPC panel into `ax`. Returns the twinx IPC
    axis if one was created (so callers can share/suppress its legend), or
    None if there was no IPC column or no data.
    """
    if df.empty:
        ax.set_title(f'{config_name} (no data)', fontsize=title_fontsize, fontweight='bold')
        ax.axis('off')
        return None

    # Labels in code order: 0:Hit(FDIP), 1:Hit(Base), 2:Merge(Base), 3:Merge(FDIP), 4:Miss
    # plot(stacked=True) stacks columns bottom-to-top in column order, so
    # df columns must already be in that bottom-to-top order.
    df_bars = df[LABELS]

    df_bars.plot(kind='bar', stacked=True, ax=ax, color=COLORS, width=0.6, edgecolor='black', linewidth=0.5, legend=False)

    ax.set_title(f'L1I Demand Access Breakdown - {config_name}', fontsize=title_fontsize, fontweight='bold')
    ax.set_xlabel('FTQ Size', fontsize=label_fontsize)
    ax.set_ylabel('Percentage (%)', fontsize=label_fontsize)
    ax.set_ylim(0, 100)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(axis='x', rotation=0)

    new_labels = ["No FDIP" if idx == 0 else str(idx) for idx in df.index]
    ax.set_xticklabels(new_labels)

    ax2 = None
    if 'IPC' in df.columns:
        ax2 = ax.twinx()
        x_indices = np.arange(len(df))
        ax2.plot(x_indices, df['IPC'], color='black', marker='o', linewidth=2, linestyle='-', label='Average IPC')
        for x, y in zip(x_indices, df['IPC']):
            ax2.text(x, y, f'{y:.4f}', ha='center', va='bottom', fontsize=9, color='black', fontweight='bold')
        ax2.set_ylabel('IPC', fontsize=label_fontsize, color='black')
        ax2.tick_params(axis='y', labelcolor='black')
        max_ipc = df['IPC'].max()
        if max_ipc > 0:
            ax2.set_ylim(0, max_ipc * 1.2)

    if legend:
        short_labels_map = dict(zip(LABELS, SHORT_LABELS))
        handles1, labels1 = ax.get_legend_handles_labels()
        new_labels1 = [short_labels_map.get(l, l) for l in labels1]
        final_handles = list(reversed(handles1))
        final_labels = list(reversed(new_labels1))
        if ax2 is not None:
            handles2, labels2 = ax2.get_legend_handles_labels()
            final_handles += handles2
            final_labels += labels2
        ax.legend(final_handles, final_labels, title='Category', bbox_to_anchor=(1.08, 1), loc='upper left')

    # Add value annotations for significant segments
    for c in ax.containers:
        labels_arr = []
        for v in c:
            height = v.get_height()
            labels_arr.append(f'{height:.1f}' if height >= 2.0 else '')
        ax.bar_label(c, labels=labels_arr, label_type='center', fontsize=8, color='white', fontweight='bold')

    return ax2


def plot_config(df, config_name, output_filename):
    if df.empty:
        print(f"No data found for configuration: {config_name}")
        return

    fig, ax = plt.subplots(figsize=(12, 7))
    plot_config_on_ax(df, config_name, ax)
    plt.tight_layout()
    plt.savefig(output_filename, dpi=300)
    print(f"Graph saved to {os.path.abspath(output_filename)}")
    plt.close(fig)


# Fixed 2x2 layout: shared top-left, 2i6d top-right, 4i4d bottom-left, 6i2d
# bottom-right. Any policy not in this set is dropped from the combined grid
# (kept for the single-policy plot_config path, which has no layout to fit).
POLICY_GRID = [["shared", "2i6d"], ["4i4d", "6i2d"]]


def plot_combined_grid(by_policy, output_filename):
    n_rows = len(POLICY_GRID)
    n_cols = len(POLICY_GRID[0])
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(9 * n_cols, 6 * n_rows))

    for r, row in enumerate(POLICY_GRID):
        for c, policy in enumerate(row):
            df = by_policy.get(policy, pd.DataFrame())
            plot_config_on_ax(df, policy, axes[r][c], legend=False, title_fontsize=12, label_fontsize=10)

    # One shared legend built from the fixed category list (not per-panel,
    # since all panels use the same categories/colors) plus the IPC line.
    short_labels_map = dict(zip(LABELS, SHORT_LABELS))
    bar_handles = [plt.Rectangle((0, 0), 1, 1, color=color) for color in COLORS]
    bar_labels = [short_labels_map[label] for label in LABELS]
    ipc_handle = plt.Line2D([0], [0], color='black', marker='o', linewidth=2, linestyle='-')
    handles = list(reversed(bar_handles)) + [ipc_handle]
    labels = list(reversed(bar_labels)) + ['Average IPC']
    fig.legend(handles, labels, title='Category', loc='upper center', ncol=len(labels), bbox_to_anchor=(0.5, 1.04), fontsize=10)

    fig.suptitle('L1I Demand Access Breakdown by L2C policy', fontsize=16, fontweight='bold', y=1.09)
    fig.tight_layout(rect=(0, 0, 1, 1.0))
    fig.savefig(output_filename, dpi=200, bbox_inches='tight')
    print(f"Graph saved to {os.path.abspath(output_filename)}")
    plt.close(fig)

def main():
    parser = argparse.ArgumentParser(description='Generate combined FDIP cover graph.')
    parser.add_argument('--summary-dir', help='Run summary directory containing fdip_*/fdip_*.txt reports')
    parser.add_argument('--output', help='Output PNG path for --summary-dir mode')
    args = parser.parse_args()

    if args.summary_dir:
        summary_dir = os.path.abspath(args.summary_dir)
        base_output = args.output if args.output else os.path.join(summary_dir, 'fdip_breakdown_combined.png')
        by_policy = get_data_from_summary(summary_dir)
        if not by_policy:
            print("No data found for configuration: FDIP Cover")
            return

        # Single-policy runs (legacy, or -L2C with just one bit set) don't
        # need the 2x2 grid -- just plot that one policy directly.
        if len(by_policy) == 1:
            ((policy, df),) = by_policy.items()
            plot_config(df, f'FDIP Cover ({policy})', base_output)
        else:
            plot_combined_grid(by_policy, base_output)
        return

    # Configurations
    configs = [
        ('pf', 'Perfect Path FDIP'),
        ('s', 'Stop/Reverted FDIP'),
        ('wp', 'Wrong Path FDIP') # Future proofing
    ]
    
    for prefix, name in configs:
        df = get_data_for_prefix(prefix)
        plot_config(df, name, f'{prefix}_fdip_breakdown_combined.png')

if __name__ == "__main__":
    main()
