import pandas as pd
import sys
import os
import re

def parse_all_res(filepath):
    # Dictionaries to store data per (benchmark, config)
    stats = {}
    
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found")
        return pd.DataFrame()
        
    try:
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 3:
                    continue
                    
                bench = parts[0]
                config = parts[1]
                key = parts[2]
                
                # We only care about STT-RAM Volatility configs for the new output
                if '-ref-' not in config and '-wb-' not in config:
                    continue
                    
                pair = (bench, config)
                if pair not in stats:
                    stats[pair] = {}
                    
                if key == 'STT_VOLATILE_STATS':
                    stats[pair]['refreshes'] = int(parts[3])
                    stats[pair]['evictions'] = int(parts[4])
                    stats[pair]['adjusted_ipc'] = float(parts[5])
                elif key == 'BTB_reads:':
                    stats[pair]['reads'] = int(parts[3])
                elif key == 'BTB_writes:':
                    stats[pair]['writes'] = int(parts[3])
                elif key == 'cumulative-IPC':
                    stats[pair]['ipc'] = float(parts[3])
                elif key == 'instructions':
                    stats[pair]['instructions'] = int(parts[3])
                elif key == 'total_mispredicts':
                    stats[pair]['mispredicts'] = int(parts[3])
                    
    except Exception as e:
        print(f"Error parsing file: {e}")
        return pd.DataFrame()
        
    data = []
    
    # Energy constants
    e_read = 0.12 * 1e-9 # 0.12 nJ -> J
    p_leak = 1.2 * 1e-3 # 1.2 mW -> W
    
    # Write energy per RT
    e_write_dict = {
        '1ms': 0.45 * 1e-9,
        '10ms': 0.52 * 1e-9,
        '100ms': 0.61 * 1e-9,
        '1s': 0.75 * 1e-9
    }
    
    for (bench, config), s in stats.items():
        if 'refreshes' not in s:
            continue
            
        # Parse config name: e.g. fdip_conv-sttram-ref-1ms
        policy = 'Unknown'
        rt = 'Unknown'
        if '-ref-' in config:
            policy = 'Refresh'
            rt = config.split('-ref-')[1]
            prefetch = config.split('_conv-sttram-')[0]
        elif '-wb-' in config:
            policy = 'WriteBack'
            rt = config.split('-wb-')[1]
            prefetch = config.split('_conv-sttram-')[0]
            
        reads = s.get('reads', 0)
        writes = s.get('writes', 0)
        refreshes = s.get('refreshes', 0)
        evictions = s.get('evictions', 0)
        instructions = s.get('instructions', 1)
        mispredicts = s.get('mispredicts', 0)
        
        ipc = s.get('adjusted_ipc', s.get('ipc', 0))
        
        mpki = (mispredicts * 1000.0) / instructions
        
        # Pred_Accuracy: assuming reads == total branches
        pred_accuracy = 0.0
        if reads > 0:
            pred_accuracy = ((reads - mispredicts) / float(reads)) * 100.0
            
        # Energy calculation
        e_write = e_write_dict.get(rt, 0.45 * 1e-9)
        dynamic_energy = ((writes + refreshes) * e_write) + (reads * e_read)
        
        # cycles = instructions / ipc
        cycles = 0
        if ipc > 0:
            cycles = instructions / ipc
            
        static_energy = p_leak * (cycles / 4000000000.0)
        
        total_energy_mj = (dynamic_energy + static_energy) * 1000.0 # Convert to mJ
        
        ref_wb_count = refreshes if policy == 'Refresh' else evictions
        
        data.append([bench, prefetch, policy, rt, ipc, mpki, pred_accuracy, total_energy_mj, ref_wb_count])
        
    df = pd.DataFrame(data, columns=['Benchmarks', 'Prefetcher', 'Policy', 'RT', 'IPC', 'MPKI', 'Pred_Accuracy (%)', 'Energy (mJ)', 'REF/WB Counts'])
    
    # Average the metrics across the different prefetcher configurations (no and fdip)
    df = df.drop(columns=['Prefetcher'])
    df = df.groupby(['Benchmarks', 'Policy', 'RT'], as_index=False).mean()
    
    return df

def generate_csv(df, output_path):
    if df.empty:
        print("No STT-RAM Volatility data to write.")
        return
        
    try:
        # Retention time custom sorting
        rt_order = {"1ms": 1, "10ms": 2, "100ms": 3, "1s": 4}
        df['RT_Sort'] = df['RT'].map(rt_order)
        df = df.sort_values(by=['Benchmarks', 'Policy', 'RT_Sort']).drop(columns=['RT_Sort'])
        
        df.to_csv(output_path, index=False)
        print(f"Successfully generated {output_path}")
        
    except Exception as e:
        print(f"Error during CSV generation: {e}")

if __name__ == "__main__":
    filepath = 'collectStats/all_res'
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        
    df = parse_all_res(filepath)
    if not df.empty:
        generate_csv(df, 'STT_VOLATILE_RESULTS.csv')
    else:
        print("No STT_VOLATILE_STATS data found in " + filepath)
