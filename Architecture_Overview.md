# ChampSim Architecture Overview

This document provides a high-level overview of the ChampSim trace-based simulator architecture and details the specific modifications made to the core simulation engine to support the Multi-Retention STT-RAM BTB project.

## 1. ChampSim Overview

ChampSim is a heavily optimized, trace-based simulator designed for microarchitecture studies. It is primarily used to evaluate branch predictors, prefetchers, and replacement policies. 

The core simulates an Out-of-Order (OoO) pipeline with the following key stages:
*   **Fetch:** Reads instructions from the L1 instruction cache (or trace file) based on predictions from the Branch Target Buffer (BTB) and Branch Predictor.
*   **Decode:** Decodes instructions and identifies dependencies.
*   **Issue:** Dispatches instructions to reservation stations.
*   **Execute:** Simulates the execution latency of instructions (ALU, memory access, etc.).
*   **Commit (Retire):** Ensures instructions complete in program order and updates the architectural state.

In this project, ChampSim processes `.champsimtrace.xz` files, which contain pre-recorded execution traces, allowing for deterministic and reproducible evaluations of different hardware configurations.

## 2. Directory Structure

For the examiner, here is a guide to the key directories in this repository:

*   **`btb/`**: Contains all the Branch Target Buffer models evaluated in this project. Includes the baseline SRAM designs (`convBTB.btb`, `pdede.btb`, `BTBX.btb`) and our novel STT-RAM designs (`sttramBTB.btb`, `fixed-retentions-btb.btb`, `multi-retention-btb.btb`).
*   **`src/`**: Contains the core C++ source files for the ChampSim simulator. The most relevant files modified for this project are `ooo_cpu.cc` and `main.cc`.
*   **`inc/`**: Contains the C++ header files. Modifications to the `O3_CPU` class structure were made in `ooo_cpu.h`.
*   **`launch/` & `collectStats/`**: Contains bash scripts used to mass-generate configuration files, submit jobs to a cluster (`launch.sh`), and aggregate the resulting statistics (`getResults.sh`).
*   **`scripts/`**: Miscellaneous scripts, including trace downloaders and the `generate_report.py` python script which parses the final results into an Excel report.
*   **`prefetcher/` & `replacement/`**: Contains implementations for various instruction/data prefetchers and cache replacement policies.

## 3. Core Simulator Modifications

To accurately model the physical characteristics of STT-RAM (specifically its asymmetric, high write latency and data volatility), significant modifications were made to the core ChampSim engine.

### A. Fetch Stalling (`inc/ooo_cpu.h` & `src/ooo_cpu.cc`)

Unlike SRAM, where writes are fast enough to complete within a standard pipeline cycle, updating an STT-RAM BTB entry can take multiple cycles (e.g., up to 4 cycles for a 100ms retention zone). 

To model this, we introduced a fine-grained stall mechanism in the fetch stage:
*   **Variables Added:** `fetch_stall` (boolean flag) and `fetch_resume_cycle` (timestamp) were added to the `O3_CPU` class in `ooo_cpu.h`.
*   **Stall Logic:** When the BTB is updated (during branch resolution), the `update_btb()` function returns a specific stall latency (e.g., 2, 3, or 4 cycles) based on the target retention zone. The core then sets `fetch_stall = true` and calculates the `fetch_resume_cycle`.
*   **Pipeline Halting:** In the main simulation loop within `ooo_cpu.cc` (specifically in the fetch stages), the pipeline checks `fetch_stall`. If true, the fetch stage is halted until the current cycle reaches the `fetch_resume_cycle`.

### B. Speculative Instruction Prefetching (`src/ooo_cpu.cc`)

Completely halting the fetch stage during an STT-RAM write penalty severely degrades IPC. To mitigate this, we modified the core to allow speculative prefetching to continue even while the main fetch pipeline is stalled.

*   **`spec_inst_prefetch()`:** This new function was introduced to decouple the L1I prefetcher from the main instruction fetch loop. While the main pipeline is stalled waiting for a BTB write to complete, the prefetcher is still permitted to issue requests down the memory hierarchy, hiding the latency of the STT-RAM write.

### C. Multi-Retention Statistics (`src/main.cc`)

To evaluate the dynamic behavior of our Multi-Retention BTB, the core needed to track metrics that standard ChampSim does not capture.

*   **Metric Tracking:** Global variables were added to `main.cc` and `ooo_cpu.h` to track:
    *   `multi_ret_zone1_hits`, `multi_ret_zone2_hits`, `multi_ret_zone3_hits`: The number of successful branch predictions served from the 1ms, 10ms, and 100ms zones, respectively.
    *   `multi_ret_promotions`: The total number of times an entry was promoted to a higher retention tier.
*   **Report Generation:** The end-of-simulation print routines in `main.cc` were modified to output these custom metrics in a specific format (e.g., `XXX MULTI_RET_STATS`). This formatted output is subsequently parsed by our `getResults.sh` and `generate_report.py` scripts to generate the final analysis spreadsheet.
*   **Volatility Modeling:** Support was also added to track `sttram_refreshes` and `sttram_evictions` globally, enabling analytic modeling of the energy costs associated with data retention policies.