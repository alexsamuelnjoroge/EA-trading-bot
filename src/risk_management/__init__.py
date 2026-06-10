import logging
import numpy as np
from src.core_engine import Signal, RiskManager

logger = logging.getLogger(__name__)


class InstitutionalRiskManager(RiskManager):
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.daily_loss_limit = self.config.get("daily_loss_limit", -500)
        self.max_drawdown = self.config.get("max_drawdown", 0.20)
        self.risk_per_trade = self.config.get("risk_per_trade", 0.02)
        self.kelly_factor = self.config.get("kelly_factor", 0.25)
        self.max_position_size_pct = self.config.get("max_position_size_pct", 0.10)
        self.min_rr_ratio = self.config.get("min_rr_ratio", 1.5)

    def calculate_position_size(
        self,
        account_equity: float,
        symbol: str,
        signal: Signal,
        current_price: float,
        win_rate: float = 0.55,
        avg_win: float = 1.5,
        avg_loss: float = 1.0,
    ) -> float:
        if signal == Signal.HOLD:
            return 0

        try:
            risk_amount = account_equity * self.risk_per_trade

            kelly_percentage = self.calculate_kelly_percentage(win_rate, avg_win, avg_loss)

            kelly_position_size = (account_equity * kelly_percentage * self.kelly_factor) / current_price

            equity_based_size = (account_equity * self.max_position_size_pct) / current_price

            position_size = min(kelly_position_size, equity_based_size)

            position_size = max(position_size, 0.01)

            logger.info(
                f"Position size for {symbol}: {position_size:.2f} "
                f"(Kelly: {kelly_percentage*100:.1f}%, Risk: {risk_amount:.2f})"
            )

            return position_size

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0

    @staticmethod
    def calculate_kelly_percentage(win_rate: float, avg_win: float, avg_loss: float) -> float:
        if avg_loss == 0:
            return 0

        win_probability = win_rate
        loss_probability = 1 - win_rate
        win_loss_ratio = avg_win / avg_loss

        kelly = (win_probability * win_loss_ratio - loss_probability) / win_loss_ratio

        kelly = max(0, min(kelly, 0.25))

        return kelly

    def calculate_stop_loss(self, entry_price: float, atr: float, signal: Signal) -> float:
        if signal == Signal.BUY:
            return entry_price - (atr * 1.5)
        elif signal == Signal.SELL:
            return entry_price + (atr * 1.5)
        return entry_price

    def calculate_take_profit(self, entry_price: float, atr: float, signal: Signal) -> float:
        if signal == Signal.BUY:
            return entry_price + (atr * 2.5)
        elif signal == Signal.SELL:
            return entry_price - (atr * 2.5)
        return entry_price

    def check_daily_loss_limit(self, current_daily_loss: float) -> bool:
        if current_daily_loss < self.daily_loss_limit:
            logger.warning(f"Daily loss limit exceeded: {current_daily_loss:.2f}")
            return False
        return True

    def check_max_drawdown(self, current_equity: float, initial_equity: float) -> bool:
        if initial_equity == 0:
            return True

        drawdown = (initial_equity - current_equity) / initial_equity

        if drawdown > self.max_drawdown:
            logger.warning(f"Maximum drawdown exceeded: {drawdown*100:.1f}%")
            return False

        return True


class VolatilityAdjustedRiskManager(InstitutionalRiskManager):
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.base_atr_period = self.config.get("atr_period", 14)
        self.volatility_threshold = self.config.get("volatility_threshold", 1.5)

    def calculate_position_size(
        self,
        account_equity: float,
        symbol: str,
        signal: Signal,
        current_price: float,
        volatility: float = None,
        atr: float = None,
        win_rate: float = 0.55,
        avg_win: float = 1.5,
        avg_loss: float = 1.0,
    ) -> float:
        base_size = super().calculate_position_size(
            account_equity, symbol, signal, current_price, win_rate, avg_win, avg_loss
        )

        if volatility is None or atr is None:
            return base_size

        if atr > self.volatility_threshold:
            volatility_factor = 1.0 / (atr / self.volatility_threshold)
            adjusted_size = base_size * volatility_factor
            logger.info(f"Position size adjusted for volatility: {adjusted_size:.2f} (factor: {volatility_factor:.2f})")
            return adjusted_size

        return base_size
