import gzip
import re
import sys
import os
import argparse
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm

def parse_log_file(file_path):
    """Parses a single .log.gz/.log file to extract counts from the Summary Table."""
    data = {}
    
    # We need to capture two things: 
    # 1. The main stats from the summary table (Reliable)
    # 2. The specific PTW patterns for ranking (from trace, optional/approximate if trace missing)
    
    # Trace pattern for detailed breakdown (optional)
    trace_pattern = re.compile(r'\[Fetch Latency\] instr_id: \d+ latency: \d+ cycle \(Translation: (\S+) Instruction: (\S+)\)')
    
    try:
        if file_path.endswith('.gz'):
            opener = gzip.open
        else:
            opener = open
            
        with opener(file_path, 'rt', errors='replace') as f:
            in_summary = False
            current_tlb_section = None # 'ITLB' or 'DTLB'
            cols = ['L1I', 'L1D', 'L2C', 'LLC', 'MEM']
            
            for line in f:
                line = line.strip()
                
                # 1. Parse Trace (Only for detailed PTW ranking if needed, or if we want to confirm misses)
                # For now, we will rely PRIMARILY on the table for the Matrix.
                if line.startswith("[Fetch Latency]"):
                   match = trace_pattern.search(line)
                   if match:
                       t_src = match.group(1)
                       d_src = match.group(2)
                       # We store this specifically for the "Ratio" or "Pattern" list, 
                       # but for the main Hit Map, we should overwrite/sum from the table?
                       # Actually, let's store trace data with a special prefix or just ignore it for the main table
                       # to avoid double counting.
                       # Decision: Only use trace for "Top STLB Miss Patterns" list if the table doesn't give enough detail.
                       # The table gives "resolved @ L2C", which implies PTW-L2C.
                       # So the table is sufficient for the matrix rows "PTW resolv @ ...".
                       # BUT the table sums DTLB and ITLB sections. We usually want just ITLB for Fetch Latency?
                       # The previous script was "Fetch Latency Hit Map".
                       # The user showed "ITLB" section in the terminal snippet. 
                       # If we want FETCH Hit Map, we should only parse "ITLB" section of the summary.
                       pass

                # 2. Detect Summary Table
                if "==== TLB→Cache/MEM Breakdown" in line:
                    in_summary = True
                    continue
                
                if not in_summary:
                    continue
                
                # Detect Section Header
                if line == "ITLB":
                    current_tlb_section = "ITLB"
                    continue
                elif line == "DTLB":
                    # IF we only want Fetch Hit Map, we might ignore DTLB.
                    # Previous script filtered `[Fetch Latency]` which implies ITLB-only (usually).
                    # User snippet shows ITLB. Let's assume we stick to ITLB for Fetch.
                    # If the tool is generic "Hit Map", maybe both?
                    # "Fetch Latency" in title implies ITLB.
                    current_tlb_section = "DTLB" 
                    # decision: Skip DTLB to maintain "Fetch" semantics unless user asked for both.
                    # User snippet shows ITLB.
                    continue
                
                if current_tlb_section == "ITLB" and line:
                    # Parse Rows
                    # Format: Label  val1 val2 val3 val4 val5
                    parts = line.split()
                    
                    # Heuristic to identify rows
                    label = None
                    values = []
                    
                    # "ITLB hit -> final level"
                    if "ITLB hit" in line and "final level" in line:
                        label = "ITLB"
                        values = parts[-5:]
                    # "STLB hit -> final level"
                    elif "STLB hit" in line and "final level" in line:
                        label = "STLB"
                        values = parts[-5:]
                    # "STLB miss -> final level" (Total)
                    elif "STLB miss" in line and "final level" in line:
                        # This is a summary row, we can skip or use check
                        continue
                    # "STLB miss resolved @ L1D"
                    elif "resolved @ L1D" in line:
                        label = "PTW-L1D"
                        values = parts[-5:]
                    elif "resolved @ L2C" in line:
                        label = "PTW-L2C"
                        values = parts[-5:]
                    elif "resolved @ LLC" in line:
                        label = "PTW-LLC"
                        values = parts[-5:]
                    elif "resolved @ MEM" in line:
                        label = "PTW-MEM"
                        values = parts[-5:]
                    
                    if label and len(values) == 5:
                        for i, val_str in enumerate(values):
                            try:
                                val = int(val_str)
                                target = cols[i] # L1I, L1D, ...
                                key = (label, target)
                                # data[key] = val (Overwrite or Add?)
                                # Since files might have multiple sections or we parse multiple files?
                                # This function is for ONE file.
                                # ITLB section appears once.
                                data[key] = val
                            except ValueError:
                                pass

    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None
        
    return data

