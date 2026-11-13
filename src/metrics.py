"""Extraction of per-cycle performance and degradation metrics."""

import numpy as np

TEMPERATURE_NAMES = ("Cell temperature [C]", "X-averaged cell temperature [C]",
                     "Volume-averaged cell temperature [C]")


def _entries(solution, *names):
    """Return the first variable that exists, keeping the code version-tolerant."""
    last_error = None
    for name in names:
        try:
            return np.ravel(np.asarray(solution[name].entries, dtype=float))
        except Exception as err:  # variable renamed / not available
            last_error = err
    raise KeyError(f"None of {names} found") from last_error


def temperature_series(solution, n_times):
    """Per-time temperature, maximised over space (mesh) if needed.

    PyBaMM stores spatially resolved variables in (space, time) order, i.e.
    ``entries.reshape(n_space, n_times)``.
    """
    values = _entries(solution, *TEMPERATURE_NAMES)
    if values.size != n_times:
        values = values.reshape(-1, n_times).max(axis=0)
    return values


def _optional_max(solution, name):
    """Maximum of a degradation variable, or NaN when the model lacks it."""
    try:
        return float(np.max(_entries(solution, name)))
    except KeyError:
        return float("nan")


def cycle_metrics(cycle, q_nominal, target_soc=0.8):
    """Performance metrics of a single cycle.

    Step order is fixed by protocols.cycle_steps: discharge, charge stages...
    and a final rest.
    """
    discharge_step = cycle.steps[0]
    charge_steps = cycle.steps[1:-1]

    q_discharge = float(np.max(_entries(discharge_step, "Discharge capacity [A.h]")))

    # Cumulative charge throughput versus time, concatenated over all stages.
    times, charges = [], []
    time_offset, accumulated = 0.0, 0.0
    for step in charge_steps:
        t = np.asarray(step.t, dtype=float)
        current = np.abs(_entries(step, "Current [A]"))
        dq = 0.5 * (current[1:] + current[:-1]) * np.diff(t) / 3600.0
        q = accumulated + np.concatenate(([0.0], np.cumsum(dq)))
        times.append(t - t[0] + time_offset)
        charges.append(q)
        accumulated = q[-1]
        time_offset = times[-1][-1]
    times = np.concatenate(times)
    charges = np.concatenate(charges)

    target = target_soc * q_nominal
    if charges[-1] >= target:
        time_to_target = float(np.interp(target, charges, times)) / 60.0
    else:
        time_to_target = float("nan")

    temperature = np.concatenate(
        [temperature_series(s, s.t.size) for s in charge_steps])

    return {
        "discharge_capacity_ah": q_discharge,
        "charge_time_to_target_min": time_to_target,
        "charge_time_full_min": time_offset / 60.0,
        "t_max_charge_c": float(temperature.max()),
        "sei_loss_ah": _optional_max(cycle, "Loss of capacity to negative SEI [A.h]"),
        "plating_loss_ah": _optional_max(
            cycle, "Loss of capacity to negative lithium plating [A.h]"),
    }
