# import gzip
# import re
# import sys
# import os
# import argparse
# import matplotlib.pyplot as plt
# import matplotlib.ticker as ticker  # [수정 1] ticker 모듈 추가
# import numpy as np

# def parse_log_file(file_path):
#     """Parses a single .log.gz/.log file and extracts latency data."""
#     data = {}
#     pattern = re.compile(r'\[Fetch Latency\] instr_id: \d+ latency: (\d+) cycle \(Translation: (\S+) Instruction: (\S+)\)')
    
#     try:
#         if file_path.endswith('.gz'):
#             opener = gzip.open
#         else:
#             opener = open
            
#         with opener(file_path, 'rt', errors='replace') as f:
#             for line in f:
#                 match = pattern.search(line)
#                 if match:
#                     latency = int(match.group(1))
#                     trans_src = match.group(2)
#                     data_src = match.group(3)
                    
#                     key = (trans_src, data_src)
#                     if key not in data:
#                         data[key] = []
#                     data[key].append(latency)
#     except Exception as e:
#         print(f"Error reading {file_path}: {e}")
#         return None
        
#     return data

# def analyze_and_plot(data, output_txt, output_png, title_suffix=""):
#     """Calculates statistics and generates a box plot."""
#     if not data:
#         return

#     # Calculate statistics
#     stats_lines = []
#     stats_lines.append(f"Analysis for: {title_suffix}")
#     stats_lines.append("Group (Translation, Instruction) | Count | Average Latency | Std Dev | Min | Max")
#     stats_lines.append("-" * 80)
    
#     # Custom Sort Order
#     trans_order = {
#         'ITLB': 0, 
#         'STLB': 1, 
#         'PTW-L1D': 2, 
#         'PTW-L2C': 3, 
#         'PTW-LLC': 4, 
#         'PTW-MEM': 5, 
#         'UNK': 99
#     }
#     data_src_order = {
#         'L1I': 0, 'L1D': 1, 'L2C': 2, 'LLC': 3, 'MEM': 4, 'UNK': 99
#     }

#     def sort_key(k):
#         return (trans_order.get(k[0], 100), data_src_order.get(k[1], 100))

#     sorted_keys = sorted(data.keys(), key=sort_key)
    
#     plot_labels = []
#     plot_data = []

#     for key in sorted_keys:
#         latencies = data[key]
#         count = len(latencies)
#         avg = np.mean(latencies)
#         std = np.std(latencies)
#         min_lat = np.min(latencies)
#         max_lat = np.max(latencies)
        
#         group_name = f"{key[0]}-{key[1]}"
#         stats_lines.append(f"{group_name:<30} | {count:<5} | {avg:<15.2f} | {std:<7.2f} | {min_lat:<3} | {max_lat:<3}")
        
#         # Updated Label with Count
#         label_with_count = f"{group_name}\n({count})"
#         plot_labels.append(label_with_count)
#         plot_data.append(latencies)

#     # Ensure valid output directory exists
#     os.makedirs(os.path.dirname(output_txt), exist_ok=True)
#     os.makedirs(os.path.dirname(output_png), exist_ok=True)

#     # Write statistics to TXT
#     with open(output_txt, 'w') as f:
#         f.write("\n".join(stats_lines))
#     print(f"Stats: {output_txt}")

#     # Generate Box Plot
#     plt.figure(figsize=(14, 8))
    
#     # Customize outliers (fliers): small dot, size 2
#     flierprops = dict(marker='.', markerfacecolor='black', markersize=2, linestyle='none', markeredgecolor='none')
    
#     plt.boxplot(plot_data, vert=True, patch_artist=True, flierprops=flierprops)
#     plt.xticks(range(1, len(plot_labels) + 1), plot_labels, rotation=45, ha='right')
    
#     plt.title(f'Fetch Latency Distribution')
#     plt.ylabel('Latency (Cycles)')
#     plt.xlabel('Translation - Data Source (Count)')
    
#     # User Request: 0-500 linear, >500 log
#     plt.yscale('symlog', linthresh=500)
    
#     # --- [수정 2] 100단위 눈금 설정 시작 ---
#     ax = plt.gca()
    
#     # 보조 눈금(Minor ticks)을 100단위로 설정
#     # symlog 특성상 500 이하에서는 100, 200, 300.. 등간격으로 찍히고
#     # 500 이상에서는 로그 스케일에 맞춰 촘촘하게 찍힙니다.
#     ax.yaxis.set_minor_locator(ticker.MultipleLocator(100))
    
