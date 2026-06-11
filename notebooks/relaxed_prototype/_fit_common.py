"""Shared helpers for the per-model LUT-fitting notebooks.

Each notebook under ``notebooks/<model>/`` takes one **HGQ-\\*** model from the
paper's Table III and uses ``da4ml.pack.fit_model`` to fit it into **~15% fewer
LUTs** than its published baseline, by offloading lookups->BRAM and adders->DSP
(all bit-exact backend hints, no quantisation change).

Method, fixed across every model so the results are comparable:

* **Part** = ``xczu7ev-ffvc1156-2-e`` — the Zynq US+ reference the Table III
  numbers were measured on (apples-to-apples; it also has plenty of unused
  BRAM/DSP, since every HGQ-\\* row in the table reports **DSP = 0**).
* **Budget** = ``lut = 0.85 x (Table III LUT)`` with **zero LUT margin**, so
  "fits" means *predicted post-route LUT <= 0.85 x baseline* exactly. FF/BRAM/DSP
  budgets are the full part (we are only constraining LUTs).
  *Exception:* a model may instead set ``fit_part_budget`` to fit the **exact
  capacity of a real, smaller part** (with default safety margins) — a genuine
  multi-resource squeeze where the baseline overflows the chip. ``jsc-plf_32p-3f``
  does this on ``xcau7p-sbvc484-2-e`` (37,440 LUT / 108 BRAM / 216 DSP).
* **Objective** = ``(min_dsp, min_bram)`` — among configs that hit the LUT
  target, prefer the one using the fewest DSPs, then the fewest BRAMs.
* ``confirm=True`` routes the winner once to validate predicted-vs-actual.

``fit_model`` itself needs only the traced ``comb`` (no X data); X is used purely
to ``trace_minmax`` the quantiser ranges before tracing, so the IR matches the
trained model.
"""

from __future__ import annotations

import os

os.environ.setdefault('KERAS_BACKEND', 'jax')
os.environ.setdefault('XLA_PYTHON_CLIENT_PREALLOCATE', 'false')
os.environ.setdefault('XLA_PYTHON_CLIENT_MEM_FRACTION', '0.4')

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixed environment
# ---------------------------------------------------------------------------
REPO = Path('/home/kevin/Dev/Imperial/HGQ-LUT-AE')
# RELAXED-STAGING COPY: notebooks under test_notebooks/ rerun the committed
# experiments with mark_*(relaxed=True). Work dirs resolve next to THIS file,
# so the committed notebooks/ results are never touched.
NB_ROOT = Path(__file__).resolve().parent
RELAXED = True
PLF_DATA = Path('/home/kevin/Dev/Imperial/HGQ2-examples/jsc150/data')   # 150c-{train,test}.h5
TGC_DATA = REPO / 'dataset' / 'tgc_dataset.h5'
VIVADO_SETTINGS = '/tools/Xilinx/2025.1/Vivado/settings64.sh'

# Reference part (Table III was measured here) + its capacity.
PART_NAME = 'xczu7ev-ffvc1156-2-e'
PART_CAP = dict(lut=230400, ff=460800, bram=312, dsp=1728)

LUT_FRACTION = 0.85   # fit into ~15% fewer LUTs than the published baseline


@dataclass
class ModelCfg:
    key: str               # notebook folder name
    title: str             # Table III identity
    family: str            # 'jsc_plf' | 'tgc'
    checkpoint: Path       # raw trained checkpoint
    traced_cache: Path     # where the trace_minmax'd model is cached
    baseline_lut: int      # Table III LUT (the published HGQ-* baseline)
    clock_period: float    # ns — the Vivado clock constraint (matches the published build)
    latency_cutoff: float  # da4ml pipeline-DEPTH budget in LUT-delay levels (NOT ns); see README
    particles: int = 0     # jsc_plf only
    features: int = 0      # jsc_plf only (3 -> pt/eta/phi)
    # Target board. Default mode constrains LUT to 0.85x baseline on the Table III
    # reference part (zero margin), other resources unconstrained. Set
    # ``fit_part_budget`` to instead fit the *exact capacity of a real part* (with
    # da4ml's default safety margins) — a genuine multi-resource squeeze.
    part_name: str = PART_NAME
    part_cap: dict = field(default_factory=lambda: dict(PART_CAP))
    fit_part_budget: dict | None = None
    part_family: str = ''  # human label for the target part, e.g. 'Artix UltraScale+'
    route_baseline: bool = False  # also place+route the unmarked pure-LUT design and compare

    @property
    def part_constrained(self) -> bool:
        return self.fit_part_budget is not None

    @property
    def lut_budget(self) -> int:
        if self.fit_part_budget is not None:
            return int(self.fit_part_budget['lut'])
        return round(self.baseline_lut * LUT_FRACTION)

    @property
    def nb_dir(self) -> Path:
        return NB_ROOT / self.key


