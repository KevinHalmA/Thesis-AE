# Notebook summary — `notebooks/`

Each folder holds one self-contained `fit.ipynb` that uses **`da4ml.pack.fit_model`**
to map an **HGQ-\*** model (Table III) onto an FPGA by offloading lookups→BRAM /
adders→DSP (bit-exact). Shared method + model registry: [`_fit_common.py`](_fit_common.py). Contents and reproduction: [`README.md`](README.md).

## The four fit notebooks

| Notebook (folder) | Mode | Part | Target | clk / cutoff | What it demonstrates |
|---|---|---|---|---|---|
| `HGQ-LUT_jsc-plf_32p-3f` | fit **exact part** | `xcau7p-sbvc484-2-e` (Artix US+) | 37,440 LUT / 108 BRAM / 216 DSP | 3.0 ns / 2.5 | Squeeze the 3-feature GNN (41,594 LUT) onto a real part it *overflows* — a true LUT↔BRAM multi-resource fit. |
| `HGQ-Hybrid_tgc_1.90mrad` | fit −15% | `xczu7ev` (ref) | 26,020 LUT (0.85 × 30,612) | 6.25 ns / 8 | Muon-tracking 1.90 mrad operating point, −15% LUTs. |
| `HGQ-Hybrid_tgc_2.03mrad` | fit −15% | `xczu7ev` (ref) | 16,683 LUT (0.85 × 19,627) | 6.25 ns / 12 | Muon-tracking 2.03 mrad, −15% LUTs. |
| `HGQ-Hybrid_tgc_2.28mrad` | fit −15% | `xczu7ev` (ref) | 12,367 LUT (0.85 × 14,549) | 6.25 ns / 12 | Muon-tracking 2.28 mrad, −15% LUTs. |

> The N=64 F=16 GNN headline experiments (grids, DSP sweep, tight target,
> fitter validation) live in `HGQ-LUT_jsc-plf_64p-16f/` — see its README.

## Notebook shape

- **Standard fit** (`intro → config → load → fit → inspect → plot → SUMMARY`): one
  `fit_model` call. *fit −15%* mode constrains LUT to 0.85× the published baseline on
  the reference board (FF/BRAM/DSP unconstrained, zero margin). *fit exact part* mode
  instead targets a real smaller part's full capacity with da4ml's default safety
  margins, so all four resources bind.

## Running them

Traces are pre-cached, so the load cell is instant. Each notebook shells out to Vivado
(≈ 3 synth-only anchors + 1 confirm route):

```bash
source /tools/Xilinx/2025.1/Vivado/settings64.sh
jupyter lab notebooks/<folder>/fit.ipynb        # Run All with your venv kernel
```

Outputs land in the folder: `SUMMARY.md`, `result.json`, `fit_front.csv`, `fit_front.png`
Vivado scratch under
`_fit_work/`.

## Notes

- **`clock_period` (ns) ≠ `latency_cutoff`.** The cutoff is da4ml's pipeline-*depth*
  budget in LUT-delay *levels* (not ns); smaller → more stages → lower Fmax pressure,
  higher cycle-latency. See README.
- The da4ml in this venv is a **regular** site-packages install (not the editable source
  tree).
