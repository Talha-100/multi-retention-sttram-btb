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
                    # Format: Benchmark Config STT_WRITE_COUNT Partition Set Way Count
                    # Example: client_001 fdip_sttramBTB STT_WRITE_COUNT 0 10 0 55
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
    
    # Mapping for Partition ID to Offset Bits Description
    partition_map = {
        0: "Return",
        1: "<= 4 bits",
        2: "<= 5 bits",
        3: "<= 7 bits",
        4: "<= 9 bits",
        5: "<= 11 bits",
        6: "<= 19 bits",
        7: "<= 25 bits",
        8: "> 25 bits"
    }

    # Helper function to generate stats table
    def generate_table(df_subset):
        if df_subset.empty:
            return pd.DataFrame()
        
        # Group by Partition (the "ways for different offset bits")
        stats = df_subset.groupby('Partition')['Count'].sum().reset_index()
        stats.columns = ['Partition ID', 'Total Writes']
        
        # Add Description
        stats['Offset Bits'] = stats['Partition ID'].map(partition_map)
        
        # Calculate Percentage
        total_sum = stats['Total Writes'].sum()
        if total_sum > 0:
            stats['% of Total'] = (stats['Total Writes'] / total_sum) * 100
        else:
            stats['% of Total'] = 0.0
            
        # Reorder columns
        stats = stats[['Partition ID', 'Offset Bits', 'Total Writes', '% of Total']]
        return stats

    # Identify configs
    # We expect config names containing "no" and "fdip"
    unique_configs = df['Config'].unique()
    
    no_sttram_configs = [c for c in unique_configs if 'no' in c and 'sttramBTB' in c]
    fdip_sttram_configs = [c for c in unique_configs if 'fdip' in c and 'sttramBTB' in c]
    
    no_fixed_configs = [c for c in unique_configs if 'no' in c and 'fixed-retentions-btb' in c]
    fdip_fixed_configs = [c for c in unique_configs if 'fdip' in c and 'fixed-retentions-btb' in c]
    
    tables = {}
    
    # 1. Table for 'no' prefetcher (no_sttramBTB)
    if no_sttram_configs:
        df_subset = df[df['Config'].isin(no_sttram_configs)]
        tables['no_sttramBTB Stats'] = generate_table(df_subset)
    
    # 2. Table for 'fdip' prefetcher (fdip_sttramBTB)
    if fdip_sttram_configs:
        df_subset = df[df['Config'].isin(fdip_sttram_configs)]
        tables['fdip_sttramBTB Stats'] = generate_table(df_subset)
        
    # 3. Table for 'no' prefetcher (no_fixed-retentions-btb)
    if no_fixed_configs:
        df_subset = df[df['Config'].isin(no_fixed_configs)]
        tables['no_fixed-retentions-btb Stats'] = generate_table(df_subset)
        
    # 4. Table for 'fdip' prefetcher (fdip_fixed-retentions-btb)
    if fdip_fixed_configs:
        df_subset = df[df['Config'].isin(fdip_fixed_configs)]
        tables['fdip_fixed-retentions-btb Stats'] = generate_table(df_subset)

    # Combined Average for sttramBTB
    if 'no_sttramBTB Stats' in tables and 'fdip_sttramBTB Stats' in tables:
        t1 = tables['no_sttramBTB Stats'].set_index('Partition ID')
        t2 = tables['fdip_sttramBTB Stats'].set_index('Partition ID')
        
        # Average the Total Writes
        avg_df = t1[['Total Writes']].add(t2[['Total Writes']], fill_value=0) / 2
        avg_df = avg_df.reset_index()
        avg_df.columns = ['Partition ID', 'Average Total Writes']
        
        # Add Description
        avg_df['Offset Bits'] = avg_df['Partition ID'].map(partition_map)
        
        # Recalculate % based on Average Total
        total_avg_sum = avg_df['Average Total Writes'].sum()
        if total_avg_sum > 0:
            avg_df['% of Total'] = (avg_df['Average Total Writes'] / total_avg_sum) * 100
        else:
            avg_df['% of Total'] = 0.0
            
        avg_df = avg_df[['Partition ID', 'Offset Bits', 'Average Total Writes', '% of Total']]
        tables['sttramBTB Combined Average Stats'] = avg_df

    # Combined Average for fixed-retentions-btb
    if 'no_fixed-retentions-btb Stats' in tables and 'fdip_fixed-retentions-btb Stats' in tables:
        t1 = tables['no_fixed-retentions-btb Stats'].set_index('Partition ID')
        t2 = tables['fdip_fixed-retentions-btb Stats'].set_index('Partition ID')
        
        # Average the Total Writes
        avg_df = t1[['Total Writes']].add(t2[['Total Writes']], fill_value=0) / 2
        avg_df = avg_df.reset_index()
        avg_df.columns = ['Partition ID', 'Average Total Writes']
        
        # Add Description
        avg_df['Offset Bits'] = avg_df['Partition ID'].map(partition_map)
        
        # Recalculate % based on Average Total
        total_avg_sum = avg_df['Average Total Writes'].sum()
        if total_avg_sum > 0:
            avg_df['% of Total'] = (avg_df['Average Total Writes'] / total_avg_sum) * 100
        else:
            avg_df['% of Total'] = 0.0
            
        avg_df = avg_df[['Partition ID', 'Offset Bits', 'Average Total Writes', '% of Total']]
        tables['fixed-retentions-btb Combined Average Stats'] = avg_df

    # Write to Excel
    print(f"Writing to {excel_file}...")
    try:
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
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
    output_filename = "sttram_analysis_results.xlsx" 
    
    if len(sys.argv) > 1:
        input_filename = sys.argv[1]
    if len(sys.argv) > 2:
        output_filename = sys.argv[2]

    analyze_stt_writes(input_filename, output_filename)