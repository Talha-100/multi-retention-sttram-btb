# Analyzing STT-RAM Writes

A python script `analyze_stt_writes.py` is provided to parse the simulation results and generate a CSV report of the write counts for the STT-RAM BTB.

### When to run
Run this script **after** you have collected the results using `collectStats/getResults.sh`. The script relies on the generated `all_res` file in the `collectStats` directory.

### How to run
You can run the script from the root directory. By default, it looks for `collectStats/all_res` and outputs to `stt_write_report.csv`.

```bash
python3 analyze_stt_writes.py
```

### Arguments
The script accepts two optional arguments:
1.  **Input File**: Path to the results file (default: `collectStats/all_res`).
2.  **Output File**: Path for the generated CSV report (default: `stt_write_report.csv`).

**Example with custom paths:**
```bash
python3 analyze_stt_writes.py my_custom_results_file.txt my_report.csv
```

### Output
The script generates a CSV file with the following columns:
*   `Benchmark`: The name of the benchmark trace (e.g., `client_001`).
*   `BTB_Type`: The configuration run (e.g., `fdip_sttramBTB`).
*   `Set`: The combined Partition and Set index (formatted as `Partition_Set`).
*   `Way`: The way index within the set.
*   `WriteCount`: The number of writes to that specific BTB entry.

This CSV file can be imported into Excel or Pandas for further analysis of write intensity and wear-leveling.
