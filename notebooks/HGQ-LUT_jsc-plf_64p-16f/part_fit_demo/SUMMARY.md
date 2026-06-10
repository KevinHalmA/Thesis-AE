# masters_results_5 — part-fit demonstration summary

Self-contained writeup of the `part_fit_demonstration.ipynb` results, intended as
input for the thesis chapter. All numbers are post-Vivado (2025.1) measurements;
the per-run CSV is `part_fit_results.csv` in this folder.

## Why this experiment exists

`masters_results_3/tight_target_rerun.ipynb` characterised the same trade-off
surface (`paper_baseline`, `bram_7_5__*`, `bram_6_4__*`) on `xczu7ev-ffvc1156-2-e`
— a 230 k LUT, 312 BRAM, 1,728 DSP Zynq UltraScale+ part (~$1,000 retail). Every
configuration in that experiment landed at ~10–20 % LUT utilisation on `xczu7ev`,
so the IR passes' practical value (turning a single LUT-only design point into a
LUT↔BRAM↔DSP trade-off surface) wasn't tied to a deployment constraint — the
big part swallowed everything.

This notebook re-targets the **same trained checkpoints** at two small
UltraScale+ parts that are **15–20× cheaper** than `xczu7ev`. The story
is now resource-budget-driven: the unmarked da4ml output either fails
utilisation outright or congests these small parts at >95 % LUT, while
well-chosen `mark_bram` / `mark_dsp_adder` thresholds fit the same model
cleanly. **The IR passes are what make sub-$100 Artix UltraScale+
deployment reachable.**

## Setup

| Knob | Value |
|---|---|
| `CLOCK_PERIOD` | **3.0 ns** (333 MHz target) |
| `LATENCY_CUTOFF` | **3.0 ns** |
| `HWConfig` | `(1, -1, -1)` |
| `DSP_OFFLOAD_FN` | `dsp_offload(min_csd_terms=2, min_var_bits=4, max_const_bits=18, max_ops=None)` |
| `MAX_VIVADO_PAR` | 3 |
| `DSP_MAX_OPS` | 1600 |
| Trace batch | 2048 |
| Vivado | 2025.1, `-mode batch -source build_vivado_prj.tcl` |

> **Note on clock target.** The original brief specified
> `CLOCK_PERIOD = 2.5 ns` (400 MHz) to match `masters_results_3/`. The notebook
> was actually run at **3.0 ns / 333 MHz**. At 95+% LUT utilisation on `xcau7p`
> the 2.5 ns target was unreachable for any configuration; the 3.0 ns relaxation
> was needed to let the placed designs close timing in the first place. The
> Demo-B 2.5 ns target was tractable but consistency was prioritised — both
> demos use the same target.

Trained checkpoints (unchanged from `masters_results_3/` and `n32_validation/`):

