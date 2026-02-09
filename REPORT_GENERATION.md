# Generating the Analysis Report

The `generate_report.py` script creates a comprehensive Excel report (`Analysis_Report.xlsx`) from your simulation results. This approach replaces the manual updating of `BTBX_artifact_results.xlsx`.

### Features
*   **Raw Data**: Imports and cleans the `collectStats/all_res` file.
*   **IPC Analysis**: Pivots data to compare IPC across different BTB configurations (`no`, `fdip`, and their average). Includes a Geomean summary.
*   **MPKI Analysis**: Calculates MPKI (Mispredictions Per Kilo-Instruction) and compares configurations. Includes an Arithmetic Mean summary.
*   **Comparison Summary**: A high-level sheet summarizing the Average IPC (Geomean) and Average MPKI for each BTB type.
*   **Extensible**: Automatically detects any new BTB configurations added to the results file.
*   **Visuals**: Applies conditional formatting (color scales) to highlight performance hotspots (Green=Good for IPC, Green=Low for MPKI).

### How to Run
Run this script **after** collecting results with `collectStats/getResults.sh`.

```bash
python3 generate_report.py
```

### Arguments
1.  **Input File**: Path to the results file (default: `collectStats/all_res`).
2.  **Output File**: Path for the generated Excel report (default: `Analysis_Report.xlsx`).

**Example:**
```bash
python3 generate_report.py my_results.txt My_New_Report.xlsx
```
