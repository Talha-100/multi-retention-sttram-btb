import pandas as pd
import sys
import os
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

def analyze_stt_writes(input_file, excel_file):
    print(f"Analyzing STT-RAM writes from {input_file}...")
    
    data = []
    try:
        with open(input_file, 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 7 and parts[2] == 'STT_WRITE_COUNT':
                    # client_001 fdip_sttramBTB STT_WRITE_COUNT 0 10 0 55
                    benchmark = parts[0]
                    config = parts[1]
                    partition = int(parts[3])
                    set_idx = int(parts[4])
                    way = int(parts[5])
                    count = int(parts[6])
                    
                    data.append({
                        'Benchmark': benchmark,
                        'Config': config,
                        'Partition': partition,
                        'Set': set_idx,
                        'Way': way,
                        'Count': count
                    })
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return

    if not data:
        print("No STT_WRITE_COUNT data found.")
        return

    df = pd.DataFrame(data)
    
    # Identify configs
    configs = df['Config'].unique()
    
    # Prepare tables
    tables = {}
    
    # 1. Totals and Averages per Config
    for cfg in configs:
        cfg_df = df[df['Config'] == cfg]
        way_stats = cfg_df.groupby('Way')['Count'].agg(['sum', 'mean', 'max']).reset_index()
        way_stats.columns = ['Way', 'Total Writes', 'Average Writes', 'Max Writes']
        tables[f"{cfg} Stats"] = way_stats

    # 2. Combined Averages
    combined_stats = df.groupby('Way')['Count'].mean().reset_index()
    combined_stats.columns = ['Way', 'Combined Average Writes']
    tables["Combined Averages"] = combined_stats
    
    # 3. Summary (Most/Least used ways) - Fraction
    total_writes_all = df['Count'].sum()
    way_totals = df.groupby('Way')['Count'].sum().reset_index()
    way_totals['Fraction'] = way_totals['Count'] / total_writes_all
    way_totals = way_totals.sort_values(by='Count', ascending=False)
    tables["Way Usage Summary"] = way_totals

    # Write to Excel
    print(f"Writing to {excel_file}...")
    try:
        # Create a new workbook or overwrite to ensure we don't corrupt existing complex files
        # We prefer writing to a separate file for safety.
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
             # Just create a dummy frame to init the sheet, then use low-level access for formatting
             # Actually simpler: just write the tables.
             
             start_row = 0
             for title, table_df in tables.items():
                 # Write title
                 pd.DataFrame([title]).to_excel(writer, sheet_name='sttramBTB writes', startrow=start_row, index=False, header=False)
                 start_row += 1
                 # Write table
                 table_df.to_excel(writer, sheet_name='sttramBTB writes', startrow=start_row, index=False)
                 start_row += len(table_df) + 3

        print(f"Successfully created {excel_file} with analysis.")
        
    except Exception as e:
        print(f"Error writing Excel: {e}")

if __name__ == "__main__":
    input_filename = "collectStats/all_res"
    output_filename = "sttram_analysis_results.xlsx" # SAFE DEFAULT
    
    if len(sys.argv) > 1:
        input_filename = sys.argv[1]
    if len(sys.argv) > 2:
        output_filename = sys.argv[2]

    analyze_stt_writes(input_filename, output_filename)