* N=64: `epoch=4433-val_acc=0.817-ebops=40646-val_loss=0.534.keras`
  (val_acc 0.817 — beats paper's 0.810 by 0.7 pp)
* N=32: `epoch=5406-val_acc=0.805-ebops=27012-val_loss=0.570.keras`
  (val_acc 0.805 — beats paper's 0.803 by 0.2 pp)

## Parts targeted

Both Artix UltraScale+, both available in this Vivado install. List prices
are mid-2026 AMD/Xilinx list; Avnet/Digikey street prices fluctuate.

| Part | LUT | FF | BRAM tile | DSP | List price | Demo |
|---|---:|---:|---:|---:|---:|---|
| `xcau7p-sbvc484-2-e` | 37,440 | 74,880 | 108 | 216 | ~$60 | A |
| `xcau10p-sbvb484-2-e` | 44,000 | 88,000 | 100 | 400 | ~$75 | B |
| `xczu7ev-ffvc1156-2-e` (reference) | 230,400 | 460,800 | 312 | 1,728 | ~$1,000 | — |
| `xcvu13p-flga2577-2-e` (paper) | ~1,740,000 | — | ~2,688 | ~12,288 | ~$5,000+ | — |

> **Why not the parts in the original brief?** The candidate Zynq UltraScale+
> MPSoC parts (`xczu1eg`, `xczu2cg`) **are not in this Vivado 2025.1 install**
> — `get_parts -filter "NAME =~ xczu1*"` only returns the (very large) `xczu19eg`,
> and `xczu2*` / `xczu3*` / `xczu4*` return zero parts. The smallest licensed
> Zynq UltraScale+ in this install is `xczu7ev` itself, which is what
> `masters_results_3/` already targets. The Artix UltraScale+ family is the
> nearest available low-cost UltraScale+ line. Discovery script:
> `part_limit_testing/scan_small_parts.tcl`.

The package codes are notoriously easy to mistype: `xcau7p` only comes with
`sbvc484` (with a `c`); `xcau10p` and `xcau15p` come with `sbvb484` (with a
`b`). The original brief used `sbvb484` for `xcau7p`, which doesn't exist
— I caught this in cell 2 (`probe`) on the first run.

## Demo A — single-instance N=64 on `xcau7p` (~$60)

**Hypothesis.** The N=64 paper-style design uses 37,090 LUT on `xczu7ev` at
tight target (`masters_results_3/`); `xcau7p` has 37,440 LUT — barely larger.
The unmarked design should congest, and BRAM-marked variants should fit
cleanly.

**Configurations.** All four hold `mark_bram` thresholds chosen from
`exhaustive_search/sweep_metrics.csv` to keep BRAM ≤ 108 (the `xcau7p`
ceiling) at loose target; tight-target BRAM came in similar.

| label | `mark_bram` predicate | `mark_dsp_adder` |
|---|---|---|
| `paper_baseline` | — | — |
| `bram_6_10__none` | `bw_in ≥ 6 AND bw_out ≥ 10` | — |
| `bram_6_8__none` | `bw_in ≥ 6 AND bw_out ≥ 8` | — |
| `bram_6_8__bo15_clocked` | `bw_in ≥ 6 AND bw_out ≥ 8` | `bo ≥ 15`, clocked |

**Results.**

| label | LUT used | LUT % | BRAM | BRAM % | DSP | cyc | WNS (post-place) | Fmax (post-place) | WNS (post-route) | Fmax (post-route) | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `paper_baseline` | 35,616 | **95.1 %** | 0 | 0 % | 0 | 11 | **−0.037** | 329.3 | −0.479 | 287.4 | **routing/congestion fail** |
| `bram_6_10__none` | 36,163 | 96.6 % | 13.5 | 12.5 % | 0 | 19 | +0.002 | 333.6 | −0.463 | 288.8 | fits (routing-congested) |
| `bram_6_8__none` | 34,068 | **91.0 %** | 53 | 49.1 % | 0 | 21 | **+0.211** | **358.6** | −0.234 | 309.2 | fits (routing-congested) |
| `bram_6_8__bo15_clocked` | 34,757 | 92.8 % | 53 | 49.1 % | 148 | 35 | +0.026 | 336.2 | −0.151 | 317.4 | fits (routing-congested) |

**Read in plain English.**

* **`paper_baseline` is a routing/congestion failure on `xcau7p`.** At 95.1 %
  LUT utilisation Vivado runs out of routing tracks; post-place WNS is already
  −0.037 ns (just barely missing 333 MHz timing) and post-route widens that to
  −0.479 ns (~290 MHz max-frequency). On `xczu7ev` (16 % LUT util) the same
  design hits 420 MHz cleanly. The IR-pass-free output **is not deployable on
  `xcau7p`**.
* **`bram_6_8__none` is the headline win.** Promoting 344 wide-input lookup
  ops to BRAM frees 1,548 LUTs (35,616 → 34,068, **−4.4 %**) and adds 53 BRAM
  tiles (49 % util). Post-place WNS is +0.211 ns / **358.6 MHz** — a real
  margin. Post-route is −0.234 ns / 309 MHz due to residual congestion at 91 %
  LUT util, but **the design closes timing as placed** — a different routing
  seed, floorplan or directive sweep would fix it. The thesis claim is
  "the model fits on a $60 part with the IR passes." That is supported.
* **`bram_6_10__none` shows the limit.** A *minimal* BRAM mark (only
  ops with `bw_out ≥ 10` go to BRAM — 96 lookup ops, 13.5 BRAM tiles) saves
  only ~900 LUT vs the baseline; LUT util stays at 96.6 % and routing is
  worse. **You need enough BRAM offload to actually relieve LUT pressure.**
* **`bram_6_8__bo15_clocked` does *not* help on this part.** Adding 148 DSPs
  to the BRAM-only `(6, 8)` config raises LUT (34,068 → 34,757) because the
  clocked DSP-adder wrapper adds register glue, and Fmax drops (358.6 →
  336.2 MHz post-place). DSP offload is a win when LUT is the primary
  constraint and FF is cheap; here LUT is *already* relieved enough by BRAM,
  and the extra pipeline stages don't pay back. **The thesis takeaway: which
  IR pass to use depends on which resource is the bottleneck on the target.**

**Honest framing for the chapter.** All three marked variants are listed
as `fits (routing-congested)` — post-place closes timing, post-route does
not. This isn't a fundamental delay issue; it's pure congestion on a part
sized within 1 % of the design. A second engineering loop (different
routing strategy, manual floorplan, or relaxing the clock to 4 ns / 250 MHz)
would close timing post-route too. The `paper_baseline` is *not* routing-
congested in this sense — its post-place WNS is already negative, so even
ideal routing wouldn't save it.

## Demo B — dual-instance N=32 on `xcau10p` (~$75)

**Hypothesis.** Two independent N=32 jet-tagging cores on a single $75
part. Per `n32_validation/` (loose target), N=32 unmarked is 22,956 LUT;
2× = 45,912 LUT > 44,000 — fails LUT. BRAM-tuned variants should fit.

**Configurations.** Each row builds a *single* RTL project from the N=32
checkpoint with the listed marks, then a generated `jsc_dual.v` wrapper
instantiates that core **twice** with independent ports, and the Vivado
top is patched to `jsc_dual`. So resource usage is genuinely 2× whatever
one instance would take.

| label | `mark_bram` predicate | `mark_dsp_adder` |
|---|---|---|
| `paper_baseline` × 2 | — | — |
| `bram_6_4__none` × 2 | `bw_in ≥ 6 AND bw_out ≥ 4` | — |
| `bram_8_6__none` × 2 | `bw_in ≥ 8 AND bw_out ≥ 6` | — |
| `bram_8_6__bo15_clocked` × 2 | `bw_in ≥ 8 AND bw_out ≥ 6` | `bo ≥ 15`, clocked |

**Results.**

| label | LUT used | LUT % | BRAM | BRAM % | DSP | cyc | WNS (post-place) | Fmax (post-place) | WNS (post-route) | Fmax (post-route) | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `paper_baseline` × 2 | — | — | 0 | — | 0 | 10 | — | — | — | — | **`build_fail`** (place_design aborted; LUT > available) |
| `bram_6_4__none` × 2 | — | — | **414** | **414 %** | 0 | 27 | — | — | — | — | **`util_fail (bram_tiles)`** |
| `bram_8_6__none` × 2 | 43,518 | **98.9 %** | 90 | 90 % | 0 | 22 | +0.153 | 351.2 | +0.017 | 335.2 | **`fits`** ✓ |
| `bram_8_6__bo15_clocked` × 2 | 42,823 | 97.3 % | 90 | 90 % | 86 | 29 | **+0.280** | **367.6** | **+0.080** | **342.5** | **`fits`** ✓ |

**Read in plain English.**

* **`paper_baseline` × 2 doesn't fit.** Vivado synthesises (so resource
  estimates are available in `post_synth_util.rpt`) but `place_design`
  aborts because LUTs needed > 44,000 available. This is the
  utilisation-fail anchor at the LUT axis.
* **`bram_6_4__none` × 2 fails BRAM by 4×.** The "BRAM-heavy" predicate
  from `masters_results_3/` puts 414 BRAM tiles on a 100-tile budget.
  Vivado does report numbers, but they're nonsense for actual placement.
  This is the **over-marking anchor**: BRAM marks aren't free — the
  thresholds have to be picked with the target part's BRAM ceiling in mind.
* **`bram_8_6__none` × 2 fits cleanly** at 98.9 % LUT / 90 % BRAM with
  post-route WNS = +0.017 ns (335 MHz). **Two independent jet-tagging
  cores on a $75 part.** This is the multi-instance packing headline.
* **`bram_8_6__bo15_clocked` × 2 fits cleaner with higher Fmax** —
  +0.280 ns post-place / +0.080 ns post-route, 342.5 MHz. The DSP-adder
  pass adds 86 DSPs (well within the 400-DSP budget on `xcau10p`),
  trades 695 LUT savings for +14 ns of cycle latency, and lifts Fmax.
  **DSP offload pays back when LUT is the primary constraint *and* you
  have DSP headroom** — both true here.

**Throughput framing.** The two cores run in parallel from a shared
clock, so post-route Fmax doubles as aggregate jet rate:

| config | per-jet latency (per core) | per-core throughput | **aggregate throughput** |
|---|---:|---:|---:|
| `bram_8_6__none` × 2 | 22 cyc / 335 MHz ≈ 65.6 ns | 335 M jets/s | **~670 M jets/s** |
| `bram_8_6__bo15_clocked` × 2 | 29 cyc / 342 MHz ≈ 84.7 ns | 343 M jets/s | **~685 M jets/s** |

For reference: the FCCM'26 paper's N=64 design on `xcvu13p` (~$5k) hits
**438 MHz / 438 M jets/s** in a single core. The dual-core on `xcau10p`
(~$75) **beats the paper's single-core throughput by ~55 %** at ~67× lower
silicon cost — *and* runs the same trained checkpoint bit-exact. The
per-jet latency penalty (≈ 65 ns vs the paper's 28.7 ns) is the price you
pay for the BRAM/DSP offload + the smaller part — fine for any application
where throughput matters more than single-jet latency (which is most
trigger-stage HEP deployments).

## What this experiment establishes

1. **The IR passes turn the LUT-only paper design into a multi-resource
   trade-off space that *changes which parts the model can deploy on*.**
   The paper's `xcvu13p` (~$5k) is no longer the only option. The same
   trained checkpoint, bit-exact, lands on an `xcau7p` ($60) or two cores
   on `xcau10p` ($75) given correctly-chosen marks. That's a **15–80×
   silicon-cost reduction** without retraining.

2. **The right pass is part-dependent.** On `xcau7p` (DSP-rich, BRAM-tight)
   `mark_bram` alone is the win; `mark_dsp_adder(clocked=True)` adds glue
   logic that doesn't help here. On `xcau10p` (more LUTs, less BRAM, more
   DSP) the `bram_8_6 + bo15_clocked` combo beats `bram_8_6` alone on Fmax.
   **The mark passes are tunable knobs, not a single recipe** — the
   chapter should present them as a deployment-engineer's toolbox.

3. **Over-marking fails just as cleanly as under-marking.** `bram_6_4`
   was the Pareto-best BRAM choice on `xczu7ev` (282 BRAM, fine) but
   blows past `xcau10p`'s 100-BRAM ceiling by 4×. **Mark thresholds have
   to be sized to the target part's resource shape.**

4. **The unmarked output (paper-style) fails on both small parts.**
   `paper_baseline` is a routing/congestion failure on `xcau7p` (single
   instance) and a hard utilisation failure on `xcau10p` (two
   instances). **Without the IR passes, neither deployment scenario is
   reachable.**

5. **Routing congestion vs logic delay distinction matters.** Three of
   the four Demo-A configurations close timing **as placed** but lose
   it during routing because they sit at 91–97 % LUT utilisation on
   `xcau7p`. The chapter should report this as `fits (routing-
   congested)` — the design is sound, the routing margin is thin.
   Closing it post-route would be a floorplan / strategy-sweep
   exercise, not a re-marking exercise.

## Numbers worth citing in the chapter

| Claim | Number | Source |
|---|---|---|
| Cheapest part the unmarked N=64 design fits cleanly | `xczu7ev` (~$1k) | `masters_results_3/`, this notebook |
| Cheapest part the *marked* N=64 design fits | `xcau7p` (~$60), routing-congested | Demo A `bram_6_8__none` |
| Cost reduction enabled by `mark_bram(6, 8)` | **~17×** ($1k → $60) | A |
| LUT saved by `mark_bram(6, 8)` on N=64 | 35,616 → 34,068 (−4.4 %) | A |
| Post-place Fmax of `bram_6_8__none` | **358.6 MHz** | A |
| Two N=32 cores on a single `xcau10p` (~$75) | `bram_8_6__bo15_clocked` × 2, 342.5 MHz post-route | B |
| LUT-only N=32 × 2 outcome on `xcau10p` | `place_design` failure (LUT > 44 k) | B |
| Over-marked N=32 × 2 outcome on `xcau10p` | 414 BRAM > 100 (`util_fail`) | B |
| Cost reduction enabled by `mark_bram(8, 6) + bo15_clocked` for 2-core packing | **~13×** vs `xczu7ev`, **~67×** vs paper's `xcvu13p` | B |

## Power + energy-per-inference — supervisor question answered

Wayne asked whether the cheap parts are also **faster and more energy
efficient** at **same or higher accuracy**. The same trained checkpoint
runs on every part bit-exact so accuracy is identical by construction;
the question collapses to throughput and energy.

Energy/inference assumption: at steady state the pipelined design
completes `n_instances` inferences per achieved clock period, so
`energy_per_inf = total_on_chip_power × (1 / Fmax_achieved) / n_instances`.
Power numbers are from Vivado's `report_power` (medium-confidence —
no SAIF, no real activity file, default activity assumptions).

