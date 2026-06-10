# The auto-searcher (`da4ml.pack.fit_model`) — what it is, how it works, thesis notes

Quick reference for writing this up. Numbers below are from the validated runs
in this folder (`fit_n64_xcau7p.ipynb`) and the wider characterisation
(`autotest/`, `track1_*`, `exhaustive_search/`, ~552 synth / 406 route runs).

---

## 1. What it is

An **automated, predictive resource-aware fitter** for quantised-NN FPGA
inference. Given a trained HGQ-LUT model and a target UltraScale+ board, it
**chooses the resource-mapping predicate** (which lookups → BRAM, which adders →
DSP) that fits the model onto the board — without an exhaustive Vivado sweep and
without expert hand-tuning.

It is the automation layer on top of the IR passes: the passes give the *knobs*;
the searcher *turns them automatically* for a given device budget. Upstreamed as
`da4ml.pack.fit_model`.

```python
from da4ml.pack import fit_model
result = fit_model(comb, budget=dict(lut=37440, ff=74880, bram=108, dsp=216),
                   part_name='xcau7p-sbvc484-2-e', vivado_settings=...,
                   clock_period=4.0, latency_cutoff=3.0,
                   objective=('min_dsp', 'min_bram'), confirm=True)
print(result.summary())
```

---

## 2. How it works (calibrate → predict → select → confirm)

1. **Calibrate** — 3 **synth-only** Vivado runs on the target part:
   - `A0` baseline (no marks), `A1` bram-max (`≥4,4` floor), `A2` dsp-cal.
   - Synth-only is fast (~4 min) **and survives placement failure** — the post-synth
     utilisation report is written *before* `place_design`, so even a
     deliberately-overflowing anchor yields exact BRAM/DSP and a conservative LUT
     estimate.
2. **Build the cost model** (per model, board, clock):
   - **LUT** affine in the IR's size-weighted `comb.cost` (which already nets out
     BRAM/DSP savings): `LUT* = a + b·cost − c·dsp_adder_cost`, then ×~0.977 for route.
   - **FF** affine in `reg_bits`.
   - **BRAM** *deterministic* from IR op geometry — each promoted lookup → a RAMB18
     (paired = two per RAMB18), large lookups → a whole RAMB36. **No regression.**
   - **DSP** = inference-rate × promoted-adder count.
3. **Predict the front** — for every candidate predicate, predict `(LUT, FF, BRAM,
   DSP, latency)` by pure arithmetic. **No Vivado.** Latency-in-cycles is *exact*
   (= pipeline depth from the IR).
4. **Select** — lexicographic objective (default `min_dsp → min_bram`: DSPs cost
   the most Fmax/latency, so a BRAM-backed fit is preferred) over candidates whose
   predicted usage fits the budget (asymmetric margins: LUT 10%, FF 15%, BRAM/DSP 5%).
5. **Confirm** (optional) — one full place+route of the winner; attaches measured
   resources + Fmax.

---

## 3. Empirical foundation (the findings that make it work)

Validated across ~552 synth / 406 route runs:

| resource | predictor | quality |
|---|---|---|
| **LUT** | affine in size-weighted `comb.cost` | R² ≈ 0.96, ±~3% |
| **BRAM** | deterministic from IR geometry (RAMB18/RAMB36) | exact |
| **DSP** | inference-rate × promoted adders | R² ≈ 0.999 |
| **latency (cycles)** | pipeline depth from the IR | **exact, pre-Vivado** |

Key enablers:
- **`comb.cost` is the right LUT feature** — it is size-weighted (a lookup's cost is
  exponential in `bw_in`), so promoting *wide* lookups saves far more LUT than
  promoting many small ones; counting ops misses this (R² 0.92 → 0.96 with cost).
- **Post-synth survives placement failure** → calibrate from synth-only anchors that
  needn't fit the part.
- **Slope is fabric-portable**, intercept is model-specific → a new UltraScale+ board
  reuses the slope; a new model needs ~2–3 synth anchors.

---

## 4. Validation result (single N=64 on xcau7p)

`fit_model` chose **`bram(8,8)`, zero DSP**:

| | predicted (route) | actual (confirm) | error |
|---|---:|---:|---|
| LUT | 33,670 (90%) | **34,724 (93%)** | +3.1% |
| FF | 27,008 | 33,379 | +23.6% (concavity, §6) |
| BRAM | 24.5 | **24.0** | ~exact |
| DSP | 0 | **0** | exact |
| timing | — | **WNS +0.050 → 253 MHz** | **fits + meets timing** |

### vs manual tuning (masters_results_5 Demo A, same model + part)

| | Manual (Demo A) | Auto (`fit_model`) |
|---|---|---|
| configs tried | 4, **hand-picked** (used the 122-run grid for intuition) | 77, **searched arithmetically** |
| Vivado runs | **4 full place+route** | **3 synth-only + 1 route** (only 1 full route) |
| outcome | 2 failed to place, 2 **timing_fail** (congested) | **fits + meets timing** |
| BRAM used | 53 tiles | **24 tiles** (found a config the human never tried) |
| human in loop | yes — pick, read reports, iterate | **none — one call** |

