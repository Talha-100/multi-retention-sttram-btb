# Analysis Motivation & Implementation Summary: STT-RAM Volatility in Branch Target Buffers

This document provides a comprehensive overview of the implementation and motivation behind evaluating STT-RAM (Spin-Transfer Torque Random-Access Memory) volatility management policies within a Branch Target Buffer (BTB). This summary is designed to explain the methodology, code changes, and resulting data to a technical audience familiar with ChampSim and general computer architecture concepts.

## 1. Project Motivation: Why STT-RAM for BTBs?

Modern server workloads suffer from high instruction cache miss rates and branch mispredictions, often due to large instruction footprints that exceed the capacity of conventional SRAM-based BTBs. STT-RAM is an emerging non-volatile memory technology that offers significantly higher density than SRAM. This project evaluates STT-RAM as a replacement for SRAM to increase BTB capacity (by a factor of 4x) without increasing the physical footprint.

However, STT-RAM introduces two major challenges:
1.  **High Write Latency:** STT-RAM takes significantly longer to write than SRAM.
2.  **Volatility Trade-offs:** To mitigate write latency, the *retention time* of the STT-RAM cells can be reduced (Multi-Retention STT-RAM). A lower retention time decreases write latency and energy, but requires a policy to handle entries that expire (lose their data) before they are naturally evicted.

## 2. Baseline Profiling (`convBTB.btb`)

Before implementing STT-RAM policies, we needed to understand the natural lifespan of BTB entries. We instrumented the baseline conventional SRAM BTB (`btb/convBTB.btb`) to track two metrics when an entry is evicted:
1.  **Lifetime:** The duration (in CPU cycles) an entry stayed in the BTB (`current_cycle - write_timestamp`).
2.  **Hit Count:** The number of times the entry successfully provided a prediction during its lifetime.

### Code Implementation (`btb/convBTB.btb`)
We modified the `update_BTB` function. When a new branch target requires eviction of an existing entry, the code calculates the lifetime and categorizes the evicted entry into a 2D array (`mot_stats[4][5]`).

*   **Lifetime Zones (4 Zones):**
    *   Zone 0: <= 1ms (assuming 4GHz, this is <= 4,000,000 cycles)
    *   Zone 1: > 1ms and <= 10ms
    *   Zone 2: > 10ms and <= 100ms
    *   Zone 3: > 100ms
*   **Hit Count Buckets (5 Buckets):** 1 hit, 2 hits, 3 hits, 4 hits, 5+ hits (0 hits are grouped into the 1 hit bucket for profiling purposes).

### Results Analysis (`data_csv/Analysis_Motivation.csv` & `Read_Hit_Distribution.csv`)
*Note: This data is typically extracted and summarized in `Analysis_Motivation.csv` and visualized in `Read_Hit_Distribution.csv`.* It shows that a massive percentage of BTB entries are "dead on arrival" (0-1 hits) and have very short useful lifetimes.

This data justifies the use of reduced retention STT-RAM. If most entries are short-lived, allocating long (non-volatile) retention times to them is a waste of write latency and energy.

## 3. STT-RAM Volatility Management (`sttram_volatile_core.h`)

To evaluate the impact of reduced retention times, we built a parameterized core BTB model (`btb/sttram_volatile_core.h`) that supports two distinct volatility management policies across four theoretical retention times (1ms, 10ms, 100ms, 1s).

### Policy A: Refresh (REF)
Instead of simulating the complex dynamic microarchitecture of periodic refreshing, we use an *Analytic Deduction Method*.
*   **Mechanism:** When an entry is evicted, the simulation calculates how many times it *would have* expired and required a refresh during its observed lifetime: `refreshes = lifetime / RETENTION_CYCLES`. This is added to a global counter (`sttram_refreshes`).
*   **End of Simulation:** At the end of the run (`dump_stt_write_stats`), we iterate through all valid entries remaining in the BTB and calculate their accumulated refreshes up to that point.
*   **Performance Impact:** The total number of refreshes is multiplied by the write latency penalty (`WRITE_PENALTY`) of the specific retention configuration. These penalty cycles are added to the total execution cycles to calculate an **Adjusted IPC**.

### Policy B: Write-Back / Eviction (WB)
This policy simply allows entries to expire.
*   **Mechanism:** During a branch prediction lookup (`btb_prediction`), the code checks if the requested entry has expired: `(current_core_cycle - btb_entry->write_timestamp) > RETENTION_CYCLES`.
*   **Performance Impact:** If expired, the entry is invalidated, a global counter (`sttram_evictions`) is incremented, and the simulation treats it as a BTB Miss. This naturally impacts performance by increasing branch mispredictions and fetch stalls.

## 4. Configuration Wrappers (`btb/volatile_wrappers/`)

To test these policies without duplicating the core logic, we use a wrapper pattern. For example, `volatile_wrappers/conv-sttram-ref-100ms.btb` simply defines the necessary macros before including the core logic:

```cpp
#define VOLATILE_POLICY_REFRESH
#define RETENTION_CYCLES 400000000 // 100ms @ 4GHz
#define WRITE_PENALTY 4            // Stalls associated with 100ms STT-RAM
#include "sttram_volatile_core.h"
```
This approach allows us to cleanly compile 8 different ChampSim binaries (2 policies x 4 retention times) using the exact same underlying mechanics.

## 5. Result Extraction & Energy Modeling (`data_csv/STT_VOLATILE_RESULTS.csv`)

The custom python script (`update_motivational_excel.py`) parses the raw ChampSim logs to build `STT_VOLATILE_RESULTS.csv`. It extracts the baseline metrics (Instructions, IPC, BTB Reads/Writes) alongside our new `STT_VOLATILE_STATS` (Refreshes, Evictions, Adjusted IPC). It also groups the data to average performance across the `fdip` and `no` prefetcher configurations.

Crucially, the script calculates **Energy (mJ)** using an analytical model derived from NVSim/TEEMO parameters for 22nm STT-RAM:
*   **Dynamic Energy:** Considers the energy of all normal writes, all normal reads, *and* the energy cost of all Refresh writes (if using the Refresh policy).
*   **Static Energy:** Calculates leakage power based on the total simulation time (cycles / frequency).

### Key Takeaways from `STT_VOLATILE_RESULTS.csv`
When analyzing this final CSV, observe the trade-offs:
*   **1ms Retention:** Likely shows the lowest base write energy, but suffers heavily from either massive refresh counts (killing Adjusted IPC and spiking dynamic energy) or massive eviction counts (killing base IPC due to miss rates).
*   **1s Retention:** Acts almost like non-volatile memory with 0 refreshes/evictions, but incurs the highest write latency penalty and per-write dynamic energy cost.
*   **The "Sweet Spot":** The goal is to identify which policy (Refresh vs. WB) and which retention time provides the optimal balance of IPC, MPKI, and Total Energy.