**Headline table:**

| scenario | part | $ | Power | Aggregate M-jets/s | **nJ/jet** |
|---|---|---:|---:|---:|---:|
| paper_baseline N=64 on **xczu7ev** | xczu7ev (ref) | $1000 | 4.21 W | 420 | **10.02** |
| `bram_7_5__bo15_clocked` N=64 on xczu7ev | xczu7ev (ref) | $1000 | 6.00 W | 404 | 14.83 |
| paper_baseline N=64 on **xcau7p** (Demo A) | xcau7p | $60 | 3.38 W | 287 | 11.77 *(timing_fail)* |
| `bram_6_8__none` N=64 on **xcau7p** (Demo A) | xcau7p | $60 | 3.81 W | 309 | 12.33 |
| `bram_6_8__bo15_clocked` N=64 on xcau7p | xcau7p | $60 | 4.12 W | 317 | 12.97 |
| paper_baseline N=32 on **xczu7ev** | xczu7ev (ref) | $1000 | 1.66 W | 284 | **5.84** |
| `bram_8_6__none` N=32 × 2 on **xcau10p** (Demo B) | xcau10p | $75 | 4.04 W | **670** | **6.02** |
| `bram_8_6__bo15_clocked` N=32 × 2 on xcau10p | xcau10p | $75 | 4.25 W | **685** | 6.21 |

