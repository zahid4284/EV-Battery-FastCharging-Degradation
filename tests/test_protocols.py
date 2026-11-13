"""Smoke tests: the protocol definitions and one short simulation cycle."""

import numpy as np
import pytest

from src import metrics, protocols, simulate


def test_every_protocol_is_a_valid_cycle():
    for key in protocols.PROTOCOLS:
        steps = protocols.cycle_steps(key)
        assert isinstance(steps, tuple)
        # discharge + at least one charge stage + rest
        assert len(steps) >= 3
        assert steps[0].startswith("Discharge")
        assert steps[-1].startswith("Rest")


def test_experiment_groups_steps_into_cycles():
    experiment = protocols.pybamm_experiment(["cc_cv_1C"], 3)
    # Each cycle is a tuple; three cycles requested.
    assert len(experiment.cycles) == 3


def test_single_cycle_metrics_are_physical():
    rows, profile = simulate.run_protocol("cc_cv_1C", 1, mode="thermal")
    row = rows[0]
    assert 30.0 < row["charge_time_to_target_min"] < 120.0
    assert 20.0 < row["t_max_charge_c"] < 60.0
    assert row["discharge_capacity_ah"] > 3.0
    time_min, temperature = profile
    assert np.all(np.isfinite(temperature))
    assert time_min.size == temperature.size