#     # 주 눈금(Major)과 보조 눈금(Minor) 모두 그리드(점선) 표시
#     # which='both'를 해야 100단위 선이 보입니다.
#     plt.grid(True, which='both', axis='y', linestyle='--', alpha=0.5)
#     # --- [수정 2] 100단위 눈금 설정 끝 ---
    
#     plt.tight_layout()
    
#     plt.savefig(output_png)
#     plt.close()
#     print(f"Plot: {output_png}")

# # ... (나머지 코드는 동일) ...
# def get_files_from_path(path):
#     if os.path.isfile(path):
#         if path.endswith('.log') or path.endswith('.log.gz'):
#              yield path, "", os.path.basename(path)
#     elif os.path.isdir(path):
#         input_dir = os.path.normpath(path)
#         for root, dirs, files in os.walk(input_dir):
#             for file in files:
#                 if file.endswith('.log') or file.endswith('.log.gz'):
#                     full_path = os.path.join(root, file)
#                     rel_dir = os.path.relpath(root, input_dir)
#                     if rel_dir == ".": rel_dir = ""
#                     yield full_path, rel_dir, file

# def count_files(inputs):
#     total = 0
#     for input_path in inputs:
#         if os.path.isfile(input_path):
#             if input_path.endswith('.log') or input_path.endswith('.log.gz'):
#                 total += 1
#         elif os.path.isdir(input_path):
#             for root, _, files in os.walk(input_path):
#                 for file in files:
#                     if file.endswith('.log') or file.endswith('.log.gz'):
#                         total += 1
#     return total

# def find_file(filename, search_path):
#     if os.path.isfile(search_path):
#         if os.path.basename(search_path) == filename:
#             return search_path
#     elif os.path.isdir(search_path):
#         for root, _, files in os.walk(search_path):
#             if filename in files:
#                 return os.path.join(root, filename)
#     return None

# def read_ranking_file(ranking_file_path):
#     ranked_files = []
#     try:
#         with open(ranking_file_path, 'r') as f:
#             for line in f:
#                 if "Count" in line and "Filename" in line: continue 
#                 if line.strip().startswith("-"): continue 
                
#                 parts = [p.strip() for p in line.split('|')]
                
#                 if len(parts) >= 2:
#                     entry = {
#                         'count': int(parts[0]),
#                         'filename': parts[1],
#                         'fullpath': parts[2] if len(parts) > 2 else None
#                     }
#                     ranked_files.append(entry)
#     except Exception as e:
#         print(f"Error reading ranking file: {e}")
#         return []
#     return ranked_files

# def main():
#     parser = argparse.ArgumentParser(description='Analyze Fetch Latency from ChampSim logs recursive.')
#     parser.add_argument('inputs', nargs='+', help='List of files, directories, or a ranking file + search dir')
#     parser.add_argument('--separate', action='store_true', help='Generate separate reports for each file')
#     parser.add_argument('--top', type=int, default=0, help='Process only the top N files from the ranking')
    
#     args = parser.parse_args()
    
#     base_png_dir = 'fetch_latency_png'
#     base_txt_dir = 'fetch_latency_txt'
    
#     first_input = args.inputs[0]
#     files_to_process = [] 
    
#     is_ranking = False
#     input_basename = "aggregated_results" 

#     if os.path.isfile(first_input) and first_input.endswith('.txt'):
#         print(f"Reading ranking file: {first_input}")
#         is_ranking = True
#         input_basename = os.path.basename(first_input).replace('.txt', '')
        
#         ranking = read_ranking_file(first_input)
        
#         if args.top > 0:
#             ranking = ranking[:args.top]
#             print(f"Selecting top {args.top} files.")
            
#         search_dir = args.inputs[1] if len(args.inputs) > 1 else "."
        
#         print(f"Resolving file paths using search dir: {search_dir}...")
        
#         for entry in ranking:
#             fname = entry['filename']
#             fpath = entry['fullpath']
            
#             if not fpath or not os.path.exists(fpath):
#                 found_path = find_file(fname, search_dir)
#                 if found_path:
#                     fpath = found_path
#                 else:
#                     print(f"Warning: Could not locate {fname} in {search_dir}")
#                     continue
            
#             rel_dir = "" 
#             files_to_process.append((fpath, rel_dir, fname))

#     else:
#         input_basename = os.path.basename(os.path.normpath(first_input))
#         print("Counting files...")
        
#         for input_path in args.inputs:
#             for full_path, rel_dir, filename in get_files_from_path(input_path):
#                  files_to_process.append((full_path, rel_dir, filename))
        
#         if args.top > 0:
#              print(f"limit to top {args.top} files found (arbitrary order due to OS walk).")
#              files_to_process = files_to_process[:args.top]

