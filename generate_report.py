import pandas as pd
import numpy as np
import sys
import os
from scipy.stats import gmean

def load_and_parse_data(filepath):
    print(f"Reading {filepath}...")
    data = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    bench = parts[0]
                    config = parts[1]
                    metric = parts[2]
                    
                    if metric == 'MULTI_RET_STATS':
                        # parts format: [bench, config, 'MULTI_RET_STATS', Benchmark, Z1_Hits, Z2_Hits, Z3_Hits, Prom, Adj_IPC]
                        if len(parts) >= 9:
                            data.append([bench, config, 'MULTI_RET_ZONE1_HITS', float(parts[4])])
                            data.append([bench, config, 'MULTI_RET_ZONE2_HITS', float(parts[5])])
                            data.append([bench, config, 'MULTI_RET_ZONE3_HITS', float(parts[6])])
                            data.append([bench, config, 'MULTI_RET_PROMOTIONS', float(parts[7])])
                            data.append([bench, config, 'MULTI_RET_ADJUSTED_IPC', float(parts[8])])
                        continue
                        
                    try:
                        value = float(parts[3])
                        data.append([bench, config, metric, value])
                    except ValueError:
                        continue 
    except FileNotFoundError:
        print(f"Error: File {filepath} not found.")
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=['Benchmark', 'Config', 'Metric', 'Value'])
    return df

def split_config(config_str):
    if '_' in config_str:
        return config_str.rsplit('_', 1)
    return config_str, "Unknown"

def autofit_columns(df, worksheet, is_pivot=False):
    if is_pivot:
        max_idx_width = max(
            [len(str(val)) for val in df.index] + 
            [len(str(df.index.name))]
        )
        worksheet.set_column(0, 0, max_idx_width + 2)
        for i, col in enumerate(df.columns):
            if isinstance(col, tuple):
                header_width = max([len(str(c)) for c in col])
            else:
                header_width = len(str(col))
            if len(df[col]) > 0:
                max_data_width = df[col].astype(str).map(len).max()
            else:
                max_data_width = 0
            final_width = max(header_width, max_data_width) + 2
            worksheet.set_column(i + 1, i + 1, final_width)
    else:
        for i, col in enumerate(df.columns):
            header_width = len(str(col))
            if len(df[col]) > 0:
                max_data_width = df[col].astype(str).map(len).max()
            else:
                max_data_width = 0
            final_width = max(header_width, max_data_width) + 2
            worksheet.set_column(i, i, final_width)

