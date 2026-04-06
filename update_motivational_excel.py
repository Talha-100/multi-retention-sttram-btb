import pandas as pd
import openpyxl
import os
import sys

def parse_all_res(filepath):
    data = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if 'MOT_STATS' in line:
                    parts = line.strip().split()
                    # Expected format: bench_name runName_btb MOT_STATS trace_string zone bucket count
                    # Example: server_001 no_convBTB MOT_STATS server_001.champsimtrace.xz 0 1 500
                    if len(parts) >= 7 and parts[2] == 'MOT_STATS':
                        config = parts[1]
                        
                        # Only collect for convBTB without prefetcher (baseline SRAM BTB profiling)
                        if config == 'no_convBTB':
                            bench = parts[0]
                            try:
                                zone = int(parts[4])
                                bucket = int(parts[5])
                                count = int(parts[6])
                                data.append([bench, zone, bucket, count])
                            except ValueError:
                                pass
    except FileNotFoundError:
        print(f"Error: {filepath} not found")
        return pd.DataFrame()
        
    if not data:
        return pd.DataFrame()
        
    df = pd.DataFrame(data, columns=['Benchmark', 'Zone', 'Bucket', 'Count'])
    df = df.groupby(['Benchmark', 'Zone', 'Bucket'], as_index=False)['Count'].sum()
    return df

def update_excel(excel_path, df):
    try:
        wb = openpyxl.load_workbook(excel_path)
    except FileNotFoundError:
        print(f"Error: {excel_path} not found")
        return
        
    if 'Sheet1' in wb.sheetnames:
        sheet = wb['Sheet1']
    else:
        sheet = wb.active
        
    # Find benchmark rows in column 14 (N)
    for row in range(1, 1000):
        val = sheet.cell(row=row, column=14).value
        if val and isinstance(val, str) and val not in ['Benchmarks', 'None', '']:
            bench_name = val.strip().lower().replace('_', '')
            
            # Find matching benchmark in df
            matched_bench = None
            for b in df['Benchmark'].unique():
                norm_b = b.lower().replace('_', '')
                if bench_name in norm_b or norm_b in bench_name:
                    matched_bench = b
                    break
                    
            if matched_bench:
                # Update cells
                for z in range(4):
                    for bkt in range(5):
                        # Filter dataframe
                        mask = (df['Benchmark'] == matched_bench) & (df['Zone'] == z) & (df['Bucket'] == bkt)
                        count_series = df.loc[mask, 'Count']
                        if not count_series.empty:
                            count = count_series.values[0]
                            sheet.cell(row=row+z, column=16+bkt).value = count
                        else:
                            sheet.cell(row=row+z, column=16+bkt).value = 0
                            
    wb.save(excel_path)
    print(f"Successfully updated {excel_path}")

if __name__ == "__main__":
    filepath = 'collectStats/all_res'
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        
    df = parse_all_res(filepath)
    if not df.empty:
        update_excel('Analysis_Motivation.xlsx', df)
    else:
        print("No MOT_STATS found.")