#     total_files_count = len(files_to_process)
#     print(f"Total files to process: {total_files_count}")

#     aggregated_data = {}
#     files_found = False
#     current_file_idx = 0
    
#     for full_path, rel_dir, filename in files_to_process:
#         current_file_idx += 1
#         print(f"  Processing ({current_file_idx}/{total_files_count}): {filename:<50}", end='\r')
        
#         file_data = parse_log_file(full_path)
        
#         if file_data:
#             files_found = True
            
#             if args.separate:
#                 if filename.endswith('.log.gz'):
#                     bench_name = filename[:-7]
#                 elif filename.endswith('.log'):
#                     bench_name = filename[:-4]
#                 else:
#                     bench_name = filename
                
#                 final_rel_dir = rel_dir
                
#                 output_txt = os.path.join(base_txt_dir, final_rel_dir, f"{bench_name}.txt")
#                 output_png = os.path.join(base_png_dir, final_rel_dir, f"{bench_name}.png")
                
#                 analyze_and_plot(file_data, output_txt, output_png, title_suffix=bench_name)
#             else:
#                 for key, latencies in file_data.items():
#                     if key not in aggregated_data:
#                         aggregated_data[key] = []
#                     aggregated_data[key].extend(latencies)
    
#     print(f"\n  Processing complete.                       ")
    
#     if not args.separate and files_found and aggregated_data:
#         output_txt = os.path.join(base_txt_dir, f"{input_basename}.txt")
#         output_png = os.path.join(base_png_dir, f"{input_basename}.png")
        
#         print(f"Generating aggregated report for {input_basename}...")
#         analyze_and_plot(aggregated_data, output_txt, output_png, title_suffix=input_basename)
#     elif not files_found:
#         print(f"No valid data processed.")

# if __name__ == "__main__":
#     try:
#         main()
#     except KeyboardInterrupt:
#         print("\nInterrupted by user.")
#         sys.exit(0)

#########################################################################################################################################아래는 8개 버전
import gzip
import re
import sys
import os
import argparse
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker  # [수정 1] ticker 모듈 추가
import numpy as np

def parse_log_file(file_path):
    """Parses a single .log.gz/.log file and extracts latency data."""
    data = {}
    pattern = re.compile(r'\[Fetch Latency\] instr_id: \d+ latency: (\d+) cycle \(Translation: (\S+) Instruction: (\S+)\)')
    
    try:
        if file_path.endswith('.gz'):
            opener = gzip.open
        else:
            opener = open
            
        with opener(file_path, 'rt', errors='replace') as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    latency = int(match.group(1))
                    trans_src = match.group(2)
                    data_src = match.group(3)
                    
                    key = (trans_src, data_src)
                    if key not in data:
                        data[key] = []
                    data[key].append(latency)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None
        
    return data

