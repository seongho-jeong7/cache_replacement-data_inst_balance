import gzip
import re
import sys
import os
import argparse
import matplotlib.pyplot as plt
import numpy as np

def parse_log_file(file_path):
    """
    Parses a single .log.gz/.log file and extracts L1I Demand Access Breakdown statistics.
    Returns a dict with keys:
    'L1I Hit (FDIP Covered)'
    'L1I Hit (Non-Prefetch)'
    'L1I Late Prefetch (Merge)'
    'L1I Merge (Non-Prefetch)'
    'L1I Miss'
    """
    stats = {
        'L1I Hit (FDIP Covered)': 0,
        'L1I Hit (Non-Prefetch)': 0,
        'L1I Late Prefetch (Merge)': 0,
        'L1I Merge (Non-Prefetch)': 0,
        'L1I Miss': 0,
        'IPC': 0.0
    }
    
    found_section = False
    data_captured = False
    last_ipc = 0.0
    
    try:
        if file_path.endswith('.gz'):
            opener = gzip.open
        else:
            opener = open
            
        with opener(file_path, 'rt', errors='replace') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line = line.strip()
            if line == "==== L1I Demand Access Breakdown ====":
                found_section = True
                continue
            
            if found_section:
                # We expect the next few lines to contain the data
                # Format: Label : Count (Percentage)
                if ":" in line:
                    parts = line.split(":")
                    label_part = parts[0].strip()
                    val_part = parts[1].strip()
                    
                    # Check if this label is one of ours
                    if label_part in stats:
                        # Extract count. val_part looks like "26915 (  0.13%)" or just "26915"
                        # We split by ' ' or '('
                        val_str = val_part.split('(')[0].strip()
                        if val_str.isdigit():
                            stats[label_part] = int(val_str)
                
                # Stop if we hit the Sum check or empty line or next section
                # Stop if we hit the Sum check or empty line or next section
                if "Sum of Components" in line or line == "":
                    # assuming the block is contiguous
                    if "Sum of Components" in line:
                         found_section = False
                         data_captured = True # Successfully passed the block
            
            # Search for IPC line
            # "CPU 0 cumulative IPC: 0.5801 instructions: 200000001 cycles: 344746624"
            if "CPU 0 cumulative IPC:" in line:
                try:
                    parts = line.split()
                    if "IPC:" in parts:
                        idx = parts.index("IPC:")
                        last_ipc = float(parts[idx+1])
                except:
                    pass

    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None
        
    # Return stats only if we found the section, otherwise maybe return None or zeros
    if not data_captured:
        return None
        
    stats['IPC'] = last_ipc
    return stats

