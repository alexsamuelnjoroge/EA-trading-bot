import pandas as pd
import numpy as np
from src.core_engine import RegimeDetector
import logging

logger = logging.getLogger(__name__)


class MarketRegimeDetector(RegimeDetector):
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.volatility_period = self.config.get("volatility_period", 14)
        self.trend_period = self.config.get("trend_period", 20)
        self.momentum_period = self.config.get("momentum_period", 14)
        self.high_volatility_threshold = self.config.get("high_volatility_threshold", 1.5)
        self.low_volatility_threshold = self.config.get("low_volatility_threshold", 0.8)
        self.strong_trend_threshold = self.config.get("strong_trend_threshold", 0.7)

    def detect(self, data: pd.DataFrame, symbol: str) -> str:
        if data is None or len(data) < self.volatility_period:
            return "UNKNOWN"

        try:
            volatility = self.calculate_volatility(data)
            trend_strength = self.calculate_trend_strength(data)
            momentum = self.calculate_momentum(data)

            regime = self.classify_regime(volatility, trend_strength, momentum)
            logger.info(f"{symbol} - Regime: {regime} (Vol: {volatility:.2f}, Trend: {trend_strength:.2f})")

            return regime

        except Exception as e:
            logger.error(f"Error detecting regime for {symbol}: {e}")
            return "UNKNOWN"

    def calculate_volatility(self, data: pd.DataFrame) -> float:
        close = data["close"].values
        returns = np.diff(np.log(close))
        volatility = np.std(returns[-self.volatility_period :]) * 100

        normalized_volatility = volatility / np.mean(
            [np.std(returns[i : i + self.volatility_period]) for i in range(len(returns) - self.volatility_period)]
        )

        return normalized_volatility

    def calculate_trend_strength(self, data: pd.DataFrame) -> float:
        close = data["close"].values
        high = data["high"].values
        low = data["low"].values

        up_moves = np.sum(np.diff(close) > 0)
        down_moves = np.sum(np.diff(close) < 0)
        total_moves = up_moves + down_moves

        if total_moves == 0:
            return 0.5

        trend_bias = up_moves / total_moves

        atr = self.calculate_atr(data)
        price_range = (close[-1] - close[-self.trend_period]) / (atr * self.trend_period)

        trend_strength = abs(price_range) * trend_bias

        return trend_strength

    def calculate_momentum(self, data: pd.DataFrame) -> float:
        close = data["close"].values
        price_change = (close[-1] - close[-self.momentum_period]) / close[-self.momentum_period]

        momentum = price_change * 100

        return momentum

    def calculate_atr(self, data: pd.DataFrame) -> float:
        high = data["high"].values
        low = data["low"].values
        close = data["close"].values

        tr = np.zeros(len(high))
        for i in range(1, len(high)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1]),
            )

        atr = np.mean(tr[-self.volatility_period :])
        return atr

    def classify_regime(self, volatility: float, trend_strength: float, momentum: float) -> str:
        if volatility > self.high_volatility_threshold:
            if abs(trend_strength) > self.strong_trend_threshold:
                return "VOLATILE_TRENDING" if trend_strength > 0 else "VOLATILE_TRENDING_DOWN"
            else:
                return "VOLATILE_RANGING"

        elif volatility < self.low_volatility_threshold:
            if abs(trend_strength) > self.strong_trend_threshold:
                return "CALM_TRENDING" if trend_strength > 0 else "CALM_TRENDING_DOWN"
            else:
                return "CALM_RANGING"

        else:
            if abs(trend_strength) > self.strong_trend_threshold:
                return "MODERATE_TRENDING" if trend_strength > 0 else "MODERATE_TRENDING_DOWN"
            else:
                return "MODERATE_RANGING"


class AdaptiveRegimeDetector(MarketRegimeDetector):
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.regime_memory = {}
        self.adaptation_factor = self.config.get("adaptation_factor", 0.7)

    def detect(self, data: pd.DataFrame, symbol: str) -> str:
        current_regime = super().detect(data, symbol)

        if symbol in self.regime_memory:
            previous_regime = self.regime_memory[symbol]

            if current_regime != previous_regime:
                logger.info(f"{symbol} - Regime change: {previous_regime} -> {current_regime}")

        self.regime_memory[symbol] = current_regime

        return current_regime

    def get_regime_statistics(self) -> dict:
        return {
            "total_symbols": len(self.regime_memory),
            "regimes": self.regime_memory,
        }
