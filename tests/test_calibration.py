"""Tests for the calibration pipeline."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.reference_data import REFERENCE_DATASETS, write_reference_csvs
from src.calibration import load_reference_csv


def test_reference_datasets_exist():
    """Three reference datasets are defined with valid metadata."""
    assert len(REFERENCE_DATASETS) == 3
    for name, meta in REFERENCE_DATASETS.items():
        assert meta["chemistry"] in ("NCA/graphite", "LCO/graphite", "NMC811/graphite-SiOx")
        assert meta["doi"].startswith("10.")
        assert len(meta["curve"]) >= 10


def test_write_and_load_csv(tmp_path):
    """CSVs can be written by reference_data and loaded by calibration."""
    write_reference_csvs(str(tmp_path))
    for name in REFERENCE_DATASETS:
        csv_path = os.path.join(str(tmp_path), f"{name.lower()}.csv")
        assert os.path.exists(csv_path)
        data = load_reference_csv(csv_path)
        assert data.shape[1] == 2
        assert data[0, 1] == 1.0  # cycle 1 retention = 100%