def analyze_and_plot(data, output_txt, output_png, title_suffix=""):
    """Calculates statistics and generates a box plot."""
    if not data:
        return

    # --- Data Grouping (8 Groups) ---
    # Groups:
    # 1. TLB Hit - L1
    # 2. TLB Hit - L2
    # 3. TLB Hit - LLC
    # 4. TLB Hit - MEM
    # 5. TLB Miss - L1
    # 6. TLB Miss - L2
    # 7. TLB Miss - LLC
    # 8. TLB Miss - MEM

    grouped_data = {
        'TLB Hit - L1': [],
        'TLB Hit - L2': [],
        'TLB Hit - LLC': [],
        'TLB Hit - MEM': [],
        'TLB Miss - L1': [],
        'TLB Miss - L2': [],
        'TLB Miss - LLC': [],
        'TLB Miss - MEM': []
    }
    
    # Process Mapping
    for (trans_src, data_src), latencies in data.items():
        # 1. Determine TLB Status
        if 'ITLB' in trans_src or 'STLB' in trans_src:
            # Note: "STLB miss" usually implies PTW, but if the string is just "STLB" it's a hit.
            # Log format: "Translation: STLB" -> Hit. "Translation: PTW-..." -> Miss.
            if 'PTW' in trans_src:
                 tlb_status = 'TLB Miss'
            else:
                 tlb_status = 'TLB Hit'
        elif 'PTW' in trans_src:
            tlb_status = 'TLB Miss'
        else:
            continue # Skip unknown translation sources

        # 2. Determine Data Source
        # Map L1I/L1D -> L1. Map DRAM -> MEM.
        ds = data_src.upper()
        if 'L1' in ds:
            level = 'L1'
        elif 'L2' in ds:
            level = 'L2'
        elif 'LLC' in ds:
            level = 'LLC'
        elif 'MEM' in ds or 'DRAM' in ds:
            level = 'MEM'
        else:
            continue # Skip unknown data sources

        group_key = f"{tlb_status} - {level}"
        if group_key in grouped_data:
            grouped_data[group_key].extend(latencies)

    # --- Statistics Generation ---
    stats_lines = []
    stats_lines.append(f"Analysis for: {title_suffix}")
    stats_lines.append("Group (TLB Status - Data Source) | Count | Average Latency | Std Dev | Min | Max")
    stats_lines.append("-" * 90)
    
    # Fixed Order for Plotting and Reporting
    plot_order = [
         'TLB Hit - L1', 'TLB Hit - L2', 'TLB Hit - LLC', 'TLB Hit - MEM',
         'TLB Miss - L1', 'TLB Miss - L2', 'TLB Miss - LLC', 'TLB Miss - MEM'
    ]
    
    plot_labels = []
    plot_data = []

    for group_name in plot_order:
        latencies = grouped_data[group_name]
        
        if not latencies:
            # Handle empty groups gracefully or skip? 
            # User wants 8 fixed categories, likely wants to see 0 if empty.
            count = 0
            avg = 0.0
            std = 0.0
            min_lat = 0
            max_lat = 0
            # For plotting empty data, we append empty list
            plot_data.append([])
        else:
            count = len(latencies)
            avg = np.mean(latencies)
            std = np.std(latencies)
            min_lat = np.min(latencies)
            max_lat = np.max(latencies)
            plot_data.append(latencies)

        stats_lines.append(f"{group_name:<30} | {count:<5} | {avg:<15.2f} | {std:<7.2f} | {min_lat:<3} | {max_lat:<3}")
        
        # Label with Count
        label_with_count = f"{group_name}\n({count})"
        plot_labels.append(label_with_count)

    # Ensure valid output directory exists
    os.makedirs(os.path.dirname(output_txt), exist_ok=True)
    os.makedirs(os.path.dirname(output_png), exist_ok=True)

    # Write statistics to TXT
    with open(output_txt, 'w') as f:
        f.write("\n".join(stats_lines))
    print(f"Stats: {output_txt}")

    # Generate Box Plot
    plt.figure(figsize=(14, 8))
    
    # Customize outliers (fliers): small dot, size 2
    flierprops = dict(marker='.', markerfacecolor='black', markersize=2, linestyle='none', markeredgecolor='none')
    
    plt.boxplot(plot_data, vert=True, patch_artist=True, flierprops=flierprops)
    plt.xticks(range(1, len(plot_labels) + 1), plot_labels, rotation=45, ha='right')
    
    plt.title(f'Fetch Latency Distribution')
    plt.ylabel('Latency (Cycles)')
    plt.xlabel('Translation - Data Source (Count)')
    
    # User Request: 0-500 linear, >500 log
    plt.yscale('symlog', linthresh=500)
    
    # --- [수정 2] 100단위 눈금 설정 시작 ---
    ax = plt.gca()
    
    # 보조 눈금(Minor ticks)을 100단위로 설정
    # symlog 특성상 500 이하에서는 100, 200, 300.. 등간격으로 찍히고
    # 500 이상에서는 로그 스케일에 맞춰 촘촘하게 찍힙니다.
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(100))
    
    # 주 눈금(Major)과 보조 눈금(Minor) 모두 그리드(점선) 표시
    # which='both'를 해야 100단위 선이 보입니다.
    plt.grid(True, which='both', axis='y', linestyle='--', alpha=0.5)
    # --- [수정 2] 100단위 눈금 설정 끝 ---
    
    plt.tight_layout()
    
    plt.savefig(output_png)
    plt.close()
    print(f"Plot: {output_png}")

# ... (나머지 코드는 동일) ...
def get_files_from_path(path):
    if os.path.isfile(path):
        if path.endswith('.log') or path.endswith('.log.gz'):
             yield path, "", os.path.basename(path)
    elif os.path.isdir(path):
        input_dir = os.path.normpath(path)
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.endswith('.log') or file.endswith('.log.gz'):
                    full_path = os.path.join(root, file)
                    rel_dir = os.path.relpath(root, input_dir)
                    if rel_dir == ".": rel_dir = ""
                    yield full_path, rel_dir, file

def count_files(inputs):
    total = 0
    for input_path in inputs:
        if os.path.isfile(input_path):
            if input_path.endswith('.log') or input_path.endswith('.log.gz'):
                total += 1
        elif os.path.isdir(input_path):
            for root, _, files in os.walk(input_path):
                for file in files:
                    if file.endswith('.log') or file.endswith('.log.gz'):
                        total += 1
    return total

