# JSC PLF 64p-16f — thesis headline experiments

Reproduction notebooks for the headline results of the thesis (pipeline-stage-aware
resource mapping + predictive part fitting), all on the N=64 F=16 JSC PLF
checkpoint in `../../models/jsc_plf/64-16/`. Each directory is one experiment:
the notebook drives trace -> mark passes -> RTL -> Vivado and saves its metrics
CSV and figures next to it. The committed CSV/PNG files and the cells' stored
outputs are the measured results the thesis reports; re-running regenerates them.

All paths in the notebooks are repo-relative. The shared helpers live in this
directory: `model.py` / `data.py` (checkpoint loading, incl. the `SameDim0`
constraint, and dataset access), `dump_bram.tcl` (post-route RAMB dump), and
`cocotb_jsc_test_runner.py` (optional simulation cross-check).

## Requirements

- The patched da4ml fork: https://github.com/KevinHalmA/da4ml, branch `main`
  (results in this folder produced at commit `df88697`)
- Vivado 2025.1 (parts: `xczu7ev-ffvc1156-2-e`, `xcau7p-sbvc484-2-e`,
  `xcau10p-sbvb484-2-e`); set `VIVADO_SETTINGS` in each notebook's config cell
  to your `settings64.sh`
- HGQ2 + Keras 3 + JAX for checkpoint loading (see `../../env.yml`)
- The JSC dataset: run `../../prepare_datasets.sh` once; it populates
  `../../dataset/jsc_plf/150c-{train,test}.h5`, which is where the notebooks
  look

## Experiments

| Directory | What it measures | Thesis result |
|---|---|---|
| `bram_grid_paired/` | 11x11 paired-BRAM `(bw_in, bw_out)` grid, 122 configs, 5 ns | The LUT-BRAM surface; headline `bram(7,5)`: -16.8% LUT at ~paper clock, zero DSP |
| `bram_grid_unpaired/` | Same grid without `pair_within_stage` (Experiment A) | LUT-vs-BRAM Pareto front; paired-vs-unpaired tile delta baseline |
| `dsp_summary/` | `mark_dsp_adder` sweep on the two BRAM bases (Experiment B) + tight 2.5 ns rerun (Experiment C) + cross-experiment Pareto | DSP-adder operating points; clocked-vs-comb; points dominating the paper baseline on (LUT, Fmax); "most LUT relief costs zero DSP" headline |
| `fit_xcau7p/` | `da4ml.pack.fit_model` on the $60 `xcau7p`: 3 synth anchors + 1 confirm route | Fitter validation table (`bram(8,7)`, prediction vs measured) |
| `part_fit_demo/` | Hand-tuned predicate selection on the same part and clock | Auto-vs-manual comparison table |
| `bram_fill/` | RAMB18 fill fraction, paired vs unpaired | Memory-tile packing section |

Suggested order: `bram_grid_unpaired` -> `bram_grid_paired` -> `dsp_summary`
(consumes the paired CSV) -> `fit_xcau7p` / `part_fit_demo`. `dsp_summary` can
regenerate all of its figures from the committed CSVs with
`BUILD_RTL=False` (the default), no Vivado or model loading needed.

The cross-model generality fits (N=32 F=3 GNN and the three TGC HGQ-Hybrid
checkpoints) live in the sibling `HGQ-LUT_jsc-plf_32p-3f/` and
`HGQ-Hybrid_tgc_*/` directories.