_M = REPO / 'models'
MODELS: dict[str, ModelCfg] = {
    'HGQ-LUT_jsc-plf_32p-16f': ModelCfg(
        key='HGQ-LUT_jsc-plf_32p-16f',
        title='HGQ-LUT (GNN) — PLF JSC, 32 particles, 16 features',
        family='jsc_plf',
        checkpoint=_M / 'jsc_plf/32-16/epoch=5406-val_acc=0.805-ebops=27012-val_loss=0.570.keras',
        traced_cache=_M / 'jsc_plf/32-16/model_traced_n32_f16.keras',
        baseline_lut=25288, clock_period=2.5, latency_cutoff=3.1,
        particles=32, features=16,
    ),
    'HGQ-LUT_jsc-plf_32p-3f': ModelCfg(
        key='HGQ-LUT_jsc-plf_32p-3f',
        title='HGQ-LUT (GNN) — PLF JSC, 32 particles, 3 features',
        family='jsc_plf',
        checkpoint=_M / 'jsc_plf/32-3/epoch=3410-val_acc=0.787-ebops=38725-val_loss=0.610.keras',
        traced_cache=_M / 'jsc_plf/32-3/model_traced_n32_f3.keras',
        baseline_lut=41594, clock_period=3, latency_cutoff=2.5,
        particles=32, features=3,
        # Fit the EXACT Artix US+ part: the 41,594-LUT baseline overflows its
        # 37,440 LUT, so the model must offload to BRAM/DSP to physically fit —
        # and BRAM (108)/DSP (216) are now real caps, not the reference board's.
        part_name='xcau7p-sbvc484-2-e',
        part_cap=dict(lut=37440, ff=74880, bram=108, dsp=216),
        fit_part_budget=dict(lut=37440, ff=74880, bram=108, dsp=216),
        part_family='Artix UltraScale+',
    ),
    'HGQ-Hybrid_tgc_1.90mrad': ModelCfg(
        key='HGQ-Hybrid_tgc_1.90mrad',
        title='HGQ-Hybrid — Muon tracking, 1.90 mrad',
        family='tgc',
        checkpoint=_M / 'tgc/epoch=15996-val_res=1.901-ebops=37139-mse=3.652.keras',
        traced_cache=_M / 'tgc/traced_1.90mrad.keras',
        baseline_lut=30612, clock_period=6.25, latency_cutoff=8,
    ),
    'HGQ-Hybrid_tgc_2.03mrad': ModelCfg(
        key='HGQ-Hybrid_tgc_2.03mrad',
        title='HGQ-Hybrid — Muon tracking, 2.03 mrad',
        family='tgc',
        checkpoint=_M / 'tgc/epoch=38501-val_res=2.020-ebops=21611-mse=4.111.keras',
        traced_cache=_M / 'tgc/traced_2.03mrad.keras',
        baseline_lut=19627, clock_period=6.25, latency_cutoff=8,
    ),
    'HGQ-Hybrid_tgc_2.03mrad_z010': ModelCfg(
        key='HGQ-Hybrid_tgc_2.03mrad_z010',
        title='HGQ-Hybrid — Muon tracking, 2.03 mrad (Zynq-7010 squeeze)',
        family='tgc',
        checkpoint=_M / 'tgc/epoch=38501-val_res=2.020-ebops=21611-mse=4.111.keras',
        traced_cache=_M / 'tgc/traced_2.03mrad.keras',   # reuse the same trace
        baseline_lut=19627, clock_period=6.25, latency_cutoff=8,
        # 7-series (NOT UltraScale+) — proves the flow generalises beyond US+.
        # NB the cost model's fixed synth->route LUT factor (0.977) and BRAM/DSP
        # geometry were validated on US+; the per-part a_lut/b_lut/kappa/dsp-rate
        # re-calibrate here, and confirm=True routes the winner to validate.
        part_name='xc7z010clg400-3',
        part_cap=dict(lut=17600, ff=35200, bram=60, dsp=80),
        fit_part_budget=dict(lut=17600, ff=35200, bram=60, dsp=80),
        part_family='Zynq-7000 (7-series, not UltraScale+)',
    ),
    'HGQ-Hybrid_tgc_2.03mrad_a35t': ModelCfg(
        key='HGQ-Hybrid_tgc_2.03mrad_a35t',
        title='HGQ-Hybrid — Muon tracking, 2.03 mrad (Artix-7 35T)',
        family='tgc',
        checkpoint=_M / 'tgc/epoch=38501-val_res=2.020-ebops=21611-mse=4.111.keras',
        traced_cache=_M / 'tgc/traced_2.03mrad.keras',   # reuse the same trace
        baseline_lut=19627, clock_period=7, latency_cutoff=6,
        # Free-tier Artix-7. The ~18.9k-LUT pure-LUT design is ~91% of the 20,800
        # LUTs -> P&R congestion / timing trouble. route_baseline builds it as-is,
        # then the autofitter offloads to BRAM/DSP and we compare the two routes.
        part_name='xc7a35tcsg324-3',   # -3 = fastest Artix-7 speed grade
        part_cap=dict(lut=20800, ff=41600, bram=50, dsp=90),
        fit_part_budget=dict(lut=20800, ff=41600, bram=50, dsp=90),
        part_family='Artix-7 (7-series, free WebPACK, -3 fastest grade)',
        route_baseline=True,
    ),
    'HGQ-Hybrid_tgc_2.28mrad': ModelCfg(
        key='HGQ-Hybrid_tgc_2.28mrad',
        title='HGQ-Hybrid — Muon tracking, 2.28 mrad',
        family='tgc',
        checkpoint=_M / 'tgc/epoch=55339-val_res=2.269-ebops=14958-mse=5.191.keras',
        traced_cache=_M / 'tgc/traced_2.28mrad.keras',
        baseline_lut=14549, clock_period=6.25, latency_cutoff=8,
    ),
}