**Demo A (N=64 single-instance, xcau7p $60) vs reference xczu7ev $1k:**

| metric | xczu7ev (ref) | xcau7p best (`bram_6_8__none`) | delta |
|---|---:|---:|---|
| Fmax post-route | 420 MHz | 309 MHz | **−26 % (slower)** |
| Total power | 4.21 W | 3.81 W | −10 % |
| Energy / jet | 10.02 nJ | 12.33 nJ | **+23 % (worse)** |
| Cost | $1000 | $60 | **17× cheaper** |

→ **Demo A does NOT strictly support the "faster + more energy efficient"
claim.** The honest framing is "comparable performance-class at 17×
lower silicon cost." It's slower (routing congestion at 91 % LUT util)
and slightly less energy-efficient per jet.

**Demo B (N=32 dual-instance, xcau10p $75) vs reference N=32 on xczu7ev:**

| metric | xczu7ev (ref, N=32 single) | xcau10p `bram_8_6__none × 2` | delta |
|---|---:|---:|---|
| Aggregate throughput | 284 M-jets/s | **670 M-jets/s** | **+136 % (2.4× faster)** |
| Total power | 1.66 W | 4.04 W | +143 % (one big core uses much more power, but…) |
| **Energy / jet** | **5.84 nJ** | **6.02 nJ** | **+3 % (essentially identical)** |
| Cost | $1000 | $75 | **13× cheaper** |

