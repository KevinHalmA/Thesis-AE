# test_notebooks/relaxed_bram_7_5_tight — relaxed staging on the headline predicate

Single-config default-vs-relaxed comparison of `mark_bram(7,5)`
(pair-packed, zero DSP) at `T = 2.5` ns, `latency_cutoff = 2` ns,
on `xczu7ev-ffvc1156-2-e`. Relaxed staging lets combinational ops share clocked
stages (`mark_bram(relaxed=True)` + `to_pipeline(relaxed=True)`); only
readers of a clocked op's un-registered address input are still evicted.

Note: the thesis tight-target rerun used `latency_cutoff = 2.0` at the same
clock; rerun with that value for a row directly comparable to `tab:tight-target`.

| metric | default | relaxed | delta |
|---|---|---|---|
| pipeline depth (cycles) | 30 | 22 | -8 |
| stages shared (BRAM+comb) | 1 | 11 | — |
| LUT total | 33094 | 32162 | -932 |
| LUT as memory | 2993 | 2100 | -893 |
| FF | 45236 | 27836 | -17400 |
| BRAM tile | 99.5 | 99.5 | +0.0 |
| DSP | 0 | 0 | — |
| WNS post-place (ns) | -0.091 | -0.101 | — |
| WNS post-route (ns) | -0.155 | -0.258 | — |
| Fmax post-route (MHz) | 376.6 | 362.6 | -14.1 |
| end-to-end latency (ns) | 79.6 | 60.7 | -19.0 |
| status | timing_fail | timing_fail | |

Both variants are bit-exact to the unmarked baseline at the SW-IR level
(256 validation samples) and bit-exact RTL-vs-IR under Verilator.
