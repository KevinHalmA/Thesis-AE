# track1_dsp_summary — DSP-adder layering + headline LUT/Fmax study

Self-contained writeup of `dsp_and_summary.ipynb`, for the thesis Results chapter.

## Why this experiment exists

Sub-exp B layers `mark_dsp_adder` (comb vs clocked) on the two paired-BRAM bases from Folder 1; sub-exp C re-runs a spanning subset at the tight 2.5 ns target to place them against the HGQ-LUT paper on the LUT-vs-Fmax plane.

## Setup

| Knob | Value |
|---|---|
| B target | 5.0 ns / 3.1 ns |
| C target | 2.5 ns / 2.0 ns |
| `HWConfig` | (1, -1, -1) |
| BRAM bases | [('bram_7_5', (7, 5)), ('bram_6_3', (6, 3))] (pair_within_stage=True) |
| `max_iter` (dsp_adder) | 1024 |
| `MAX_VIVADO_PAR` | 3 |

## Results

- Sub-exp B: 42 configs, 31 timing-met.
- Sub-exp C: 6 configs at tight target, 4 met.
- Beat the paper (39765 LUT, 383.6 MHz) on BOTH LUT and Fmax: 2 point(s) — but at a markedly higher cycle count (see the cycle column; these are not free wins).
- Bit-exact + Verilator confirmed (subsets ['bram_7_5__boNone', 'bram_7_5__bo15_clocked'] / ['bram_7_5__bo15_clocked', 'bram_6_3__boNone']).

## Operating points worth highlighting

| label | LUT | BRAM | DSP | Cyc | Fmax_pr | WNS_pr | Status |
|---|---|---|---|---|---|---|---|
| bram_7_5__boNone | 33094 | 99.5 | 0 | 30 | 376.6 | -0.155 | routing_fail |
| bram_7_5__bo15_clocked | 34138 | 101.0 | 148 | 44 | 414.1 | +0.085 | met |
| bram_7_5__bo11_clocked | 46556 | 100.5 | 674 | 77 | 401.8 | +0.011 | met |
| bram_6_3__boNone | 30548 | 257.0 | 0 | 31 | 366.3 | -0.230 | routing_fail |
| bram_6_3__bo15_clocked | 31984 | 257.5 | 148 | 48 | 406.5 | +0.040 | met |
| bram_6_3__bo11_clocked | 44804 | 258.5 | 674 | 85 | 402.1 | +0.013 | met |

## What this experiment establishes

1. The trade-off surface — (LUT, Fmax, cycles, latency) together, not any single 2-D slice — is the contribution. Reading LUT-vs-Fmax alone is misleading: the higher-Fmax points add many cycles, which is exactly the cycles↔Fmax trade da4ml's pipelining already provides.
2. High-Fmax extreme: bram_7_5__bo15_clocked @ 414.1 MHz, 34138 LUT — but 44 cycles (106.3 ns latency).
3. Low-LUT extreme: bram_6_3__bo15_clocked @ 31984 LUT, 406.5 MHz, 48 cycles.
4. clocked DSP-adder buys Fmax at a cycle cost that scales with clocked-stage cuts; comb mode preserves cycles but Vivado infers fewer DSPs (compare `dsp` vs `dsp_promoted_ir` in `dsp_sweep_metrics.csv`).
5. Every config bit-exact (SW gate all configs + Verilator subset).

## Honest caveats

- An Fmax win that costs a large cycle increase is **not** a free improvement: compare end-to-end ns-latency (cycles x achieved period), not Fmax in isolation.
- The unmarked tight-target `paper_baseline` is excluded from the headline (Vivado-target artefact, not an IR-pass result).
- Fill in any place_fail/routing_fail configs from the CSV status column.
- Bit-exactness held on all sub-exp B+C configs; Verilator confirmed on subsets.
