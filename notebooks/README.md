# Thesis notebooks — contents and reproduction

## What is here

| path | contents |
|---|---|
| `HGQ-LUT_jsc-plf_32p-3f/` | `fit.ipynb` — the N=32, 3-feature GNN squeezed onto the exact capacity of `xcau7p` (its 41,594-LUT baseline overflows the 37,440-LUT part). |
| `HGQ-Hybrid_tgc_{1.90,2.03,2.28}mrad/` | `fit.ipynb` per model — the three muon-tracking models fit into 0.85× their published LUT count on `xczu7ev`. |
| `HGQ-LUT_jsc-plf_64p-16f/` | The headline N=64 experiments: BRAM grids, DSP sweeps, BRAM fill, part-fit demos. See its own `README.md`. |
| `relaxed_prototype/` | Relaxed-staging prototype runs (thesis §3.3). See its own `README.md`; needs the fork at `b9b2db4` or later. |
| `_fit_common.py` | Shared config for the four fit notebooks: parts, budgets, clocks, objective, model registry. |
| `NOTEBOOK_SUMMARY.md` | Per-notebook summary of the fit results. |

Every fit folder ships its executed outputs — `SUMMARY.md`, `result.json`,
`fit_front.csv`, `fit_front.png` — so all results can be inspected, and the
figures regenerated, without running Vivado.

## Environment

1. Create the Python environment from [`../env.yml`](../env.yml) (micromamba or
   conda, as in the repository root readme).
2. Install the **patched da4ml fork** in place of the pip release — the passes
   and `da4ml.pack` only exist there:

   ```bash
   pip install "git+https://github.com/KevinHalmA/da4ml@df88697"   # thesis results
   # use @b9b2db4 (or later) for relaxed_prototype/
   ```

3. Register a Jupyter kernel for that environment and select it when opening
   the notebooks. The committed notebooks reference the author's local kernel
   name (`ml5090-312`) — substitute your own; nothing depends on the name.
4. Vivado 2025.1, sourced before launching Jupyter
   (`source /tools/Xilinx/<ver>/Vivado/settings64.sh`); the notebooks shell
   out to it. Datasets come from [`../prepare_datasets.sh`](../prepare_datasets.sh);
   the quantiser traces are cached under [`../models/`](../models/), so the
   model-loading cells are instant.

## Reproducing a fit

Open a folder's `fit.ipynb` **from inside that folder** and Run All. Each run
is three synthesis-only calibration anchors plus one confirming place-and-route
(~4 Vivado invocations; minutes for the anchors, tens of minutes for the
route). Outputs overwrite the committed ones in the same folder; Vivado scratch
goes to `<folder>/_fit_work/`.
