import csv
import sys

def analyze_stt_writes(input_file, output_file):
    try:
        with open(input_file, 'r') as f_in, open(output_file, 'w', newline='') as f_out:
            writer = csv.writer(f_out)
            writer.writerow(['Benchmark', 'BTB_Type', 'Set', 'Way', 'WriteCount'])

            for line in f_in:
                parts = line.split()
                # Expected format after sed in getResults.sh:
                # Benchmark Configuration STT_WRITE_COUNT Partition Set Way Count
                # Example: client_001 fdip_sttramBTB STT_WRITE_COUNT 0 10 0 55
                
                if len(parts) >= 7 and parts[2] == 'STT_WRITE_COUNT':
                    benchmark = parts[0]
                    btb_type = parts[1]
                    partition = parts[3]
                    set_idx = parts[4]
                    way = parts[5]
                    count = parts[6]

                    # Combine Partition and Set to ensure uniqueness if needed, 
                    # or just report Set if that's what is strictly requested.
                    # Given the ambiguity, I'll use Partition_Set.
                    full_set_id = f"{partition}_{set_idx}"

                    writer.writerow([benchmark, btb_type, full_set_id, way, count])
                    
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    input_filename = "collectStats/all_res"
    output_filename = "stt_write_report.csv"
    
    # Allow overriding filenames via command line args
    if len(sys.argv) > 1:
        input_filename = sys.argv[1]
    if len(sys.argv) > 2:
        output_filename = sys.argv[2]

    analyze_stt_writes(input_filename, output_filename)
    print(f"Analysis complete. Report saved to {output_filename}")