def analyze_and_plot(data, output_txt, output_png, title_suffix=""):
    """Generates a formatted table and a heatmap."""
    if not data:
        return

    # proper mapping for columns and rows
    cols_data_src = ['L1I', 'L1D', 'L2C', 'LLC', 'MEM']
    
    # helper to safely get count
    def get_count(t_src, d_src):
        return data.get((t_src, d_src), 0)

    # 1. ITLB hit -> final level
    row_itlb = [get_count('ITLB', d) for d in cols_data_src]
    
    # 2. STLB hit -> final level
    row_stlb = [get_count('STLB', d) for d in cols_data_src]
    
    # 3. Breakdown rows
    row_ptw_l1d = [get_count('PTW-L1D', d) for d in cols_data_src]
    row_ptw_l2c = [get_count('PTW-L2C', d) for d in cols_data_src]
    row_ptw_llc = [get_count('PTW-LLC', d) for d in cols_data_src]
    row_ptw_mem = [get_count('PTW-MEM', d) for d in cols_data_src]
    
    # Total Miss Row
    row_stlb_miss_total = [0] * len(cols_data_src)
    for i in range(len(cols_data_src)):
         row_stlb_miss_total[i] = row_ptw_l1d[i] + row_ptw_l2c[i] + row_ptw_llc[i] + row_ptw_mem[i]

    # For heatmap specifically (matches previous plot_data structure)
    heatmap_data = np.array([
        row_itlb,
        row_stlb,
        row_ptw_l1d,
        row_ptw_l2c,
        row_ptw_llc,
        row_ptw_mem
    ])
    
    heat_rows_labels = [
        "ITLB hit",
        "STLB hit",
        "PTW resolv @ L1D",
        "PTW resolv @ L2C",
        "PTW resolv @ LLC",
        "PTW resolv @ MEM"
    ]

    # Calculate Percentages
    row_sums = heatmap_data.sum(axis=1)
    percent_data = np.zeros_like(heatmap_data, dtype=float)
    
    for i in range(len(row_sums)):
        if row_sums[i] > 0:
            percent_data[i] = (heatmap_data[i] / row_sums[i]) * 100.0

    # --- Generate Text Report ---
    lines = []
    lines.append(f"Analysis for: {title_suffix}")
    
    # Header
    header = f"{'(case)':<35} " + "".join([f"{c:<12}" for c in cols_data_src])
    lines.append("==== Raw Counts ====")
    lines.append(header)
    
    def format_row(label, values):
        row_str = f"{label:<35} " + "".join([f"{v:<12}" for v in values])
        return row_str
    
    def format_row_pct(label, values):
        total = sum(values)
        if total == 0:
            pcts = [0.0] * len(values)
        else:
            pcts = [(v/total)*100.0 for v in values]
        row_str = f"{label:<35} " + "".join([f"{p:<12.1f}" for p in pcts])
        return row_str

    # Table 1: Raw Counts
    lines.append(format_row("ITLB hit → final level", row_itlb))
    lines.append("-" * 95)
    lines.append(format_row("STLB hit → final level", row_stlb))
    lines.append(format_row("STLB miss → final level", row_stlb_miss_total))
    lines.append("-" * 95)
    lines.append(format_row("STLB miss resolved @ L1D", row_ptw_l1d))
    lines.append(format_row("STLB miss resolved @ L2C", row_ptw_l2c))
    lines.append(format_row("STLB miss resolved @ LLC", row_ptw_llc))
    lines.append(format_row("STLB miss resolved @ MEM", row_ptw_mem))
    lines.append("")
    
    # Table 2: Percentages
    lines.append("==== Row-wise Percentages (%) ====")
    lines.append(header)
    lines.append(format_row_pct("ITLB hit → final level", row_itlb))
    lines.append("-" * 95)
    lines.append(format_row_pct("STLB hit → final level", row_stlb))
    lines.append(format_row_pct("STLB miss → final level", row_stlb_miss_total))
    lines.append("-" * 95)
    lines.append(format_row_pct("STLB miss resolved @ L1D", row_ptw_l1d))
    lines.append(format_row_pct("STLB miss resolved @ L2C", row_ptw_l2c))
    lines.append(format_row_pct("STLB miss resolved @ LLC", row_ptw_llc))
    lines.append(format_row_pct("STLB miss resolved @ MEM", row_ptw_mem))
    
    os.makedirs(os.path.dirname(output_txt), exist_ok=True)
    os.makedirs(os.path.dirname(output_png), exist_ok=True)

    with open(output_txt, 'w') as f:
        f.write("\n".join(lines))
    print(f"Stats: {output_txt}")

    # --- Generate Heatmap ---
    # We use 'percent_data' for colors (0-100), 'heatmap_data' for text annotations (counts)
    
    plt.figure(figsize=(12, 8))
    
    # Use Linear Scale (0-100) for Percentages
    im = plt.imshow(percent_data, cmap='YlOrRd', aspect='auto', vmin=0, vmax=100)
    
    cbar = plt.colorbar(im)
    cbar.set_label('Row Percentage (%)')

    plt.xticks(np.arange(len(cols_data_src)), cols_data_src)
    plt.yticks(np.arange(len(heat_rows_labels)), heat_rows_labels)
    plt.setp(plt.gca().get_xticklabels(), rotation=0, ha="center", rotation_mode="anchor")

    for i in range(len(heat_rows_labels)):
        for j in range(len(cols_data_src)):
            count_val = heatmap_data[i, j]
            pct_val = percent_data[i, j]
            
            # Text: Count \n (Pct%)
            text_val = f"{count_val}\n({pct_val:.1f}%)"
            
            # Text Color Contrast
            color = "white" if pct_val > 50 else "black"
            
            plt.text(j, i, text_val, ha="center", va="center", color=color, fontsize=8)

    plt.title(f"Fetch Hit Map - {title_suffix}")
    plt.tight_layout()
    
    plt.savefig(output_png)
    plt.close()
    print(f"Plot: {output_png}")

