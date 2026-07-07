import gzip
import re
import sys
import os
import argparse
import matplotlib.pyplot as plt
import numpy as np

def parse_log_file(file_path):
    """
    Parses a single .log.gz/.log file and extracts ITLB and Misprediction-ITLB statistics.
    Returns a nested dictionary: data[section][row_type][level] = count
    sections: 'General', 'Misprediction'
    row_types: 'ITLB_Hit', 'STLB_Hit', 'STLB_Miss'
    levels: 'L1I', 'L1D', 'L2C', 'LLC', 'MEM'
    """
    data = {
        'General': {'ITLB_Hit': {}, 'STLB_Hit': {}, 'STLB_Miss': {}},
        'Misprediction': {'ITLB_Hit': {}, 'STLB_Hit': {}, 'STLB_Miss': {}}
    }
    
    # Regex to capture the row label and the 5 values (ignoring percentages)
    # Row examples: 
    #   ITLB hit → final level ...
    #   STLB hit → final level ...
    #   STLB miss → final level ...
    # Values might be "123" or "123 (45.6%)" depending on the log version. 
    # We will look for 5 number groups.
    
    # Flags to track current section
    current_section = None # 'General' or 'FDIP'
    
    levels = ['L1I', 'L1D', 'L2C', 'LLC', 'MEM']
    
    try:
        if file_path.endswith('.gz'):
            opener = gzip.open
        else:
            opener = open
            
        with opener(file_path, 'rt', errors='replace') as f:
            for line in f:
                line = line.strip()
                
                # Detect Section Headers
                # "ITLB" is the header for general. 
                # "[FDIP Post-Mispred] ITLB" is for FDIP.
                # Note: "[FDIP Post-Mispred] ITLB" contains "ITLB", so check specific first.
                if line == "[FDIP Post-Mispred] ITLB":
                    current_section = 'Misprediction'
                    continue
                elif line == "ITLB":
                    current_section = 'General'
                    continue
                
                if current_section is None:
                    continue

                # Detect Rows
                row_type = None
                if line.startswith("ITLB hit → final level"):
                    row_type = 'ITLB_Hit'
                elif line.startswith("STLB hit → final level"):
                    row_type = 'STLB_Hit'
                elif line.startswith("STLB miss → final level"):
                    row_type = 'STLB_Miss'
                
                if row_type:
                    # Extract numbers. 
                    # If format is "123 (45%)", we want 123.
                    # If format is "123", we want 123.
                    # We can pick all non-parenthesized numbers?
                    # Regex: find digits that are NOT preceded by inside of parenthesis?
                    # Simpler: Split by whitespace, ignore tokens starting with '('. 
                    # Actually, the format is strict: "Label... val1 (pct1) val2 (pct2) ..." 
                    # Let's use regex to find sequences of digits that are followed by space or (
                    
                    # Pattern: find all integer numbers.
                    # But we must be careful not to pick up the percentages if they are integers (e.g. (100%)).
                    # If user output is `23640 (66.4%)`, the `66` and `4` are digits.
                    # Strategy: Remove everything within parenthesis first.
                    
                    clean_line = re.sub(r'\(.*?\)', '', line)
                    # Now "ITLB hit → final level 23640 0 4389 616 6982"
                    
                    parts = clean_line.split()
                    # Filter out non-digits (the label parts)
                    numbers = [int(p) for p in parts if p.isdigit()]
                    
                    # We expect exactly 5 numbers corresponding to L1I, L1D, L2C, LLC, MEM
                    if len(numbers) >= 5:
                        # Take the last 5 numbers found in the line (safety)
                        counts = numbers[-5:]
                        for i, level in enumerate(levels):
                            data[current_section][row_type][level] = counts[i]
                            
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None
        
    return data

def aggregate_data(aggregated, new_data):
    """Sum up counts from new_data into aggregated."""
    for section in ['General', 'Misprediction']:
        for row_type in ['ITLB_Hit', 'STLB_Hit', 'STLB_Miss']:
            for level in ['L1I', 'L1D', 'L2C', 'LLC', 'MEM']:
                val = new_data[section][row_type].get(level, 0)
                current = aggregated[section][row_type].get(level, 0)
                aggregated[section][row_type][level] = current + val

