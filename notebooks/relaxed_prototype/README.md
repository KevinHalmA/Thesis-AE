# relaxed_prototype — relaxed-staging experiments (thesis §3.3)

Prototype reruns of selected experiments with **relaxed staging**
(`mark_*(relaxed=True)` + `to_pipeline(relaxed=True)` +
`fit_model(relaxed=True)`): combinational ops share clocked stages instead
of being evicted; only readers of a clocked op's un-registered address
input are still pushed out. Requires the da4ml fork at commit `b9b2db4`
or later. Every other result in the thesis and in `notebooks/` uses the
default (`relaxed=False`) staging.

| directory | backs |
|---|---|
| `worked_example_10_10__relaxed/` | thesis Table 3.2's relaxed worked-example row — the single widest lookup promoted under relaxed staging at the loose 5 ns target (reports + metadata; the default and baseline rows come from `../HGQ-LUT_jsc-plf_64p-16f/bram_grid_unpaired/sweep_metrics.csv`). |
| `HGQ-LUT_jsc-plf_64p-16f_bram_7_5/` | thesis Table 3.2 — default-vs-relaxed `bram(7,5)` (pair-packed, zero DSP) at the tight 2.5 ns target, plus the run reports (`bram_7_5__{default,relaxed}/`, pruned to reports + metadata). The notebook also carries the cocotb bit/latency-exactness gate. |
| `HGQ-LUT_jsc-plf_32p-3f/` | thesis §3.3 fitter-evidence table — N=32 F=3 `xcau7p` squeeze refit under relaxed staging (`fit.ipynb`, `SUMMARY.md`, `result.json`, `fit_front.csv`; `_fit_work/` pruned to reports). |
| `HGQ-Hybrid_tgc_2.28mrad/` | thesis §3.3 fitter-evidence table — TGC 2.28 mrad refit under relaxed staging (same layout). |
| `_fit_common.py` | relaxed copy of `../_fit_common.py`: `RELAXED = True` default in `run_fit`, work dirs resolve next to this file. |

Compare each against its committed default-staging counterpart under
`notebooks/`. The other model folders (`fit_xcau7p`, TGC 1.90/2.03, the
chapter-4 sweeps) were **not** rerun under relaxed staging — a few
examples suffice for the prototype claim; full re-validation is future
work (thesis §6.5).