def find_file(filename, search_path):
    if os.path.isfile(search_path):
        if os.path.basename(search_path) == filename:
            return search_path
    elif os.path.isdir(search_path):
        for root, _, files in os.walk(search_path):
            if filename in files:
                return os.path.join(root, filename)
    return None

def read_ranking_file(ranking_file_path):
    ranked_files = []
    try:
        with open(ranking_file_path, 'r') as f:
            for line in f:
                if "Count" in line and "Filename" in line: continue 
                if line.strip().startswith("-"): continue 
                
                parts = [p.strip() for p in line.split('|')]
                
                if len(parts) >= 2:
                    entry = {
                        'count': int(parts[0]),
                        'filename': parts[1],
                        'fullpath': parts[2] if len(parts) > 2 else None
                    }
                    ranked_files.append(entry)
    except Exception as e:
        print(f"Error reading ranking file: {e}")
        return []
    return ranked_files

def main():
    parser = argparse.ArgumentParser(description='Analyze Fetch Latency from ChampSim logs recursive.')
    parser.add_argument('inputs', nargs='+', help='List of files, directories, or a ranking file + search dir')
    parser.add_argument('--separate', action='store_true', help='Generate separate reports for each file')
    parser.add_argument('--top', type=int, default=0, help='Process only the top N files from the ranking')
    
    args = parser.parse_args()
    
    base_png_dir = 'fetch_latency_png'
    base_txt_dir = 'fetch_latency_txt'
    
    first_input = args.inputs[0]
    files_to_process = [] 
    
    is_ranking = False
    input_basename = "aggregated_results" 

    if os.path.isfile(first_input) and first_input.endswith('.txt'):
        print(f"Reading ranking file: {first_input}")
        is_ranking = True
        input_basename = os.path.basename(first_input).replace('.txt', '')
        
        ranking = read_ranking_file(first_input)
        
        if args.top > 0:
            ranking = ranking[:args.top]
            print(f"Selecting top {args.top} files.")
            
        search_dir = args.inputs[1] if len(args.inputs) > 1 else "."
        
        print(f"Resolving file paths using search dir: {search_dir}...")
        
        for entry in ranking:
            fname = entry['filename']
            fpath = entry['fullpath']
            
            if not fpath or not os.path.exists(fpath):
                found_path = find_file(fname, search_dir)
                if found_path:
                    fpath = found_path
                else:
                    print(f"Warning: Could not locate {fname} in {search_dir}")
                    continue
            
            rel_dir = "" 
            files_to_process.append((fpath, rel_dir, fname))

    else:
        input_basename = os.path.basename(os.path.normpath(first_input))
        print("Counting files...")
        
        for input_path in args.inputs:
            for full_path, rel_dir, filename in get_files_from_path(input_path):
                 files_to_process.append((full_path, rel_dir, filename))
        
        if args.top > 0:
             print(f"limit to top {args.top} files found (arbitrary order due to OS walk).")
             files_to_process = files_to_process[:args.top]

    total_files_count = len(files_to_process)
    print(f"Total files to process: {total_files_count}")

    aggregated_data = {}
    files_found = False
    current_file_idx = 0
    
    for full_path, rel_dir, filename in files_to_process:
        current_file_idx += 1
        print(f"  Processing ({current_file_idx}/{total_files_count}): {filename:<50}", end='\r')
        
        file_data = parse_log_file(full_path)
        
        if file_data:
            files_found = True
            
            if args.separate:
                if filename.endswith('.log.gz'):
                    bench_name = filename[:-7]
                elif filename.endswith('.log'):
                    bench_name = filename[:-4]
                else:
                    bench_name = filename
                
                final_rel_dir = rel_dir
                
                output_txt = os.path.join(base_txt_dir, final_rel_dir, f"{bench_name}.txt")
                output_png = os.path.join(base_png_dir, final_rel_dir, f"{bench_name}.png")
                
                analyze_and_plot(file_data, output_txt, output_png, title_suffix=bench_name)
            else:
                for key, latencies in file_data.items():
                    if key not in aggregated_data:
                        aggregated_data[key] = []
                    aggregated_data[key].extend(latencies)
    
    print(f"\n  Processing complete.                       ")
    
    if not args.separate and files_found and aggregated_data:
        output_txt = os.path.join(base_txt_dir, f"{input_basename}.txt")
        output_png = os.path.join(base_png_dir, f"{input_basename}.png")
        
        print(f"Generating aggregated report for {input_basename}...")
        analyze_and_plot(aggregated_data, output_txt, output_png, title_suffix=input_basename)
    elif not files_found:
        print(f"No valid data processed.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)