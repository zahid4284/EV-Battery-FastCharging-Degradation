"""Tests for the 96-cell pack simulation."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from src.pack import simulate_pack, protocol_current, COOLING_H


def test_pack_runs_and_returns_correct_shape():
    """simulate_pack returns a 3D array with the right dimensions."""
    T_hist, _ = simulate_pack(
        protocol_current("cc_cv_1C"), 45 * 60, dt=2, cooling_h=COOLING_H)
    # shape: (timesteps, rows, cols)
    assert T_hist.ndim == 3
    assert T_hist.shape[1] == 8
    assert T_hist.shape[2] == 12
    # all temperatures physically plausible
    assert T_hist.min() > 0
    assert T_hist.max() < 200


def test_centre_hotter_than_edge():
    """Centre cells run hotter than edge cells (spatially varying cooling)."""
    T_hist, _ = simulate_pack(
        protocol_current("cc_cv_1C"), 45 * 60, dt=2, cooling_h=COOLING_H)
    T_peak = T_hist.max(axis=0)
    centre = T_peak[4, 6]  # centre cell
    edge = T_peak[0, 0]     # corner cell
    assert centre > edge


def test_protocol_current_callable():
    """protocol_current returns a callable that returns current in Amps."""
    I_func = protocol_current("cc_cv_1C")
    assert callable(I_func)
    # 1C on a 5 Ah cell = 5 A during CC phase
    assert abs(I_func(100) - 5.0) < 0.01
