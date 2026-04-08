import pandas as pd
import sys
import os

def parse_all_res(filepath):
    data = []
    # Lifetime Zones mapping (as per GEMINI.md)
    zone_labels = {
        0: "<= 1ms",
        1: "> 1ms & <= 10ms",
        2: "> 10ms & <= 100ms",
        3: "> 100ms"
    }
    # Hit Count Buckets mapping (as per GEMINI.md)
    bucket_labels = {
        0: "1 hit",
        1: "2 hits",
        2: "3 hits",
        3: "4 hits",
        4: "5+ hits"
    }
    
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found")
        return pd.DataFrame()
        
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if 'MOT_STATS' in line:
                    parts = line.strip().split()
                    # Expected format: bench_name runName_btb MOT_STATS trace_string zone bucket count
                    if len(parts) >= 7 and parts[2] == 'MOT_STATS':
                        config = parts[1]
                        # Focus on baseline convBTB with no prefetcher for standard motivation analysis
                        if config == 'no_convBTB':
                            bench = parts[0]
                            try:
                                zone_id = int(parts[4])
                                bucket_id = int(parts[5])
                                count = int(parts[6])
                                
                                zone_label = zone_labels.get(zone_id, f"Zone_{zone_id}")
                                bucket_label = bucket_labels.get(bucket_id, f"Bucket_{bucket_id}")
                                
                                data.append([bench, zone_label, bucket_label, count])
                            except ValueError:
                                pass
    except Exception as e:
        print(f"Error parsing file: {e}")
        return pd.DataFrame()
        
    if not data:
        return pd.DataFrame()
        
    df = pd.DataFrame(data, columns=['Benchmark', 'Lifetime', 'Hit_Bucket', 'Count'])
    # Aggregate counts across potential multiple entries for same combination
    df = df.groupby(['Benchmark', 'Lifetime', 'Hit_Bucket'], as_index=False)['Count'].sum()
    return df

def generate_csv(df, output_path):
    try:
        # Create a readable pivot table: Benchmarks/Lifetimes as rows, Hit Buckets as columns
        pivot_df = df.pivot_table(index=['Benchmark', 'Lifetime'], 
                                  columns='Hit_Bucket', 
                                  values='Count', 
                                  fill_value=0)
        
        # Ensure all columns exist in the correct order
        cols = ["1 hit", "2 hits", "3 hits", "4 hits", "5+ hits"]
        for col in cols:
            if col not in pivot_df.columns:
                pivot_df[col] = 0
        pivot_df = pivot_df[cols]
        
        # Order the lifetimes correctly for each benchmark
        lifetime_order = ["<= 1ms", "> 1ms & <= 10ms", "> 10ms & <= 100ms", "> 100ms"]
        
        # Build a complete index to ensure every benchmark has all 4 lifetime zones
        all_benchmarks = sorted(df['Benchmark'].unique())
        full_index = pd.MultiIndex.from_product([all_benchmarks, lifetime_order], 
                                                names=['Benchmark', 'Lifetime'])
        
        # Reindex and save
        pivot_df = pivot_df.reindex(full_index, fill_value=0)
        pivot_df.to_csv(output_path)
        print(f"Successfully generated {output_path}")
        
    except Exception as e:
        print(f"Error during CSV generation: {e}")

if __name__ == "__main__":
    filepath = 'collectStats/all_res'
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        
    df = parse_all_res(filepath)
    if not df.empty:
        generate_csv(df, 'Analysis_Motivation.csv')
    else:
        print("No motivational data found for 'no_convBTB' configuration in " + filepath)