def plot_breakdown(avg_stats, output_path):
    # Order (Bottom to Top) for Stacking
    # User Request (Top to Bottom): Miss, FDIP Merge, Merge, Base Hit, FDIP Hit
    # So Bottom to Top: FDIP Hit, Base Hit, Merge, FDIP Merge, Miss
    labels = [
        'L1I Hit (FDIP Covered)',
        'L1I Hit (Non-Prefetch)',
        'L1I Merge (Non-Prefetch)',
        'L1I Late Prefetch (Merge)',
        'L1I Miss'
    ]
    
    # shorten labels for legend
    short_labels = [
        'Hit (FDIP)',
        'Hit (Base)',
        'Merge (Base)',
        'Merge (FDIP)',
        'Miss'
    ]
    
    # Colors corresponding to the above order
    # FDIP Hit: Green, Base Hit: Blue, Merge Base: Light Blue, Merge FDIP: Light Green, Miss: Red
    colors = ['#2ca02c', '#1f77b4', '#aec7e8', '#98df8a', '#d62728']
    
    counts = [avg_stats[l] for l in labels]
    total = sum(counts)
    
    if total == 0:
        print("Total count is 0, skipping plot.")
        return

    percentages = [c / total * 100.0 for c in counts]
    
    fig, ax = plt.subplots(figsize=(6, 8))
    
    # Draw Single Stacked Bar
    bottom = 0
    x_pos = ['Average']
    
    # To accumulate handles/labels for reversed legend
    legend_handles = []
    legend_labels = []
    
    for i, (pct, label, color) in enumerate(zip(percentages, short_labels, colors)):
        bars = ax.bar(x_pos, pct, bottom=bottom, label=label, color=color, width=0.5)
        
        # Store handle for legend
        legend_handles.append(bars[0])
        legend_labels.append(label)
        
        # Annotate text
        if pct > 1.0: 
            y_center = bottom + pct / 2
            # Use white for dark colors (Hit FDIP/Base, Miss), black for light (Merge Base/FDIP)
            # Indices: 0(Green), 1(Blue), 2(Light Blue), 3(Light Green), 4(Red)
            # 2 and 3 are light.
            text_color = 'black' if i in [2, 3] else 'white'
            ax.text(0, y_center, f'{pct:.2f}%', ha='center', va='center', 
                    color=text_color, fontweight='bold')
            
        bottom += pct
    
    ax.set_ylabel('Percentage (%)')
    ax.set_title('Average L1I Demand Access Breakdown')
    ax.set_ylim(0, 100)
    
    # Reverse legend order to match stacked bar (Top to Bottom)
    ax.legend(reversed(legend_handles), reversed(legend_labels), bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Graph saved to {output_path}")

def write_txt_report(avg_stats, num_files, output_path):
    labels = [
        'L1I Hit (FDIP Covered)',
        'L1I Hit (Non-Prefetch)',
        'L1I Late Prefetch (Merge)',
        'L1I Merge (Non-Prefetch)',
        'L1I Miss'
    ]
    
    counts = [avg_stats[l] for l in labels]
    total = sum(counts)
    
    with open(output_path, 'w') as f:
        f.write(f"L1I Demand Access Breakdown Analysis\n")
        f.write(f"====================================\n")
        f.write(f"Number of traces averaged: {num_files}\n\n")
        f.write(f"{'Category':<30} | {'Avg Count':<15} | {'Percent':<10}\n")
        f.write("-" * 65 + "\n")
        
        for label, count in zip(labels, counts):
            pct = (count / total * 100.0) if total > 0 else 0.0
            f.write(f"{label:<30} | {count:15.2f} | {pct:9.2f}%\n")
            
        f.write("-" * 65 + "\n")
        f.write(f"{'TOTAL':<30} | {total:15.2f} | 100.00%\n")
        f.write("-" * 65 + "\n")
        f.write(f"Average IPC: {avg_stats.get('IPC', 0.0):.4f}\n")
        
    print(f"Text report saved to {output_path}")

def get_files_from_path(path):
    if os.path.isfile(path):
        if path.endswith('.log') or path.endswith('.log.gz'):
             yield path
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.log') or file.endswith('.log.gz'):
                    yield os.path.join(root, file)

def main():
    parser = argparse.ArgumentParser(description='Analyze L1I FDIP Stats from ChampSim logs.')
    parser.add_argument('inputs', nargs='+', help='List of files or directories')
    parser.add_argument('-o', '--name', default='fdip', help='Output filename stem (default: fdip)')
    parser.add_argument('--output-dir', help='Directory to write PNG/TXT reports. Defaults to ./fdip_cover next to this script.')
    parser.add_argument('--quiet', action='store_true', help='Do not print every processed log file.')
    
    args = parser.parse_args()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = args.output_dir if args.output_dir else os.path.join(script_dir, 'fdip_cover')
    os.makedirs(output_dir, exist_ok=True)
    
    total_stats = {
        'L1I Hit (FDIP Covered)': 0,
        'L1I Hit (Non-Prefetch)': 0,
        'L1I Late Prefetch (Merge)': 0,
        'L1I Merge (Non-Prefetch)': 0,
        'L1I Miss': 0,
        'IPC': 0.0
    }
    
    file_count = 0
    
    for input_path in args.inputs:
        for file_path in get_files_from_path(input_path):
            if not args.quiet:
                print(f"Processing: {file_path}", end='\r')
            data = parse_log_file(file_path)
            if data:
                file_count += 1
                for k, v in data.items():
                    total_stats[k] += v
                    
    print(f"\nTotal files processed: {file_count}")
    
    if file_count > 0:
        # Calculate Averages
        avg_stats = {k: v / file_count for k, v in total_stats.items()}
        
        plot_path = os.path.join(output_dir, f'{args.name}.png')
        txt_path = os.path.join(output_dir, f'{args.name}.txt')
        
        plot_breakdown(avg_stats, plot_path)
        write_txt_report(avg_stats, file_count, txt_path)
        
    else:
        print("No valid data found.")

if __name__ == "__main__":
    main()
