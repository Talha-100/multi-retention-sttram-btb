# Branch Target Buffers (BTBs)

This document provides a description of the different Branch Target Buffer (BTB) implementations available in `btb/**`. It covers the architecture, underlying memory technology, and any major modifications from previous iterations.

---

## `convBTB.btb`

*   **Memory Technology:** SRAM
*   **Architecture Description:** This is a conventional BTB design that stores the full target addresses of branches. It serves as the baseline for performance and storage comparisons. 
*   **Citations:** Baseline conventional BTB described and evaluated in:
    *   *T. Asheim, B. Grot, and R. Kumar, "A Storage-Effective BTB Organization for Servers," 2023 IEEE International Symposium on High-Performance Computer Architecture (HPCA).*

---

## `pdede.btb`

*   **Memory Technology:** SRAM
*   **Architecture Description:** PDede (Partitioned, Deduplicated, Delta branch target buffer) is an advanced BTB organization that aims to reduce storage costs by compressing branch targets. It partitions the BTB into a Main-BTB, a Page-BTB, and a Region-BTB. By storing page and region numbers only once for all branches within the same page/region, PDede significantly avoids duplication of information. 
*   **Citations:**
    *   Evaluated against in: *T. Asheim, B. Grot, and R. Kumar, "A Storage-Effective BTB Organization for Servers," 2023 IEEE International Symposium on High-Performance Computer Architecture (HPCA).*
    *   Original paper: *N. K. Soundararajan et al., "Pdede: Partitioned, deduplicated, delta branch target buffer," in MICRO-54: 54th Annual IEEE/ACM International Symposium on Microarchitecture, 2021.*

---

## `BTBX.btb`

*   **Memory Technology:** SRAM
*   **Architecture Description:** BTB-X is a storage-effective BTB organization that stores branch target offsets instead of full or compressed targets. Based on the insight that the vast majority of branch target offsets require only a few bits to encode, it uses an 8-way set associative BTB where each way is sized to hold a different number of target offset bits. This allows it to capture more branches within the same storage budget compared to conventional BTBs and PDede.
*   **Citations:**
    *   *T. Asheim, B. Grot, and R. Kumar, "A Storage-Effective BTB Organization for Servers," 2023 IEEE International Symposium on High-Performance Computer Architecture (HPCA).*

---

## `sttramBTB.btb`

*   **Memory Technology:** STT-RAM (Spin-Transfer Torque Random-Access Memory)
*   **Architecture Description:** This implementation adapts the BTB-X architecture to use STT-RAM instead of SRAM. STT-RAM provides a significantly higher storage density, allowing the capacity of the BTB to be increased by 4x compared to the SRAM baseline. In this initial STT-RAM implementation, all entries operate in a single retention zone.
*   **Changes/Details:** 
    *   Capacity is increased by 4x due to STT-RAM density.
    *   Implements a static write latency of 8 cycles for all STT-RAM writes.
*   **Citations:**
    *   Architecture based on BTB-X: *T. Asheim, B. Grot, and R. Kumar, "A Storage-Effective BTB Organization for Servers," 2023 IEEE HPCA.*
    *   STT-RAM capacity scaling (4x) and characteristics based on: *X. Dong et al., "NVSim: A Circuit-Level Performance, Energy, and Area Model for Emerging Nonvolatile Memory," IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, 2012.*

---

## `fixed-retentions-btb.btb`

*   **Memory Technology:** Multi-Retention STT-RAM
*   **Architecture Description:** Building on top of `sttramBTB.btb`, this design optimizes STT-RAM write performance by taking advantage of Multi-Retention STT-RAM. Instead of a single static retention time and write latency for the entire BTB, it maps different BTB-X partitions (ways) to specific retention "zones" based on their observed write intensity.
*   **Changes/Details:**
    *   Retains the 4x density advantage of STT-RAM.
    *   Implements variable write latencies dynamically based on the target partition (way) being updated.
    *   **Retention Zone Mapping:**
        *   **Zone 1:** 1ms retention, allocated to high-write Partition IDs 0, 1, 3. Write Latency: 4 Cycles (+1 Cycle stall vs SRAM).
        *   **Zone 2:** 10ms retention, allocated to Partition IDs 2, 4, 6, 8. Write Latency: 7 Cycles (+4 Cycles stall vs SRAM).
        *   **Zone 3:** 100ms retention, allocated to low-write Partition IDs 5, 7. Write Latency: 11 Cycles (+8 Cycles stall vs SRAM).
*   **Citations:**
    *   Architecture based on BTB-X: *T. Asheim, B. Grot, and R. Kumar, "A Storage-Effective BTB Organization for Servers," 2023 IEEE HPCA.*
    *   STT-RAM capacity scaling, retention zones, and modeling characteristics based on: *X. Dong et al., "NVSim: A Circuit-Level Performance, Energy, and Area Model for Emerging Nonvolatile Memory," IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, 2012.*

---

## `multi-retention-btb.btb`

*   **Memory Technology:** Multi-Retention STT-RAM
*   **Architecture Description:** This design utilizes the BTB-X architecture with a dynamic promotion policy. The BTB is logically partitioned into three retention zones (1ms, 10ms, 100ms). Entries are promoted to higher retention tiers upon successful branch hits to optimize the trade-off between write latency and data volatility.
*   **Changes/Details:**
    *   Retains the 4x density advantage of STT-RAM.
    *   **Zone 1:** 1ms retention, capacity 50% (Sets 0-1023). Write Latency: 2 Cycles.
    *   **Zone 2:** 10ms retention, capacity 25% (Sets 1024-1535). Write Latency: 3 Cycles.
    *   **Zone 3:** 100ms retention, capacity 25% (Sets 1536-2047). Write Latency: 4 Cycles.
    *   **Dynamic Policy:** Insertion into Zone 1. Promotion to higher zones on branch hits. Eviction is LRU per zone.
*   **Output:** Generates `XXX MULTI_RET_STATS` lines containing zone hits, promotions, and adjusted IPC.
