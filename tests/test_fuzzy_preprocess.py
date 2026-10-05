"""
Tests for fuzzy logic and preprocess helpers
"""
import numpy as np

from src.model import fuzzy_logic, preprocess
from src.config import RF_FEATURES


def test_fuzzy_system_builds():
    fz = fuzzy_logic.FuzzyFloodRisk()
    assert fz.system is not None


def test_compute_risk_level():
    assert preprocess.calculate_risk_level(0) in ["normal", "alert", "alarm", "critical"]


def test_rf_features_present():
    assert all(f in RF_FEATURES for f in ["R1", "R3", "R7", "rain_days", "TMAX", "TMIN", "TideMax", "TideMin"])
