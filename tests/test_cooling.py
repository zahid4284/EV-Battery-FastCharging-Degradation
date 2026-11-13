"""Tests for cooling sensitivity data consistency."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd


def test_cooling_summary_has_three_h_values():
    """cooling_summary.csv covers h = 1, 10, 100."""
    path = "results/cooling_summary.csv"
    if not os.path.exists(path):
        return  # skip if not generated
    df = pd.read_csv(path)
    assert set(df["h_wm2k"].unique()) == {1.0, 10.0, 100.0}


def test_higher_h_gives_lower_temperature():
    """For each protocol, increasing h decreases peak temperature."""
    path = "results/cooling_summary.csv"
    if not os.path.exists(path):
        return
    df = pd.read_csv(path)
    for proto in df["protocol"].unique():
        g = df[df["protocol"] == proto].sort_values("h_wm2k")
        temps = g["t_max_charge_c"].values
        assert temps[0] > temps[-1]  # h=1 hotter than h=100
