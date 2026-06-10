# LUT-fitting notebooks — pack each HGQ-\* model into ~15% fewer LUTs

One folder per **HGQ-\*** model from the paper's Table III. Each `fit.ipynb` uses
[`da4ml.pack.fit_model`](../../da4ml/src/da4ml/pack/fit.py) to find a **bit-exact**
BRAM/DSP offload that fits the model into **0.85 × its published LUT count** on the
reference part — i.e. a ~15% LUT saving, traded into the BRAM/DSP that every HGQ-\*
row leaves at **DSP = 0**.

> **HGQ-LUT (GNN) 64p-16f is intentionally excluded** (already done elsewhere).

## Models (folder → Table III row)

| Folder | Table III row | Baseline LUT | Target | Trace cache |
|---|---|---:|---|---|
| `HGQ-LUT_jsc-plf_32p-16f` | HGQ-LUT (GNN) 32, 16 feat | 25,288 | 21,495 LUT (0.85×) on ref part | `models/jsc_plf/32-16/model_traced_n32_f16.keras` |
| `HGQ-LUT_jsc-plf_32p-3f`  | HGQ-LUT (GNN) 32, 3 feat  | 41,594 | **fit `xcau7p` exactly** (37,440 LUT / 108 BRAM / 216 DSP) — Artix US+ | `models/jsc_plf/32-3/model_traced_n32_f3.keras` |
| `HGQ-Hybrid_tgc_1.90mrad` | HGQ-Hybrid, 1.90 mrad     | 30,612 | 26,020 LUT (0.85×) on ref part | `models/tgc/traced_1.90mrad.keras` |
| `HGQ-Hybrid_tgc_2.03mrad` | HGQ-Hybrid, 2.03 mrad     | 19,627 | 16,683 LUT (0.85×) on ref part | `models/tgc/traced_2.03mrad.keras` |
| `HGQ-Hybrid_tgc_2.03mrad_z010` | HGQ-Hybrid, 2.03 mrad | 19,627 | **fit `xc7z010` exactly** (17,600 LUT / 60 BRAM / 80 DSP) — **Zynq-7000, not US+** | `models/tgc/traced_2.03mrad.keras` (reused) |
| `HGQ-Hybrid_tgc_2.03mrad_a35t` | HGQ-Hybrid, 2.03 mrad | 19,627 | **pure-LUT vs autofit on `xc7a35t`** (20,800 LUT / 50 BRAM / 90 DSP) — **Artix-7, free** | `models/tgc/traced_2.03mrad.keras` (reused) |
| `HGQ-Hybrid_tgc_2.28mrad` | HGQ-Hybrid, 2.28 mrad     | 14,549 | 12,367 LUT (0.85×) on ref part | `models/tgc/traced_2.28mrad.keras` |

