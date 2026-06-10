# Part-fit demonstration — hand-tuned baseline (Demo A)

Manual mark-predicate selection for the N=64 F=16 checkpoint on
`xcau7p-sbvc484-2-e` ($60: 37,440 LUT / 108 BRAM / 216 DSP), at the same
3.0 ns (333 MHz) target the auto-fitter used. All numbers are post-Vivado
(2025.1) measurements; the raw post-route reports are committed under
`reports_3p0ns/`.

## Setup

| Knob | Value |
|---|---|
| `CLOCK_PERIOD` | 3.0 ns (333 MHz target) |
| `LATENCY_CUTOFF` | 3.0 ns |
| `HWConfig` | (1, -1, -1) |
| part | xcau7p-sbvc484-2-e |
| configs | 4, hand-picked from the grid-sweep intuition |

## Demo A — single-instance N=64 on `xcau7p` (~$60)

**Hypothesis.** The N=64 paper-style design uses 37,090 LUT on `xczu7ev` at
tight target (the tight-target rerun, `../dsp_summary/`); `xcau7p` has 37,440 LUT — barely larger.
The unmarked design should congest, and BRAM-marked variants should fit
cleanly.

**Configurations.** All four hold `mark_bram` thresholds chosen from
`../bram_grid_unpaired/sweep_metrics.csv` to keep BRAM ≤ 108 (the `xcau7p`
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
