"""cocotb test driver for the bwin_4_bwout_7 jsc design.

Invoked by `cocotb_jsc_test.ipynb` via `cocotb_tools.runner`. Mirrors the
loop pattern of the C++ binder under `sim/binder_util.hh`:

    iter t  : drive model_inp = inputs[t] (or 0 once exhausted)
              one rising edge fires
              read model_out (if t >= latency, the read is output[t-latency])

A small `Timer(1, 'ns')` after each rising edge advances past the NBA
region — cocotb's bare `await RisingEdge(clk)` returns *before* the
non-blocking assignments settle, so reading `dut.model_out.value`
immediately would return pre-edge values and silently shift everything
by one cycle.

Two tests:

1. `correctness_and_latency` — drive N pre-quantised vectors, capture
   the outputs at the binder-equivalent slot, bit-exact compare. A
   wrong claimed latency would shift the capture window and every
   sample would mismatch.

2. `latency_boundary` — drive a single distinguishable sample, hold
   zeros otherwise, scan cycle-by-cycle for the first matching output,
   and assert that cycle equals `metadata.json["latency"]`.
"""

import json
import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import numpy as np


# Post-edge settle delay. 1 ns is well inside one half of a 5 ns clock
# period — far enough past the rising edge that all NBAs have settled,
# but well before the next falling/rising edge.
SETTLE = (1, 'ns')


def _load():
    data_dir = Path(os.environ['TEST_DATA_DIR'])
    cfg = json.loads((data_dir / 'test_config.json').read_text())
    vecs = np.load(data_dir / 'test_vectors.npz', allow_pickle=True)
    return cfg, vecs


def _unpack_outputs(model_out_int, cfg):
    """Decode the 15-bit-per-output slot format into signed integers."""
    out = []
    slot_w = cfg['out_slot_w']
    ref    = cfg['out_lsb_ref']
    for j, (bw, f, k) in enumerate(zip(cfg['out_bws'], cfg['out_fs'], cfg['out_ks'])):
        slot = (model_out_int >> (slot_w * j)) & ((1 << slot_w) - 1)
        v_uint = (slot >> (ref - f)) & ((1 << bw) - 1)
        if k and (v_uint >> (bw - 1)) & 1:
            v_uint -= (1 << bw)
        out.append(v_uint)
    return out


@cocotb.test()
async def correctness_and_latency(dut):
    cfg, vecs = _load()
    inputs   = list(vecs['model_inp'])
    expected = vecs['expected'].astype(int)
    latency  = int(cfg['latency'])
    period   = float(cfg['clock_period_ns'])
    n        = len(inputs)
    dut._log.info(f'N samples = {n}, claimed latency = {latency} cycles')

    cocotb.start_soon(Clock(dut.clk, period, units='ns').start())
    dut.model_inp.value = 0

    captured = [None] * n
    for t in range(n + latency):
        # Drive input before the edge — same as the binder's write_input.
        dut.model_inp.value = inputs[t] if t < n else 0
        await RisingEdge(dut.clk)
        if t >= latency:
            await Timer(*SETTLE)        # let NBA region settle
            idx = t - latency
            if idx < n:
                captured[idx] = _unpack_outputs(int(dut.model_out.value), cfg)

    fails = [(i, captured[i], expected[i].tolist())
             for i in range(n) if captured[i] != expected[i].tolist()]
    if fails:
        dut._log.error(f'{len(fails)}/{n} samples MISMATCH (first 5):')
        for i, got, exp in fails[:5]:
            dut._log.error(f'  sample {i}: got {got}  expected {exp}')
        assert False, f'{len(fails)}/{n} samples mismatched'
    dut._log.info(f'All {n} samples bit-exact: output[i] captured at '
                  f'iter t = {latency} + i = (latency + i) as claimed.')


@cocotb.test()
async def latency_boundary(dut):
    """Drive one stimulus before the loop, scan cycle-by-cycle for the
    first matching output. Match iter must equal `latency` — the binder's
    iter index at which output_0 first becomes valid."""
    cfg, vecs = _load()
    inputs   = list(vecs['model_inp'])
    expected = vecs['expected'].astype(int)
    latency  = int(cfg['latency'])
    period   = float(cfg['clock_period_ns'])

    probe_inp = inputs[0]
    probe_exp = expected[0].tolist()

    cocotb.start_soon(Clock(dut.clk, period, units='ns').start())
    dut.model_inp.value = probe_inp     # on the bus before edge 1

    match_iter = None
    for t in range(latency + 8):
        await RisingEdge(dut.clk)
        if t == 0:
            dut.model_inp.value = 0     # only edge 1 latches probe
        await Timer(*SETTLE)
        got = _unpack_outputs(int(dut.model_out.value), cfg)
        if got == probe_exp:
            match_iter = t
            break

    dut._log.info(f'probe matched at iter t = {match_iter}  '
                  f'(claimed latency = {latency})')
    assert match_iter is not None, 'probe never matched within latency+8 cycles'
    assert match_iter == latency, (
        f'latency boundary mismatch: claimed {latency}, measured {match_iter}. '
        f'(metadata.json["latency"] is off by {match_iter - latency} cycles.)'
    )
