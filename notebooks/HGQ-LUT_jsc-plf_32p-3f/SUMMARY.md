# Fit summary — HGQ-LUT (GNN) — PLF JSC, 32 particles, 3 features

- **Part:** `xcau7p-sbvc484-2-e`  (37,440 LUT / 74,880 FF / 108 BRAM / 216 DSP)
- **Published baseline (Table III):** 41,594 LUT, DSP 0
- **Target — physically fit on the part:** budget 37,440 LUT / 108 BRAM / 216 DSP (usable after margins: 33,696 LUT / 103 BRAM / 205 DSP).
  The 41,594-LUT baseline **overflows the part by 4,154 LUT (11%)** — it must offload BRAM/DSP to fit.
- **Clock / latency cutoff:** 3 ns / 2.5 ns

- **A0 baseline (synth-calibrated LUT-only prediction):** 39,246 LUT (94% of Table III)

**FIT:** `bram(8, 7)_dsp-`
- predicted (route): **LUT 31,963** (77% of baseline → −23%), FF 26,722, BRAM 58, DSP 0, latency 28 cyc  [LUT 85% / BRAM 54% / DSP 0% of part]
- confirmed (route): LUT 35,064, FF 37,682, BRAM 58, DSP 0, Fmax 323.3 MHz
