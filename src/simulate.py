"""Run one charging protocol over many cycles and collect metrics."""

import time
import numpy as np
import pybamm

from . import metrics as metrics_mod
from . import protocols
from .model import build_model


def make_solver():
    """IDAKLU is fast; Casadi is a fallback for older PyBaMM releases."""
    if hasattr(pybamm, "IDAKLUSolver"):
        try:
            return pybamm.IDAKLUSolver()
        except Exception:
            pass
    return pybamm.CasadiSolver(mode="safe", dt_max=30)


def run_protocol(key, cycles, mode="ageing", solver=None, model_override=None):
    """Simulate one protocol and return (per-cycle rows, first-cycle profile).

    Parameters
    ----------
    key : str
        Protocol key (see protocols.PROTOCOLS).
    cycles : int
        Number of full charge-discharge cycles to run.
    mode : str
        One of 'ageing', 'thermal', 'coupled'.
    solver : pybamm.Solver, optional
    model_override : tuple or None
        If (model, params), use these instead of build_model(mode).
        Useful for parameter sweeps (e.g. cooling sensitivity).
    """
    if model_override is not None:
        model, params = model_override
    else:
        model, params = build_model(mode)
    experiment = protocols.pybamm_experiment([key], cycles)
    solver = solver or make_solver()

    start = time.time()
    sim = pybamm.Simulation(model, experiment=experiment,
                            parameter_values=params, solver=solver)
    solution = sim.solve()

    rows, profile = [], None
    q_nominal = None
    for index, cycle in enumerate(solution.cycles):
        if q_nominal is None:
            q_nominal = float(np.max(cycle.steps[0]["Discharge capacity [A.h]"].entries))
        row = metrics_mod.cycle_metrics(cycle, q_nominal)
        row.update(protocol=key, label=protocols.PROTOCOLS[key]["label"],
                   cycle=index + 1)
        rows.append(row)

        if index == 0:
            profile = first_charge_profile(cycle)

    elapsed = time.time() - start
    print(f"{protocols.PROTOCOLS[key]['label']:<22} "
          f"cycles={len(rows):3d}  {elapsed:5.1f}s", flush=True)
    return rows, profile


def first_charge_profile(cycle):
    """Time (min) and cell temperature (degC) during the first charge."""
    times, temps = [], []
    offset = 0.0
    for step in cycle.steps[1:-1]:
        t = np.asarray(step.t, dtype=float)
        temp = metrics_mod.temperature_series(step, t.size)
        times.append(t - t[0] + offset)
        temps.append(temp)
        offset = times[-1][-1]
    return np.concatenate(times) / 60.0, np.concatenate(temps)
