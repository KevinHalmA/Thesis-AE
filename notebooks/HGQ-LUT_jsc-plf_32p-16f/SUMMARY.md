# Fit summary — HGQ-LUT (GNN) — PLF JSC, 32 particles, 16 features

- **Part:** `xczu7ev-ffvc1156-2-e`  (230,400 LUT / 460,800 FF / 312 BRAM / 1728 DSP)
- **Published baseline (Table III):** 25,288 LUT, DSP 0
- **LUT budget (0.85×):** 21,495 LUT  (target −15%); FF/BRAM/DSP unconstrained.
- **Clock / latency cutoff:** 2.5 ns / 3.1 ns

- **A0 baseline (synth-calibrated LUT-only prediction):** 23,059 LUT (91% of Table III)

**FIT:** `bram(8, 7)_dsp-`
- predicted (route): **LUT 20,866** (83% of baseline → −17%), FF 15,427, BRAM 26, DSP 0, latency 18 cyc
- confirmed (route): LUT 22,942, FF 5,434, BRAM 119, DSP 0, Fmax 231.9 MHz
