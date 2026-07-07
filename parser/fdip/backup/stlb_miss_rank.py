import gzip
import re
import sys
import os
import argparse

def get_files_from_path(path):
    """Recursively yields (full_path, relative_path_from_input, filename)"""
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

def get_stlb_miss_count(file_path):
    """Scans a file quickly to just count STLB misses."""
    count = 0
    # Quick regex for Translation: PTW-*
    pattern = re.compile(r'Translation: (PTW-\S+)')
    
    try:
        if file_path.endswith('.gz'):
            opener = gzip.open
        else:
            opener = open
            
        with opener(file_path, 'rt', errors='replace') as f:
            for line in f:
                if "Translation: PTW-" in line:
                    count += 1
    except Exception as e:
        print(f"Error scanning {file_path}: {e}")
        return 0
    return count

def count_files(inputs):
    """Counts total number of log files to be processed."""
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

def main():
    parser = argparse.ArgumentParser(description='Scan ChampSim logs and rank by STLB misses.')
    parser.add_argument('inputs', nargs='+', help='List of files or directories to analyze')
    
    args = parser.parse_args()
    
    # UPDATED OUTPUT DIRECTORY
    base_output_dir = os.path.expanduser('~/melong/champsim_replay/script/hit_map')
    
    # Pre-count total files for progress bar
    print("Counting files...")
    total_files_count = count_files(args.inputs)
    print(f"Total files to scan: {total_files_count}")

    for input_path in args.inputs:
        input_basename = os.path.basename(os.path.normpath(input_path))
        print(f"Scanning input: {input_path}")
        
        files_metadata = [] # (stlb_miss_count, full_path, rel_dir, filename)
        
        print("Scanning files for ranking...")
        current_file_idx = 0
        for full_path, rel_dir, filename in get_files_from_path(input_path):
            current_file_idx += 1
            print(f"  Scanning ({current_file_idx}/{total_files_count}): {filename:<50}", end='\r') 
            miss_count = get_stlb_miss_count(full_path)
            files_metadata.append((miss_count, full_path, rel_dir, filename))
        print(f"\n  Scanning complete for {input_basename}.          ")

        if files_metadata:
            # Sort by miss count desc
            files_metadata.sort(key=lambda x: x[0], reverse=True)
            
            # Write Ranking File
            ranking_file = os.path.join(base_output_dir, f"{input_basename}_stlb_ranking.txt")
            os.makedirs(os.path.dirname(ranking_file), exist_ok=True)
            with open(ranking_file, 'w') as f:
                f.write(f"STLB Miss Ranking for {input_basename}\n")
                f.write(f"{'Count':<12} | Filename\n")
                f.write("-" * 50 + "\n")
                for count, fullpath, _, fname in files_metadata:
                    # Format: Count | Filename
                    f.write(f"{count:<12} | {fname}\n")
            print(f"Ranking generated: {ranking_file}")
        else:
            print(f"No valid data found in {input_path}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)