**Honest caveat:** Demo A targeted 3.0 ns, the auto run 4.0 ns — so claim
*efficiency, automation, and "fits without a sweep,"* **not** higher Fmax. Re-run
at 3.0 ns for a same-clock row if you want the direct comparison.

---

## 5. What to put in the thesis (and what not to)

**Defensible claims:**
- Resource usage of quantised-NN IR is **predictable pre-place-and-route** (LUT
  R²≈0.96, BRAM exact, DSP R²≈0.999), validated over ~500 runs.
- A target board can be fit **from 3 synth-only runs + 1 confirm**, vs the manual
  sweep/expert-guess baseline — **~4× fewer full place-and-route runs, no human,
  no prior characterisation**.
- The searcher found a **lower-BRAM, zero-DSP, timing-met** config the manual sweep
  missed.
- Everything is **bit-exact** to the trained checkpoint (the passes are backend hints).

**Do NOT claim:**
- Higher Fmax than manual (different clock targets — not apples-to-apples).
- A finished *multi-model* packer (single-model is done + validated; multi-model is
  designed/scaffolded — present as future work, see the two impl-notes docs).
- "Optimal" packing — it's a *feasible* fit under a lexicographic objective.

**Framing that lands:** "the IR passes expose the knobs; the searcher turns them
automatically — a synth-calibrated predictive cost model replaces the hours of
exhaustive Vivado sweeps with 3 synth runs and one confirm, validated to a few %."

---

## 6. Honest limitations (keep a slide on these — naming them first disarms examiners)

- **FF is the loosest** (+23.6% here): BRAM/clocked stages absorb pipeline registers
  into the primitives, making fabric FF *concave* in `reg_bits`; the affine model
  under-predicts mid-BRAM FF. Mitigated by a 15% FF margin; FF is rarely binding.
- **DSP inference rate is `bo`-dependent** — one calibration `bo` mis-predicts DSP
  (and hence the DSP-driven LUT saving) at other thresholds; this is the main source
  of the +3% LUT error. Fix: per-`bo` DSP calibration.
- **BRAM rule** must use the per-module RAMB18/RAMB36 capacity test (a wide lookup
  eats a whole RAMB36), not a flat 0.5/module.
- **Fmax is not modelled** — board/congestion-dependent; only *confirmed* at route.
- **Multi-model packing** not yet implemented (single-model only).

---

## 7. The 3-challenge / 3-novelty restructure

Proposed thesis spine — **mechanism → policy → automation**:

| # | Challenge | Novelty |
|---|---|---|
| **1** | da4ml emits one *combinational* graph; BRAM/DSP have **mandatory output registers**, so inserting them breaks pipeline timing alignment. | **Pipeline-stage-aware resource mapping** — clocked ops get isolated stages, downstream ops are pushed, bit-widths re-inferred, latencies recomputed; bit-exact, at predicted depth. |
| **2** | HGQ-LUT emits an **all-LUT** design; LUT is the scarce resource. Offload to BRAM/DSP must preserve bit-exactness *and* give the engineer control. | **4 composable IR passes + intra-stage BRAM pairing**, exposing the LUT↔BRAM↔DSP Pareto surface. |
| **3** | Choosing the right offload for a board normally needs **hours of exhaustive Vivado sweeps**. | **Synth-calibrated predictive auto-searcher** (`fit_model`): 3 synth runs → predict → select → 1 confirm. |

**Narrative arc:** *make clocked resources insertable → use them to trade LUT for
BRAM/DSP → automate the trade for any board.*

**Framing notes (important for the viva):**
- **Keep #1 and #2 distinct.** They couple (the staging exists *because of* the
  passes), so an examiner may call them one contribution. Defend by framing #1 as the
  **general, reusable mechanism** (it would support *any* clocked-resource insertion,
  not just these four passes) with its **own validation** — bit-exactness, the
  `stage-count == metadata.latency` invariant, and the key result that **latency cost
  scales with clocked stages introduced, not ops promoted**. Give #1 its own chapter
  with its own results so it doesn't collapse into #2.
- **Rename "stage pushing"** → "pipeline-stage-aware resource mapping" / "clocked-
  resource pipeline integration." The name should signal it's the technical core, not
  a tweak.
- **Sanity check for #1's independence:** be able to answer *"what breaks if you drop
  a BRAM in without the staging?"* with a concrete failure (wrong outputs / broken
  timing alignment) — then show your fix. If you can demo that failure, #1 is
  unambiguously its own novelty.
- **Scope #3 honestly** to the validated single-model fit; multi-model + per-core
  clock domains are designed (see `DA4ML_PACKER_IMPL_NOTES.md` and
  `DA4ML_PACKER_EXTENSIONS_TO_IMPL.md`), present as future work.

This gives technical depth in #1, empirical breadth in #2, and a working automated
system in #3 — a coherent, defensible MEng thesis.