def generate_report(input_file, output_file):
    df = load_and_parse_data(input_file)
    if df.empty:
        print("No data found to process.")
        return

    df[['Prefetcher', 'BTB']] = df['Config'].apply(lambda x: pd.Series(split_config(x)))
    df_wide = df.pivot_table(index=['Benchmark', 'BTB', 'Prefetcher'], columns='Metric', values='Value', aggfunc='first').reset_index()

    # --- Derived Metrics ---
    
    # 1. MPKI
    if 'total_mispredicts' in df_wide.columns and 'instructions' in df_wide.columns:
        df_wide['MPKI'] = (df_wide['total_mispredicts'] / df_wide['instructions']) * 1000
    else:
        df_wide['MPKI'] = np.nan

    if 'cumulative-IPC' in df_wide.columns:
        df_wide.rename(columns={'cumulative-IPC': 'IPC'}, inplace=True)
        
    # 2. BTB Miss Rate
    miss_cols = [c for c in df_wide.columns if c.startswith('BTB_') and c.endswith('_Misses')]
    hit_cols = [c for c in df_wide.columns if c.startswith('BTB_') and c.endswith('_Hits')]
    
    # Ensure all columns exist, replace NaN with 0 for summing
    for c in miss_cols + hit_cols:
        df_wide[c] = df_wide[c].fillna(0)
        
    df_wide['Total_BTB_Misses'] = df_wide[miss_cols].sum(axis=1)
    df_wide['Total_BTB_Hits'] = df_wide[hit_cols].sum(axis=1)
    
    df_wide['BTB_Miss_Rate'] = 0.0
    total_accesses = df_wide['Total_BTB_Misses'] + df_wide['Total_BTB_Hits']
    # Avoid division by zero
    mask = total_accesses > 0
    df_wide.loc[mask, 'BTB_Miss_Rate'] = (df_wide.loc[mask, 'Total_BTB_Misses'] / total_accesses.loc[mask]) * 100

    # 3. BTB Hit MPKI (Mispredict on Hit)
    if 'mispredict_on_btb_hit' in df_wide.columns and 'instructions' in df_wide.columns:
         df_wide['BTB_Hit_MPKI'] = (df_wide['mispredict_on_btb_hit'] / df_wide['instructions']) * 1000
    else:
         df_wide['BTB_Hit_MPKI'] = np.nan

    # --- Sort Logic ---
    custom_btb_order = ['convBTB', 'pdede', 'BTBX', 'sttramBTB', 'fixed-retentions-btb', 'multi-retention-btb']

    def get_btb_sort_key(btb_name):
        if btb_name in custom_btb_order:
            return custom_btb_order.index(btb_name)
        return len(custom_btb_order)

    def sort_pivot_columns(df_pivot):
        unique_btbs = sorted(list(set(df_pivot.columns.get_level_values(0))), 
                             key=lambda x: (get_btb_sort_key(x), x))
        new_columns = []
        for btb in unique_btbs:
            cols = [c for c in df_pivot.columns if c[0] == btb]
            cols.sort()
            new_columns.extend(cols)
        return df_pivot[new_columns]

    # --- Pivot Helpers ---
    def create_pivot(metric_name, agg_func_row='mean'):
        pivot = df_wide.pivot_table(index='Benchmark', columns=['BTB', 'Prefetcher'], values=metric_name)
        unique_btbs = df_wide['BTB'].unique()
        for btb in unique_btbs:
            cols = [c for c in pivot.columns if c[0] == btb]
            if cols:
                 pivot[(btb, 'Average')] = pivot[cols].mean(axis=1)
        pivot = sort_pivot_columns(pivot)
        
        # Summary Row
        if agg_func_row == 'gmean':
            def safe_gmean(series):
                v = series.dropna()
                v = v[v > 0]
                return gmean(v) if len(v) > 0 else 0
            row = pivot.apply(safe_gmean)
            row.name = 'Geomean'
        else:
            row = pivot.mean()
            row.name = 'Arithmetic Mean'
            
        pivot = pd.concat([pivot, row.to_frame().T])
        return pivot

    # --- Create Pivots ---
    ipc_pivot = create_pivot('IPC', 'gmean')
    mpki_pivot = create_pivot('MPKI', 'mean')
    btb_miss_pivot = create_pivot('BTB_Miss_Rate', 'mean')
    btb_hit_mpki_pivot = create_pivot('BTB_Hit_MPKI', 'mean')
    
    if 'MULTI_RET_PROMOTIONS' in df_wide.columns:
        multi_ret_prom_pivot = create_pivot('MULTI_RET_PROMOTIONS', 'mean')
        multi_ret_z1_pivot = create_pivot('MULTI_RET_ZONE1_HITS', 'mean')
        multi_ret_z2_pivot = create_pivot('MULTI_RET_ZONE2_HITS', 'mean')
        multi_ret_z3_pivot = create_pivot('MULTI_RET_ZONE3_HITS', 'mean')
    else:
        multi_ret_prom_pivot = None
        multi_ret_z1_pivot = None
        multi_ret_z2_pivot = None
        multi_ret_z3_pivot = None

    # --- Summary Sheet ---
    unique_btbs = df_wide['BTB'].unique()
    summary_data = []
    for btb in unique_btbs:
        ipc_val = ipc_pivot.loc['Geomean', (btb, 'Average')] if (btb, 'Average') in ipc_pivot.columns else np.nan
        mpki_val = mpki_pivot.loc['Arithmetic Mean', (btb, 'Average')] if (btb, 'Average') in mpki_pivot.columns else np.nan
        miss_val = btb_miss_pivot.loc['Arithmetic Mean', (btb, 'Average')] if (btb, 'Average') in btb_miss_pivot.columns else np.nan
        hit_mpki_val = btb_hit_mpki_pivot.loc['Arithmetic Mean', (btb, 'Average')] if (btb, 'Average') in btb_hit_mpki_pivot.columns else np.nan
        
        summary_data.append({
            'BTB': btb, 
            'Avg IPC (Geomean)': ipc_val, 
            'Avg MPKI': mpki_val,
            'Avg BTB Miss Rate (%)': miss_val,
            'Avg BTB Hit MPKI': hit_mpki_val
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df['sort_key'] = summary_df['BTB'].apply(get_btb_sort_key)
    summary_df = summary_df.sort_values(['sort_key', 'BTB']).drop('sort_key', axis=1)

    # --- Writing to Excel ---
    print(f"Writing report to {output_file}...")
    try:
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            # Sheet 1: BTB Comparison
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            autofit_columns(summary_df, writer.sheets['Summary'], is_pivot=False)
            
            # Sheets 2-5: Analysis
            sheet_map = {
                'IPC Analysis': ipc_pivot,
                'MPKI Analysis': mpki_pivot,
                'BTB Miss Rate': btb_miss_pivot,
                'BTB Hit MPKI': btb_hit_mpki_pivot
            }
            if multi_ret_prom_pivot is not None:
                sheet_map['Multi-Ret Promotions'] = multi_ret_prom_pivot
                sheet_map['Multi-Ret Zone1 Hits'] = multi_ret_z1_pivot
                sheet_map['Multi-Ret Zone2 Hits'] = multi_ret_z2_pivot
                sheet_map['Multi-Ret Zone3 Hits'] = multi_ret_z3_pivot
            
            for name, pvt in sheet_map.items():
                pvt.to_excel(writer, sheet_name=name)
                autofit_columns(pvt, writer.sheets[name], is_pivot=True)
                
                # Formatting
                sheet = writer.sheets[name]
                nrow, ncol = pvt.shape
                
                # Logic: IPC is Higher=Better (Green Max)
                # Others are Lower=Better (Red Max, Green Min)
                if name == 'IPC Analysis':
                    colors = {'min_color': '#F8696B', 'mid_color': '#FFEB84', 'max_color': '#63BE7B'}
                else:
                    colors = {'min_color': '#63BE7B', 'mid_color': '#FFEB84', 'max_color': '#F8696B'}
                
                sheet.conditional_format(2, 1, nrow+2, ncol, {'type': '3_color_scale', **colors})
            
            # Sheet 6: Raw Data
            df_wide.to_excel(writer, sheet_name='Raw Data', index=False)
            autofit_columns(df_wide, writer.sheets['Raw Data'], is_pivot=False)

        print("Report generated successfully.")

    except Exception as e:
        print(f"Error creating Excel file: {e}")

if __name__ == "__main__":
    input_file = "collectStats/all_res"
    output_file = "Analysis_Report.xlsx"
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
        
    generate_report(input_file, output_file)
