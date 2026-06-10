import pytest
from src.risk_management import InstitutionalRiskManager, VolatilityAdjustedRiskManager
from src.core_engine import Signal


@pytest.fixture
def risk_manager():
    """Create a risk manager instance"""
    config = {
        "daily_loss_limit": -500,
        "max_drawdown": 0.20,
        "risk_per_trade": 0.02,
        "kelly_factor": 0.25,
        "max_position_size_pct": 0.10,
        "min_rr_ratio": 1.5,
    }
    return InstitutionalRiskManager(config)


def test_risk_manager_initialization(risk_manager):
    """Test risk manager initialization"""
    assert risk_manager.daily_loss_limit == -500
    assert risk_manager.max_drawdown == 0.20
    assert risk_manager.risk_per_trade == 0.02


def test_position_size_calculation(risk_manager):
    """Test position size calculation"""
    account_equity = 10000
    symbol = "EURUSD"
    signal = Signal.BUY
    current_price = 1.0850

    position_size = risk_manager.calculate_position_size(
        account_equity=account_equity,
        symbol=symbol,
        signal=signal,
        current_price=current_price,
    )

    assert position_size > 0
    assert position_size <= (account_equity * 0.10) / current_price


def test_position_size_with_hold_signal(risk_manager):
    """Test that HOLD signal returns 0 position size"""
    position_size = risk_manager.calculate_position_size(
        account_equity=10000,
        symbol="EURUSD",
        signal=Signal.HOLD,
        current_price=1.0850,
    )

    assert position_size == 0


def test_kelly_percentage_calculation(risk_manager):
    """Test Kelly percentage calculation"""
    win_rate = 0.55
    avg_win = 1.5
    avg_loss = 1.0

    kelly = InstitutionalRiskManager.calculate_kelly_percentage(
        win_rate, avg_win, avg_loss
    )

    assert kelly > 0
    assert kelly <= 0.25


def test_kelly_percentage_no_wins(risk_manager):
    """Test Kelly when win rate is 0"""
    kelly = InstitutionalRiskManager.calculate_kelly_percentage(0, 1.5, 1.0)
    assert kelly == 0


def test_kelly_percentage_all_wins(risk_manager):
    """Test Kelly when win rate is 1.0"""
    kelly = InstitutionalRiskManager.calculate_kelly_percentage(1.0, 1.5, 1.0)
    assert kelly > 0


def test_stop_loss_calculation_buy(risk_manager):
    """Test stop loss calculation for BUY signal"""
    entry_price = 100.0
    atr = 2.0
    stop_loss = risk_manager.calculate_stop_loss(entry_price, atr, Signal.BUY)
    assert stop_loss < entry_price
    assert stop_loss == pytest.approx(entry_price - (atr * 1.5), rel=1e-5)


def test_stop_loss_calculation_sell(risk_manager):
    """Test stop loss calculation for SELL signal"""
    entry_price = 100.0
    atr = 2.0
    stop_loss = risk_manager.calculate_stop_loss(entry_price, atr, Signal.SELL)
    assert stop_loss > entry_price
    assert stop_loss == pytest.approx(entry_price + (atr * 1.5), rel=1e-5)


def test_take_profit_calculation_buy(risk_manager):
    """Test take profit calculation for BUY signal"""
    entry_price = 100.0
    atr = 2.0
    take_profit = risk_manager.calculate_take_profit(entry_price, atr, Signal.BUY)
    assert take_profit > entry_price
    assert take_profit == pytest.approx(entry_price + (atr * 2.5), rel=1e-5)


def test_take_profit_calculation_sell(risk_manager):
    """Test take profit calculation for SELL signal"""
    entry_price = 100.0
    atr = 2.0
    take_profit = risk_manager.calculate_take_profit(entry_price, atr, Signal.SELL)
    assert take_profit < entry_price
    assert take_profit == pytest.approx(entry_price - (atr * 2.5), rel=1e-5)


def test_daily_loss_limit_check(risk_manager):
    """Test daily loss limit enforcement"""
    assert risk_manager.check_daily_loss_limit(-400) is True
    assert risk_manager.check_daily_loss_limit(-500) is True
    assert risk_manager.check_daily_loss_limit(-600) is False


def test_max_drawdown_check(risk_manager):
    """Test maximum drawdown enforcement"""
    initial_equity = 10000
    current_equity = 8200
    assert risk_manager.check_max_drawdown(current_equity, initial_equity) is True

    current_equity = 7900
    assert risk_manager.check_max_drawdown(current_equity, initial_equity) is False


def test_volatility_adjusted_risk_manager():
    """Test volatility-adjusted risk manager"""
    config = {
        "daily_loss_limit": -500,
        "risk_per_trade": 0.02,
        "atr_period": 14,
        "volatility_threshold": 1.5,
    }
    manager = VolatilityAdjustedRiskManager(config)
    assert manager.base_atr_period == 14
    assert manager.volatility_threshold == 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