**Two part-constrained experiments** fit the *exact capacity of a real, smaller part*
(with da4ml's default safety margins) instead of an artificial 0.85× budget — a
genuine multi-resource squeeze where the baseline overflows the chip:

- **`jsc-plf_32p-3f` → `xcau7p-sbvc484-2-e`** (Artix US+): baseline 41,594 LUT
  overflows the 37,440-LUT part; usable ≈ 33,696 LUT / 102 BRAM / 205 DSP. Max BRAM
  offload alone needs ~490 tiles ≫ 108, so the fitter must balance LUT↔BRAM.
  *Feasibility probe: comfortably fits (~31k LUT / ~54 BRAM / 0 DSP).*
- **`tgc_2.03mrad_z010` → `xc7z010clg400-3`** (**Zynq-7000 — proves the flow works
  outside UltraScale+**): baseline 19,627 LUT overflows the 17,600-LUT part; usable
  ≈ 15,840 LUT / 57 BRAM / 76 DSP. This model is adder-dominated (only 575 lookups),
  so BRAM-only floors at ~17k LUT (~7% over) and the fit *must* recruit DSP-adders to
  duck under — **borderline; may return INFEASIBLE.** Either outcome demonstrates
  `fit_model` calibrating + running on a 7-series part. ⚠ The cost model's fixed
  synth→route LUT factor (0.977) and BRAM/DSP geometry were validated on US+; the
  per-part slopes re-calibrate here and `confirm=True` routes the winner to validate.

**`tgc_2.03mrad_a35t` is a before/after comparison** (`route_baseline=True`) on the
free-WebPACK **Artix-7 `xc7a35tcsg324-1`** (20,800 LUT / 50 BRAM / 90 DSP). It does a
*real place+route of the unmarked pure-LUT design* (~94% LUT → P&R congestion / likely
timing miss, handled even if it fails to place), then runs the autofitter (which offloads
to ~87–89% LUT + ~15–37 BRAM, 0 DSP), and writes a `compare.csv` / `compare.png` /
`SUMMARY.md` contrasting the two routes (LUT %, Fmax, met-timing). This is the clearest
"why fit at all" demo. Switch any model between the modes via `fit_part_budget` /
`route_baseline` in `_fit_common.py`.

## Method (identical across models, set in [`_fit_common.py`](_fit_common.py))

- **Part** `xczu7ev-ffvc1156-2-e` — the Zynq US+ reference the Table III numbers
  were measured on. The LUT constraint is artificial (the chip has 230k LUT); the
  point is to prove the offload, not to change boards. *(Except `jsc-plf_32p-3f`,
  which targets the real `xcau7p-sbvc484-2-e` it overflows — see above.)*
- **Budget** `lut = 0.85 × Table III LUT`, **zero LUT margin** → "fits" means
  *predicted post-route LUT ≤ 0.85 × baseline*. FF/BRAM/DSP = full part. *(For the
  part-constrained model: budget = exact part capacity with da4ml's default safety
  margins, so all four resources bind.)*
- **Objective** `(min_dsp, min_bram)` — hit the LUT target using the fewest DSPs,
  then the fewest BRAMs (a BRAM-backed, DSP-free fit is preferred).
- **Clock vs latency-cutoff — different units, not comparable numbers.** `clock_period`
  (ns) is the Vivado timing constraint. `latency_cutoff` is da4ml's **pipeline-depth
  budget in LUT-delay *levels*** (a LUT6 resolves 6 input bits per level; op delay grows
  ~`max(bw_in−6,1)` per op), and the graph is split into a new stage every `latency_cutoff`
  levels (`stage = floor(op.latency / latency_cutoff)`). Smaller cutoff → more stages →
  lower achievable clock but higher cycle-latency. Values are taken verbatim from the
  paper's repo: tgc `6.25 ns / 12` (→ ~3–4 stages, matching Table III's 4–5-cycle tgc
  latency at ~163 MHz on the **fast Zynq US+**), `32p-16f` `2.5 ns / 3.1`, `32p-3f`
  `3.0 ns / 2.5`. ⚠ The `12` was latency-optimised for US+; on a **slow Artix-7** a
  12-level stage may exceed 6.25 ns → negative WNS, so the `xc7a35t`/`xc7z010` notebooks
  may need a smaller cutoff (more stages) to close timing — orthogonal to the LUT fit.
- `confirm=True` routes the winner once to validate predicted-vs-actual.

`fit_model` runs **3 synth-only Vivado anchors** to calibrate, picks by pure
arithmetic, then **1 full place+route** to confirm — so expect ~4 Vivado
invocations per notebook (a handful of minutes for synth, longer for the route).

## Running

The quantiser traces are already cached, so the load cell is instant. Just open a
notebook and Run All (kernel `ml5090-312`):

```bash
source /tools/Xilinx/2025.1/Vivado/settings64.sh   # fit_model shells out to Vivado
jupyter lab notebooks/HGQ-LUT_jsc-plf_32p-16f/fit.ipynb
```

Each run writes, into the model's folder:
`fit_front.csv` (full predicted candidate front), `result.json`, `SUMMARY.md`,
and `fit_front.png` (the LUT↔BRAM trade with the budget line + chosen point).
Vivado scratch goes to `<folder>/_fit_work/`.

Regenerate the notebooks after editing the generator:

```bash
python notebooks/_gen.py
```

## Notes

- **Latency is not constrained** by the default objective — BRAM offload inserts
  output registers, so the chosen config may add pipeline stages vs. the Table III
  baseline (reported in each `SUMMARY.md`). Add `min_latency` to the objective, or
  pass a tighter candidate set, if you want to bound it.
- TGC is "hybrid" but still traces to **0 vmul ops**, so (like the pure-LUT models)
  the working levers are BRAM (lookups) + comb DSP-adders — exactly the default
  candidate front. `mark_dsp`/`dsp_offload` are no-ops here.