def plot_comparison(aggregated_data, output_png):
    """
    Generates a figure with 4 subplots (ITLB Hit, STLB Hit, STLB Miss, Overall).
    In each subplot, compare General vs Misprediction distributions across 5 levels.
    """
    # Categories and Levels
    # We will simulate a 4th category 'Overall' by summing the first 3 on the fly
    row_types = ['ITLB_Hit', 'STLB_Hit', 'STLB_Miss', 'Overall']
    levels = ['L1I', 'L1D', 'L2C', 'LLC', 'MEM']
    sections = ['General', 'Misprediction']
    colors = {'General': '#1f77b4', 'Misprediction': '#ff7f0e'} # Blue, Orange

    # Change to 3x2 grid
    fig, axes = plt.subplots(3, 2, figsize=(14, 15)) # Increased height for 3 rows
    axes = axes.flatten()
    
    # 1. Plot the 4 Distribution Graphs (Slots 0-3)
    for idx, r_type in enumerate(row_types):
        ax = axes[idx]
        
        x = np.arange(len(levels))
        width = 0.35
        
        for i, section in enumerate(sections):
            if r_type == 'Overall':
                # Sum up all 3 base types
                counts = []
                for lvl in levels:
                    s = 0
                    for base_type in ['ITLB_Hit', 'STLB_Hit', 'STLB_Miss']:
                        s += aggregated_data[section][base_type].get(lvl, 0)
                    counts.append(s)
            else:
                counts = [aggregated_data[section][r_type].get(lvl, 0) for lvl in levels]
                
            total = sum(counts)
            if total > 0:
                pcts = [c / total * 100.0 for c in counts]
            else:
                pcts = [0.0] * len(levels)
            
            label = section
            
            # Plot bar
            bars = ax.bar(x + (i - 0.5) * width, pcts, width, label=label, color=colors[section])
            
            # Add text on top
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.annotate(f'{height:.1f}%',
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3), 
                                textcoords="offset points",
                                ha='center', va='bottom', fontsize=8, rotation=0)

        title = r_type.replace('_', ' ')
        if r_type == 'Overall':
             title = "Overall Distribution (By Level)"
             
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(levels)
        ax.set_ylim(0, 110) 
        ax.grid(True, axis='y', linestyle='--', alpha=0.5)
        
        if idx % 2 == 0:
            ax.set_ylabel('Distribution (%)')
        
        if idx == 0:
            ax.legend()
            
    # 2. Plot 5: STLB Miss Rate (Overall) - Slot 4
    ax = axes[4]
    miss_rates = []
    
    for section in sections:
        total_access = 0
        total_miss = 0
        
        # Calculate totals
        for base_type in ['ITLB_Hit', 'STLB_Hit', 'STLB_Miss']:
            type_sum = sum(aggregated_data[section][base_type].values())
            total_access += type_sum
            if base_type == 'STLB_Miss':
                total_miss += type_sum
        
        if total_access > 0:
            rate = (total_miss / total_access) * 100.0
        else:
            rate = 0.0
        miss_rates.append(rate)
        
    x_pos = np.arange(len(sections))
    bars = ax.bar(x_pos, miss_rates, color=[colors[s] for s in sections])
    
    ax.set_title("Overall STLB Miss Rate (Total Miss / Total Access)")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(sections)
    ax.set_ylabel('Miss Rate (%)')
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    
    # Add text
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), 
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Slot 5 (Index 5) - Empty for now, or maybe STLB Hit Rate?
    # Let's hide it if not used
    axes[5].axis('off')
    
    plt.suptitle("ITLB Stats Distribution: General vs. Post-Misprediction", fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    if os.path.dirname(output_png):
        os.makedirs(os.path.dirname(output_png), exist_ok=True)
    plt.savefig(output_png)
    print(f"Plot saved: {output_png}")
    plt.close()

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
    parser = argparse.ArgumentParser(description='Analyze ITLB Stats (General vs Misprediction) from ChampSim logs.')
    parser.add_argument('inputs', nargs='+', help='List of files or directories')
    parser.add_argument('-o', '--output', default='itlb_comparison.png', help='Output PNG filename')
    
    args = parser.parse_args()
    
    # Initialize Aggregated Structure
    aggregated_data = {
        'General': {'ITLB_Hit': {}, 'STLB_Hit': {}, 'STLB_Miss': {}},
        'Misprediction': {'ITLB_Hit': {}, 'STLB_Hit': {}, 'STLB_Miss': {}}
    }
    
    files_processed = 0
    
    for input_path in args.inputs:
        for file_path in get_files_from_path(input_path):
            print(f"Processing: {file_path}", end='\r')
            data = parse_log_file(file_path)
            if data:
                aggregate_data(aggregated_data, data)
                files_processed += 1
                
    print(f"\nTotal files processed: {files_processed}")
    
    if files_processed > 0:
        plot_comparison(aggregated_data, args.output)
    else:
        print("No valid data found.")

if __name__ == "__main__":
    main()