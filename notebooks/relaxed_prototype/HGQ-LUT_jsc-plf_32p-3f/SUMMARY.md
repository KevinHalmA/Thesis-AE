# Fit summary — HGQ-LUT (GNN) — PLF JSC, 32 particles, 3 features

- **Part:** `xcau7p-sbvc484-2-e`  (37,440 LUT / 74,880 FF / 108 BRAM / 216 DSP)
- **Published baseline (Table III):** 41,594 LUT, DSP 0
- **Target — physically fit on the part:** budget 37,440 LUT / 108 BRAM / 216 DSP (usable after margins: 33,696 LUT / 103 BRAM / 205 DSP).
  The 41,594-LUT baseline **overflows the part by 4,154 LUT (11%)** — it must offload BRAM/DSP to fit.
- **Clock / latency cutoff:** 3 ns / 2.5 ns

- **A0 baseline (synth-calibrated LUT-only prediction):** 39,246 LUT (94% of Table III)

**FIT:** `bram(8, 8)_dsp-_rlx`
- predicted (route): **LUT 33,362** (80% of baseline → −20%), FF 18,357, BRAM 38, DSP 0, latency 19 cyc  [LUT 89% / BRAM 36% / DSP 0% of part]
- confirmed (route): LUT 35,227, FF 24,371, BRAM 38, DSP 0, Fmax 295.4 MHz