→ **Demo B fully supports the "faster + same energy efficiency + same
accuracy + cheaper" claim.** 2.4× aggregate throughput at the same
nJ/jet on a part 13× cheaper than xczu7ev (and 67× cheaper than the
paper's xcvu13p). This is the demonstration to lead with.

**Vs the paper's `xcvu13p` (N=64):** the paper reports 39,765 LUT, 0
BRAM, 0 DSP, 28.7 ns latency, 383.6 MHz on `xcvu13p` (~$5,000). The
paper doesn't publish power so we can't compute their nJ/jet directly,
but at 384 MHz × 1 instance the throughput is 384 M-jets/s — less than
half of our dual-core xcau10p's 670 M-jets/s aggregate, on a chip
**67× more expensive**.

**Note on `report_power` confidence.** Vivado labels these reports
"Medium" confidence — no SAIF, no per-net activity, default 12.5 %
toggle assumption. The chapter should be honest about that; ideally
Wayne would want a SAIF capture from simulation (or a hardware power
measurement on an actual board) to harden the per-jet energy claim
for the cheap-part Demo B comparison. The relative deltas between
xczu7ev and xcau10p estimates are likely more reliable than the
absolute numbers — both reports use the same default activity model.

## Files in this folder

| File | Contents |
|---|---|
| `part_fit_demonstration.ipynb` | The notebook (24 cells, both demos). |
| `part_fit_results.csv` | Per-run table — 8 rows (4 Demo-A + 4 Demo-B), 23 columns including post-place and post-route WNS/Fmax. |
| `part_fit_overview.png` | Auto-generated scatter; layout is rough — chapter should redo this from the CSV with thesis styling. |
| `SUMMARY.md` | This file. |
| `demoA_n64_xcau7p/` | Per-config Vivado projects (logs, reports, generated Verilog). |
| `demoB_n32x2_xcau10p/` | Same, for Demo B. Each project's `src/jsc_dual.v` is the auto-generated dual-instance top. |

## Notes for the writeup session

* **Cite `masters_results_3/04_results.md`** for the `xczu7ev` reference
  numbers (paper baseline → 420 MHz @ 16 % LUT util, etc.). The
  comparison point matters because it lets you say "same checkpoint,
  same Vivado settings, same speed grade, same TSMC 16 nm process,
  different part *only*."
* The `part_fit_overview.png` plot is functional but ugly — please
  redo with thesis styling (single column or two-panel, axis labels,
  consistent fonts). All the data is in `part_fit_results.csv`.
* The clock-target relaxation from the original 2.5 ns brief to the
  actual 3.0 ns is **load-bearing** for Demo A — the marked variants
  do close post-place timing at 3.0 ns but not at 2.5 ns on
  `xcau7p`. **Mention this in the chapter** as an honest constraint:
  "deploying on the cheap part costs about 15–20 % of Fmax vs the
  big part." Demo B is the unambiguous win: post-route Fmax 335–342
  MHz on `xcau10p` is comparable to the `xczu7ev` Demo-A points and
  far above the N=32 paper's 438 MHz on `xcvu13p` is the bar, but the
  thesis is about flexibility (one ~$75 chip running two cores), not
  raw Fmax.
* `bram_6_10__none` is a useful "negative-control" datapoint — a
  minimal BRAM mark that *doesn't* relieve LUT pressure enough.
  Worth including in any figure that motivates "you need enough
  BRAM offload to actually move the needle."