# ---------------------------------------------------------------------------
# Trace (load checkpoint -> set quantiser ranges -> da4ml CombLogic)
# ---------------------------------------------------------------------------
def _register_layers(family: str):
    """Import the hgq layers so load_model can find QDense/QConv1D/..."""
    import hgq          # noqa: F401
    import hgq.layers   # noqa: F401


def _load_family_module(family: str, modname: str):
    """Load ``src/<family>/<modname>.py`` under a unique name.

    Both families ship a ``data.py`` (and a ``model.py``); a plain
    ``from data import ...`` collides in ``sys.modules`` if more than one family
    is used in the same process. Loading by file path under a namespaced key
    avoids that entirely.
    """
    import importlib.util
    uniq = f'_fitsrc_{family}_{modname}'
    if uniq in sys.modules:
        return sys.modules[uniq]
    path = REPO / 'src' / family / f'{modname}.py'
    spec = importlib.util.spec_from_file_location(uniq, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[uniq] = mod
    spec.loader.exec_module(mod)
    return mod


def _trace_minmax_jsc_plf(model, cfg: ModelCfg):
    from hgq.utils import trace_minmax
    data = _load_family_module('jsc_plf', 'data')
    (Xtr, _), (Xv, _), _ = data.get_data(PLF_DATA, cfg.particles, cfg.features == 3)
    trace_minmax(model, Xtr, batch_size=2048, reset=True, verbose=True)
    trace_minmax(model, Xv, batch_size=2048, reset=False, verbose=True)


def _trace_minmax_tgc(model, cfg: ModelCfg):
    from hgq.utils import trace_minmax
    data = _load_family_module('tgc', 'data')
    (Xtr, _), (Xv, _), _, _ = data.get_data_and_mask(str(TGC_DATA))
    trace_minmax(model, Xtr, batch_size=8192, reset=True, verbose=True)
    trace_minmax(model, Xv, batch_size=8192, reset=False, verbose=True)


def load_traced_comb(cfg: ModelCfg, verbose: bool = True):
    """Return the traced base ``CombLogic`` for ``cfg``.

    Uses the cached trace_minmax'd checkpoint if present; otherwise loads the raw
    checkpoint, traces min/max over train+val (the published flow), and caches it.
    """
    import keras
    from da4ml.converter import trace_model
    from da4ml.trace import HWConfig, comb_trace

    _register_layers(cfg.family)

    if cfg.traced_cache.exists():
        if verbose:
            print(f'Using cached trace: {cfg.traced_cache.name}')
        model = keras.models.load_model(cfg.traced_cache, compile=False)
    else:
        if verbose:
            print(f'No cache — tracing min/max from {cfg.checkpoint.name} (first run only)...')
        model = keras.models.load_model(cfg.checkpoint, compile=False)
        if cfg.family == 'jsc_plf':
            _trace_minmax_jsc_plf(model, cfg)
        elif cfg.family == 'tgc':
            _trace_minmax_tgc(model, cfg)
        else:
            raise ValueError(cfg.family)
        cfg.traced_cache.parent.mkdir(parents=True, exist_ok=True)
        model.save(cfg.traced_cache)

    inp, out = trace_model(model, hwconf=HWConfig(1, -1, -1), solver_options={'hard_dc': 2}, verbose=False)
    comb = comb_trace(inp, out)
    if verbose:
        n8 = sum(1 for op in comb.ops if op.opcode == 8)
        n7 = sum(1 for op in comb.ops if op.opcode == 7)
        print(f'Traced: cost={comb.cost:.0f}  ops={len(comb.ops)}  lookups(op8)={n8}  vmul(op7)={n7}')
        assert max(op.latency for op in comb.ops) < 50, 'latency cutoff leaked into trace (use HWConfig(1,-1,-1))'
    return comb


# ---------------------------------------------------------------------------
# Budget + fit
# ---------------------------------------------------------------------------
def budget_for(cfg: ModelCfg):
    """Two modes:

    * ``fit_part_budget`` set -> fit the **exact part capacity** with da4ml's
      default safety margins (a real, multi-resource board fit).
    * else -> constrain **LUT to 0.85x baseline (zero margin)** on the reference
      part; FF/BRAM/DSP left at full part capacity.
    """
    from da4ml.pack import ResourceBudget
    if cfg.fit_part_budget is not None:
        return ResourceBudget(**cfg.fit_part_budget)
    return ResourceBudget(
        lut=cfg.lut_budget, ff=cfg.part_cap['ff'], bram=cfg.part_cap['bram'], dsp=cfg.part_cap['dsp'],
        margins=dict(lut=0.0, ff=0.0, bram=0.0, dsp=0.0),
    )


def run_fit(cfg: ModelCfg, comb, *, confirm: bool = True, max_parallel: int = 3, verbose: bool = True,
            relaxed: bool = RELAXED):
    """Calibrate (3 synth-only anchors) + pick the predicate that fits + confirm."""
    from da4ml.pack import fit_model
    return fit_model(
        comb,
        budget=budget_for(cfg),
        part_name=cfg.part_name,
        vivado_settings=VIVADO_SETTINGS,
        clock_period=cfg.clock_period,
        latency_cutoff=cfg.latency_cutoff,
        objective=('min_dsp', 'min_bram'),
        confirm=confirm,
        work_dir=str(cfg.nb_dir / '_fit_work'),
        model_name='fit',
        max_parallel=max_parallel,
        verbose=verbose,
        relaxed=relaxed,
    )


def run_compare(cfg: ModelCfg, comb, *, confirm: bool = True, verbose: bool = True):
    """Run the **pure-LUT baseline route and the autofit concurrently** (each
    blocks on its own Vivado subprocesses in a separate thread; they write to
    different work dirs, so they overlap instead of running in series).

    Peak Vivado processes ≈ baseline (1) + fit anchors (2) = 3, matching the
    house MAX_VIVADO_PAR cap. Wall time ≈ max(baseline route, full fit) instead
    of their sum. Returns ``(base_res, fit_result)``.
    """
    from concurrent.futures import ThreadPoolExecutor
    if verbose:
        print('Launching pure-LUT baseline route + autofit concurrently '
              '(interleaved logs below)...\n')
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_base = ex.submit(route_pure_lut, cfg, comb, verbose=verbose)
        f_fit = ex.submit(run_fit, cfg, comb, confirm=confirm, max_parallel=2, verbose=verbose)
        base = f_base.result()
        result = f_fit.result()
    return base, result


# ---------------------------------------------------------------------------
# Pure-LUT baseline route (the "no fitting" comparison point)
# ---------------------------------------------------------------------------
def _route_fail_reason(log_path: Path) -> str:
    """First Vivado ERROR / over-utilization line from a failed baseline build."""
    import re
    try:
        txt = Path(log_path).read_text(errors='ignore')
    except OSError:
        return 'route failed (no log)'
    for pat in (r'ERROR:[^\n]*(?:overutilized|requires more|Placer|Router|[Uu]nrouted|congest)[^\n]*',
                r'(?:requires more \w+ cells than|overutilized|Placement Failed|Routing results? .*unrouted)[^\n]*',
                r'ERROR:[^\n]*'):
        m = re.search(pat, txt, re.IGNORECASE)
        if m:
            return ' '.join(m.group(0).split())[:200]
    return 'route did not complete (see baseline_build.log)'


def route_pure_lut(cfg: ModelCfg, comb, *, work_dir: str | None = None, verbose: bool = True) -> dict:
    """Place+route the **unmarked pure-LUT** design on ``cfg.part_name`` — the
    "no offload" baseline. Returns measured route ``lut/ff/bram/dsp`` + ``wns`` +
    ``fmax`` (MHz), a ``routed`` flag (``False`` if Vivado could not place/route
    it, e.g. LUT/congestion overflow), and a short ``reason`` when it fails.

    This is the comparison counterpart to :func:`run_fit`: same part/clock, but no
    BRAM/DSP marks. A near-full all-LUT design may miss timing (negative WNS) or
    fail P&R outright — both are the point.
    """
    import subprocess
    import time

    from da4ml.pack._vivado import _parse_wns, _vivado_cmd, _write_project, parse_util

    work = Path(work_dir) if work_dir else (cfg.nb_dir / '_baseline_route')
    prj = _write_project(comb, work / 'baseline', 'baseline', part_name=cfg.part_name,
                         clock_period=cfg.clock_period, latency_cutoff=cfg.latency_cutoff,
                         clock_uncertainty=0.0)
    tcl = prj / 'build_vivado_prj.tcl'
    log = prj / 'baseline_build.log'
    t0 = time.time()
    with open(log, 'w') as lf:
        subprocess.run(['bash', '-lc', _vivado_cmd(tcl, VIVADO_SETTINGS)],
                       cwd=str(prj), stdout=lf, stderr=subprocess.STDOUT, text=True)
    rep = prj / 'output_baseline' / 'reports'
    res = parse_util(rep / 'baseline_post_route_util.rpt', post_route=True)
    wns = _parse_wns(rep / 'baseline_post_route_timing.rpt')
    res['wns'] = wns
    res['fmax'] = 1000.0 / (cfg.clock_period - wns) if wns == wns and (cfg.clock_period - wns) > 0 else float('nan')
    res['routed'] = res.get('lut') == res.get('lut')          # not NaN -> a post-route report exists
    res['meets_timing'] = bool(res['routed'] and wns == wns and wns >= 0)
    res['reason'] = '' if res['routed'] else _route_fail_reason(log)
    res['seconds'] = time.time() - t0
    if verbose:
        if res['routed']:
            cap = cfg.part_cap
            print(f"[baseline] routed: LUT {res['lut']:.0f} ({res['lut'] / cap['lut'] * 100:.0f}%)  "
                  f"FF {res['ff']:.0f}  BRAM {res['bram']:.1f}  DSP {res['dsp']:.0f}  "
                  f"WNS {wns:+.3f} ns  Fmax {res['fmax']:.1f} MHz  "
                  f"{'TIMING MET' if res['meets_timing'] else 'TIMING FAILED'}  t={res['seconds']:.0f}s")
        else:
            print(f"[baseline] DID NOT ROUTE — {res['reason']}  t={res['seconds']:.0f}s")
    return res


def write_compare(cfg: ModelCfg, base_res: dict, result, comb, out_dir: Path | None = None):
    """Compare the pure-LUT baseline route against the autofitted route. Writes
    compare.csv, result.json, SUMMARY.md (and fit_front.csv via write_outputs)."""
    import pandas as pd

    out_dir = Path(out_dir) if out_dir is not None else cfg.nb_dir
    write_outputs(cfg, result, comb, out_dir)             # fit_front.csv + (overwritten below) SUMMARY/json
    cap = cfg.part_cap
    fit = result.confirm or (result.predicted.as_dict() if result.predicted else None)

    def row(name, r, routed, meets, fmax):
        if r is None:
            return dict(design=name, routed=routed, lut=float('nan'), lut_pct=float('nan'),
                        ff=float('nan'), bram=float('nan'), dsp=float('nan'), fmax=float('nan'), meets_timing=meets)
        return dict(design=name, routed=routed,
                    lut=r['lut'], lut_pct=100 * r['lut'] / cap['lut'], ff=r['ff'],
                    bram=r['bram'], dsp=r['dsp'], fmax=fmax, meets_timing=meets)

    rows = [row('pure-LUT (no fitting)', base_res if base_res.get('routed') else None,
                base_res.get('routed', False), base_res.get('meets_timing', False), base_res.get('fmax', float('nan')))]
    if fit is not None:
        fit_meets = (fit.get('wns', float('nan')) >= 0) if 'wns' in fit else None
        rows.append(row(f'autofit ({result.config.name})' if result.config else 'autofit',
                        fit, True, fit_meets, fit.get('fmax', float('nan'))))
    cmp_df = pd.DataFrame(rows)
    cmp_df.to_csv(out_dir / 'compare.csv', index=False)

    # SUMMARY.md (comparison flavour)
    L = [f'# Pure-LUT vs autofit — {cfg.title}', '',
         f'- **Part:** `{cfg.part_name}` ({cap["lut"]:,} LUT / {cap["bram"]} BRAM / {cap["dsp"]} DSP), '
         f'{cfg.part_family}', f'- **Clock:** {cfg.clock_period} ns ({1000 / cfg.clock_period:.0f} MHz target)', '']
    b = base_res
    if b.get('routed'):
        L.append(f'**Pure-LUT (no fitting):** LUT {b["lut"]:,.0f} ({b["lut"] / cap["lut"] * 100:.0f}% of part), '
                 f'BRAM {b["bram"]:.0f}, DSP {b["dsp"]:.0f}, WNS {b["wns"]:+.3f} ns, Fmax {b["fmax"]:.1f} MHz — '
                 f'**{"meets timing" if b["meets_timing"] else "MISSES TIMING"}**.')
    else:
        L.append(f'**Pure-LUT (no fitting): DID NOT ROUTE** — {b.get("reason", "?")}')
    if result.feasible and fit is not None:
        f = fit
        fm = f.get('fmax', float('nan'))
        L.append(f'**Autofit (`{result.config.name}`):** LUT {f["lut"]:,.0f} ({f["lut"] / cap["lut"] * 100:.0f}%), '
                 f'BRAM {f["bram"]:.0f}, DSP {f["dsp"]:.0f}' + (f', Fmax {fm:.1f} MHz' if fm == fm else '') +
                 ' — fits the part with BRAM/DSP headroom.')
        if b.get('routed'):
            L.append(f'\n**Δ:** autofit trades **{b["lut"] - f["lut"]:,.0f} LUT** '
                     f'({(1 - f["lut"] / b["lut"]) * 100:.0f}% fewer) for {f["bram"]:.0f} BRAM + {f["dsp"]:.0f} DSP'
                     + (f', and Fmax {b["fmax"]:.0f} → {fm:.0f} MHz' if (b["fmax"] == b["fmax"] and fm == fm) else '') + '.')
    else:
        L.append(f'**Autofit:** INFEASIBLE — binding {result.binding}.')
    L.append('')
    (out_dir / 'SUMMARY.md').write_text('\n'.join(L))
    return cmp_df


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def _baseline_candidate(result):
    """The no-mark (LUT-only) candidate in the predicted front."""
    for c in result.front:
        if c.config.bram_thr is None and c.config.dsp_bo is None:
            return c
    return None


def front_dataframe(result):
    import pandas as pd
    rows = []
    for c in result.front:
        p = c.predicted
        rows.append(dict(config=c.config.name, lut=p.lut, ff=p.ff, bram=p.bram,
                         dsp=p.dsp, latency=p.latency,
                         fits=result.budget.fits(p * result.n_instances)))
    return pd.DataFrame(rows).sort_values('lut').reset_index(drop=True)


def write_outputs(cfg: ModelCfg, result, comb, out_dir: Path | None = None):
    """Write fit_front.csv, result.json and SUMMARY.md into the notebook folder."""
    out_dir = Path(out_dir) if out_dir is not None else cfg.nb_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    df = front_dataframe(result)
    df.to_csv(out_dir / 'fit_front.csv', index=False)

    base = _baseline_candidate(result)
    base_pred_lut = float(base.predicted.lut) if base else None
    chosen = result.predicted
    budget = budget_for(cfg)
    usable = budget.usable()
    info = {
        'model': cfg.title,
        'family': cfg.family,
        'part': cfg.part_name,
        'part_capacity': cfg.part_cap,
        'constraint': 'fit_exact_part' if cfg.part_constrained else 'lut_0.85x_baseline',
        'clock_period_ns': cfg.clock_period,
        'latency_cutoff_ns': cfg.latency_cutoff,
        'baseline_lut_tableIII': cfg.baseline_lut,
        'budget': dict(lut=budget.lut, ff=budget.ff, bram=budget.bram, dsp=budget.dsp),
        'usable_after_margins': usable.as_dict(),
        'lut_budget': cfg.lut_budget,
        'comb_cost': float(comb.cost),
        'a0_predicted_lut': base_pred_lut,
        'feasible': bool(result.feasible),
        'binding': result.binding,
        'chosen_config': result.config.name if result.config else None,
        'predicted': chosen.as_dict() | {'latency': chosen.latency} if chosen else None,
        'confirm': result.confirm,
    }
    (out_dir / 'result.json').write_text(json.dumps(info, indent=2))

    # SUMMARY.md
    cap = cfg.part_cap
    L = [f'# Fit summary — {cfg.title}', '',
         f'- **Part:** `{cfg.part_name}`  ({cap["lut"]:,} LUT / {cap["ff"]:,} FF / {cap["bram"]} BRAM / {cap["dsp"]} DSP)',
         f'- **Published baseline (Table III):** {cfg.baseline_lut:,} LUT, DSP 0']
    if cfg.part_constrained:
        over = cfg.baseline_lut - cap['lut']
        L += [f'- **Target — physically fit on the part:** budget {cap["lut"]:,} LUT / {cap["bram"]} BRAM / {cap["dsp"]} DSP '
              f'(usable after margins: {usable.lut:,.0f} LUT / {usable.bram:.0f} BRAM / {usable.dsp:.0f} DSP).',
              f'  The {cfg.baseline_lut:,}-LUT baseline **overflows the part by {over:,} LUT ('
              f'{over / cap["lut"] * 100:.0f}%)** — it must offload BRAM/DSP to fit.']
    else:
        L.append(f'- **LUT budget (0.85×):** {cfg.lut_budget:,} LUT  (target −15%); FF/BRAM/DSP unconstrained.')
    L += [f'- **Clock / latency cutoff:** {cfg.clock_period} ns / {cfg.latency_cutoff} ns', '']
    if base_pred_lut is not None:
        L.append(f'- **A0 baseline (synth-calibrated LUT-only prediction):** {base_pred_lut:,.0f} LUT '
                 f'({base_pred_lut / cfg.baseline_lut * 100:.0f}% of Table III)')
    if not result.feasible:
        L += ['', f'**INFEASIBLE** — no predicate fits. Binding resource(s): {result.binding}.']
    else:
        p = chosen
        line = (f'- predicted (route): **LUT {p.lut:,.0f}** '
                f'({p.lut / cfg.baseline_lut * 100:.0f}% of baseline → '
                f'−{(1 - p.lut / cfg.baseline_lut) * 100:.0f}%), '
                f'FF {p.ff:,.0f}, BRAM {p.bram:.0f}, DSP {p.dsp:.0f}, latency {p.latency} cyc')
        if cfg.part_constrained:
            line += f'  [LUT {p.lut / cap["lut"] * 100:.0f}% / BRAM {p.bram / cap["bram"] * 100:.0f}% / DSP {p.dsp / cap["dsp"] * 100:.0f}% of part]'
        L += ['', f'**FIT:** `{result.config.name}`', line]
        if result.confirm:
            c = result.confirm
            L.append(f'- confirmed (route): LUT {c["lut"]:,.0f}, FF {c["ff"]:,.0f}, '
                     f'BRAM {c["bram"]:.0f}, DSP {c["dsp"]:.0f}, Fmax {c.get("fmax", float("nan")):.1f} MHz')
    L.append('')
    (out_dir / 'SUMMARY.md').write_text('\n'.join(L))
    return df, info
