import pytest
import pandas as pd
import numpy as np
from src.strategies import TrendFollowingStrategy, MeanReversionStrategy
from src.core_engine import Signal


@pytest.fixture
def sample_data():
    """Create sample OHLC data for testing"""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="H")

    close = 100 + np.cumsum(np.random.randn(100) * 0.5)
    open_prices = close + np.random.randn(100) * 0.2
    high = np.maximum(open_prices, close) + np.abs(np.random.randn(100) * 0.2)
    low = np.minimum(open_prices, close) - np.abs(np.random.randn(100) * 0.2)

    data = pd.DataFrame(
        {
            "open": open_prices,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": np.random.randint(1000, 10000, 100),
            "real_volume": np.random.randint(500, 5000, 100),
        },
        index=dates,
    )

    return data


def test_trend_following_strategy_initialization():
    """Test strategy initialization"""
    strategy = TrendFollowingStrategy()
    assert strategy.name == "TrendFollowing"
    assert strategy.params["fast_ma_period"] == 10
    assert strategy.params["slow_ma_period"] == 20


def test_trend_following_strategy_with_custom_params():
    """Test strategy with custom parameters"""
    params = {"fast_ma_period": 5, "slow_ma_period": 15}
    strategy = TrendFollowingStrategy(params)
    assert strategy.params["fast_ma_period"] == 5
    assert strategy.params["slow_ma_period"] == 15


def test_trend_following_signal_generation(sample_data):
    """Test signal generation"""
    strategy = TrendFollowingStrategy()
    signal = strategy.generate_signal(sample_data, "EURUSD")
    assert signal in [Signal.BUY, Signal.SELL, Signal.HOLD]


def test_trend_following_insufficient_data():
    """Test handling of insufficient data"""
    strategy = TrendFollowingStrategy()
    small_data = pd.DataFrame({"close": [100, 101, 102]})
    signal = strategy.generate_signal(small_data, "EURUSD")
    assert signal == Signal.HOLD


def test_mean_reversion_strategy_initialization():
    """Test mean reversion strategy initialization"""
    strategy = MeanReversionStrategy()
    assert strategy.name == "MeanReversion"
    assert strategy.params["bb_period"] == 20
    assert strategy.params["rsi_period"] == 14


def test_mean_reversion_signal_generation(sample_data):
    """Test mean reversion signal generation"""
    strategy = MeanReversionStrategy()
    signal = strategy.generate_signal(sample_data, "EURUSD")
    assert signal in [Signal.BUY, Signal.SELL, Signal.HOLD]


def test_simple_moving_average():
    """Test moving average calculation"""
    prices = np.array([100, 101, 102, 103, 104, 105])
    ma = TrendFollowingStrategy.simple_moving_average(prices, 3)
    expected = np.array([101, 102, 103, 104])
    np.testing.assert_array_almost_equal(ma, expected)


def test_rsi_calculation():
    """Test RSI calculation"""
    prices = np.array([100, 102, 101, 103, 105, 104, 106, 108])
    rsi = MeanReversionStrategy.calculate_rsi(prices, 3)
    assert len(rsi) > 0
    assert np.all(rsi >= 0)
    assert np.all(rsi <= 100)


def test_strategy_with_none_data():
    """Test handling of None data"""
    strategy = TrendFollowingStrategy()
    signal = strategy.generate_signal(None, "EURUSD")
    assert signal == Signal.HOLD


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
