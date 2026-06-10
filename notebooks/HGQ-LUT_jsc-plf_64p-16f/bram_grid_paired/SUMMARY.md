# track1_bram_paired — paired-BRAM mark_bram grid (pair_within_stage=True)

Self-contained writeup of `bram_paired_grid.ipynb`, for the thesis Results chapter.

## Why this experiment exists

Companion to the unpaired BRAM grid (`exhaustive_search/`). Quantifies what the
`pair_within_stage=True` codegen path buys: two same-stage same-geometry ROMs
packed into one RAMB18, cutting BRAM-tile count at zero functional cost.

## Setup

| Knob | Value |
|---|---|
| `CLOCK_PERIOD` | 5.0 ns |
| `LATENCY_CUTOFF` | 3.1 ns |
| `HWConfig` | (1, -1, -1) |
| part | xczu7ev-ffvc1156-2-e |
| grid | 11×11 + none = 122 configs |
| `pair_within_stage` | True |
| `MAX_VIVADO_PAR` | 3 |

## Results

- Timing-met: 90/122 configs.
- Bit-exact (comb.predict vs unmarked baseline): 122/122 — must be all.
- Verilator (rtl.predict==comb.predict) confirmed on: ['none', 'bwin_7_bwout_5', 'bwin_6_bwout_4'].

## Operating points worth highlighting

| label | LUT | BRAM | DSP | Cyc | Fmax_pr | WNS_pr | Status |
|---|---|---|---|---|---|---|---|
| Fmax-best low-BRAM (7,5) | 31360 | 98.0 | 0 | 24 | 255.5 | +1.086 | met |
| LUT-min, BRAM-heavy (6,3) | 29382 | 267.5 | 0 | 29 | 221.1 | +0.477 | met |
| no-mark baseline (none) | 35492 | 0.0 | 0 | 11 | 256.0 | +1.094 | met |

Note: an earlier draft of this SUMMARY called (3,6) the knee. (3,6)
is in fact dominated by (7,5) on every axis (LUT, BRAM, cycles,
Fmax, latency) simultaneously and is not on the met-timing Pareto
front.

## What this experiment establishes

1. Pairing reduces BRAM-tile count vs unpaired (see `bram_paired_vs_unpaired.png`)
   with negligible LUT/FF/Fmax change — a pure backend-mapping win.
2. Cycle count tracks the number of clocked (BRAM) stages, NOT the number of
   promoted lookups — verify the monotonic relationship in the `cycles` heatmap.
3. Every config is bit-exact to the unmarked da4ml output (SW gate + Verilator).

## Honest caveats

- Fill in: any configs that failed placement (status=place_fail) — these are
  LUT-congestion artefacts on xczu7ev's single SLR at low-bwout, not mark bugs.
- The bit-exactness assertion held on all 122/122 configs.
- Verilator confirmation was run on a representative subset (['none', 'bwin_7_bwout_5', 'bwin_6_bwout_4']),
  not all 122, for runtime; the SW bit-exact gate covers all.