def get_files_from_path(path):
    if os.path.isfile(path):
        if path.endswith('.log') or path.endswith('.log.gz'):
             yield path, os.path.basename(path)
    elif os.path.isdir(path):
        input_dir = os.path.normpath(path)
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.endswith('.log') or file.endswith('.log.gz'):
                    full_path = os.path.join(root, file)
                    yield full_path, file

def read_ranking_file(ranking_file_path):
    ranked_files = []
    try:
        with open(ranking_file_path, 'r') as f:
            lines = f.readlines()
            start_idx = 0
            for i, line in enumerate(lines):
                 if line.strip().startswith("-"):
                     start_idx = i + 1
                     break
            
            for line in lines[start_idx:]:
                parts = [p.strip() for p in line.strip().split('|')]
                if not parts or parts[0] == '': continue
                
                filename = parts[1]
                fullpath = parts[2] if len(parts) >= 3 else None
                
                entry = {'filename': filename, 'fullpath': fullpath}
                ranked_files.append(entry)
    except Exception as e:
        print(f"Error reading ranking file: {e}")
        return []
    return ranked_files

def find_file(filename, search_dir):
    if not search_dir: return None
    for root, _, files in os.walk(search_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None

def main():
    parser = argparse.ArgumentParser(description='Generate Hit Map from Logs or Ranking File.')
    parser.add_argument('inputs', nargs='+', help='List of files, directories, or a ranking file + search dir')
    parser.add_argument('--separate', action='store_true', help='Generate separate reports for each file')
    parser.add_argument('--top', type=int, help='Only aggregate the top N files (requires ranking file or will just take first N found)')
    
    args = parser.parse_args()
    
    files_to_process = [] # list of (fullpath, filename)
    base_output_dir = os.path.expanduser('~/melong/champsim_replay/script/hit_map')
    
    input_basename = "aggregated_results"
    
    if len(args.inputs) > 1:
        # Multiple inputs (likely wildcard expansion)
        # Try to find a common prefix for the basename
        basenames = [os.path.basename(os.path.normpath(p)) for p in args.inputs]
        common = os.path.commonprefix(basenames)
        if len(common) > 3: # arbitrary threshold to ensure it's not just a generic prefix
            input_basename = common.rstrip('-_ .')
        else:
             input_basename = "aggregated_results"
    else:
        # Single input
        first_input = args.inputs[0]
        if os.path.isdir(first_input):
            input_basename = os.path.basename(os.path.normpath(first_input))
        elif os.path.isfile(first_input):
            if first_input.endswith('.txt'):
                input_basename = os.path.basename(first_input).replace('.txt', '')
            else:
                 input_basename = "custom_selection"
    
    first_input = args.inputs[0]
    
    # Check if first input is a ranking file
    if os.path.isfile(first_input) and first_input.endswith('.txt'):
         print(f"Reading ranking file: {first_input}")
         ranking_entries = read_ranking_file(first_input)
         
         # Assuming second arg might be search dir if provided
         search_dir = args.inputs[1] if len(args.inputs) > 1 and os.path.isdir(args.inputs[1]) else None
         if search_dir:
             print(f"Using search directory: {search_dir}")

         for entry in ranking_entries:
             fpath = entry['fullpath']
             fname = entry['filename']
             
             if not fpath or not os.path.exists(fpath):
                 if search_dir:
                     found = find_file(fname, search_dir)
                     if found:
                         fpath = found
                     else:
                         print(f"Warning: Could not find {fname} in {search_dir}")
                         continue
                 else:
                     # If we can't find it, skip
                     continue
             
             files_to_process.append((fpath, fname))
             
    else:
        # Normal scan of all inputs
        print("Scanning inputs...")
        for inp in args.inputs:
            for full_path, filename in get_files_from_path(inp):
                files_to_process.append((full_path, filename))

    if not files_to_process:
        print("No files found.")
        sys.exit(0)

    # Apply Top N Filter
    if args.top is not None:
        print(f"Filtering Top {args.top} files...")
        files_to_process = files_to_process[:args.top]
        suffix = f"{input_basename}_top{args.top}"
    else:
        suffix = input_basename
    
    aggregated_data = {}
    print(f"Processing {len(files_to_process)} files...")
    
    for i, (fullpath, filename) in enumerate(files_to_process):
        print(f"  Processing ({i+1}/{len(files_to_process)}): {filename}")
        
        file_data = parse_log_file(fullpath)
        
        if file_data:
            if args.separate:
                # Bench name logic
                if filename.endswith('.log.gz'):
                    bench_name = filename[:-7]
                elif filename.endswith('.log'):
                    bench_name = filename[:-4]
                else:
                    bench_name = filename
                
                output_folder = os.path.join(base_output_dir, input_basename)
                output_txt = os.path.join(output_folder, f"{bench_name}.txt")
                output_png = os.path.join(output_folder, f"{bench_name}.png")
                
                analyze_and_plot(file_data, output_txt, output_png, title_suffix=bench_name)
            else:
                # Aggregate
                for key, count in file_data.items():
                    aggregated_data[key] = aggregated_data.get(key, 0) + count

    # Generate Aggregated Report
    if not args.separate and aggregated_data:
        output_txt = os.path.join(base_output_dir, f"{suffix}.txt")
        output_png = os.path.join(base_output_dir, f"{suffix}.png")
        
        print(f"Generating aggregated hit map for {suffix}...")
        analyze_and_plot(aggregated_data, output_txt, output_png, title_suffix=suffix)
    elif not aggregated_data and not args.separate:
        print("No valid data aggregated.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)