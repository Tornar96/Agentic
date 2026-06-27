import math

import pytest

from scanner.indicators import daily_change_pct, rsi


def test_daily_change_drop():
    assert daily_change_pct(96.0, 100.0) == pytest.approx(-0.04)


def test_daily_change_gain():
    assert daily_change_pct(110.0, 100.0) == pytest.approx(0.10)


def test_daily_change_rejects_nonpositive_prior():
    with pytest.raises(ValueError):
        daily_change_pct(10.0, 0.0)


def test_rsi_all_gains_is_100():
    closes = [float(x) for x in range(1, 20)]  # strictly increasing
    assert rsi(closes) == 100.0


def test_rsi_all_losses_is_0():
    closes = [float(x) for x in range(20, 1, -1)]  # strictly decreasing
    assert rsi(closes) == 0.0


def test_rsi_requires_enough_data():
    with pytest.raises(ValueError):
        rsi([1.0, 2.0, 3.0], period=14)


def test_rsi_stockcharts_reference():
    # Canonical StockCharts RSI(14) worked example. The first RSI value off
    # these 15 closes is ~70.5 across common references; assert a tight band.
    closes = [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
        45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
    ]
    value = rsi(closes, period=14)
    assert 70.0 <= value <= 71.0


def test_rsi_oversold_when_recent_selloff():
    # Flat then a sharp multi-day decline -> deeply oversold (< 30).
    closes = [100.0] * 14 + [97.0, 94.0, 91.0, 88.0, 85.0]
    assert rsi(closes, period=14) < 30.0
