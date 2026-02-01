# Analyzing STT-RAM Writes

A python script `analyze_stt_writes.py` is provided to parse the simulation results and aggregate write statistics.

### Safety Note
This script generates a **separate** Excel file (`sttram_analysis_results.xlsx`) containing the write analysis. This is to prevents corruption of the complex Data Connections in your main `BTBX_artifact_results.xlsx` file.

### When to run
Run this script **after** you have collected the results using `collectStats/getResults.sh`. The script relies on the generated `all_res` file in the `collectStats` directory.

### What it does
1.  **Reads** raw write count data from `collectStats/all_res`.
2.  **Calculates** statistics for each STT-RAM configuration (`no_sttramBTB`, `fdip_sttramBTB`), including:
    *   Total writes per way.
    *   Average writes per way.
    *   Maximum writes per way.
3.  **Computes** a combined average across configurations.
4.  **Generates** a summary table showing the most to least used ways and their fractional usage.
5.  **Writes** these tables to a new Excel file.

### How to run
You can run the script from the root directory. By default, it looks for `collectStats/all_res` and creates `sttram_analysis_results.xlsx`.

```bash
python3 analyze_stt_writes.py
```

### Arguments
The script accepts two optional arguments:
1.  **Input File**: Path to the simulation results file (default: `collectStats/all_res`).
2.  **Output Excel File**: Path for the output Excel file (default: `sttram_analysis_results.xlsx`).

**Example with custom paths:**
```bash
python3 analyze_stt_writes.py my_custom_results.txt my_sttram_stats.xlsx
```
