import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from src.core_engine import Signal
import logging

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    def __init__(self, name: str, params: dict = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        """Generate trading signal based on data"""
        pass

    def add_indicator(self, data: pd.DataFrame, indicator_name: str, indicator_func, **kwargs) -> pd.DataFrame:
        """Add technical indicator to dataframe"""
        try:
            data[indicator_name] = indicator_func(data, **kwargs)
            return data
        except Exception as e:
            logger.error(f"Error adding indicator {indicator_name}: {e}")
            return data

    def validate_data(self, data: pd.DataFrame, min_rows: int = 20) -> bool:
        """Validate data has enough rows"""
        if data is None or len(data) < min_rows:
            logger.warning(f"Insufficient data: {len(data) if data is not None else 0} rows")
            return False
        return True

    @staticmethod
    def calculate_atr(data: pd.DataFrame, period: int = 14) -> np.ndarray:
        """Calculate Average True Range - volatility measure"""
        if len(data) < period:
            return np.array([0])

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

        atr = np.array([np.mean(tr[max(0, i - period + 1):i + 1]) for i in range(len(tr))])
        return atr

    @staticmethod
    def calculate_macd(data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD and signal line"""
        close = data["close"].values
        ema_fast = BaseStrategy._calculate_ema(close, fast)
        ema_slow = BaseStrategy._calculate_ema(close, slow)
        macd_line = ema_fast - ema_slow
        signal_line = BaseStrategy._calculate_ema(macd_line, signal)
        return macd_line, signal_line

    @staticmethod
    def _calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.zeros(len(prices))
        ema = np.zeros(len(prices))
        multiplier = 2 / (period + 1)
        ema[period - 1] = np.mean(prices[:period])
        for i in range(period, len(prices)):
            ema[i] = (prices[i] * multiplier) + (ema[i - 1] * (1 - multiplier))
        return ema


class TrendFollowingStrategy(BaseStrategy):
    def __init__(self, params: dict = None):
        default_params = {
            "fast_ma_period": 10,
            "slow_ma_period": 20,
            "adx_period": 14,
            "adx_threshold": 25,
            "atr_period": 14,
            "min_atr_ratio": 0.5,
            "max_atr_ratio": 2.0,
            "use_macd_confirmation": True,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "stop_loss_pips": 50,
            "take_profit_pips": 150,
        }
        if params:
            default_params.update(params)

        super().__init__("TrendFollowing", default_params)

    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        if not self.validate_data(data, min_rows=30):
            return Signal.HOLD

        try:
            close = data["close"].values
            high = data["high"].values
            low = data["low"].values

            fast_period = self.params["fast_ma_period"]
            slow_period = self.params["slow_ma_period"]

            # Main trend indicators
            fast_ma = self.simple_moving_average(close, fast_period)
            slow_ma = self.simple_moving_average(close, slow_period)

            adx = self.calculate_adx(high, low, close, self.params["adx_period"])
            adx_threshold = self.params["adx_threshold"]

            # Volatility filter - only trade in reasonable volatility
            atr = self.calculate_atr(data, self.params["atr_period"])
            atr_sma = np.mean(atr[-20:]) if len(atr) > 20 else atr[-1]
            atr_ratio = atr[-1] / (atr_sma + 1e-10)

            if atr_ratio < self.params["min_atr_ratio"] or atr_ratio > self.params["max_atr_ratio"]:
                return Signal.HOLD

            # ADX filter - require strong trend
            if adx[-1] < adx_threshold:
                return Signal.HOLD

            # MA crossover signal
            ma_signal = Signal.HOLD
            if fast_ma[-1] > slow_ma[-1] and fast_ma[-2] <= slow_ma[-2]:
                ma_signal = Signal.BUY
            elif fast_ma[-1] < slow_ma[-1] and fast_ma[-2] >= slow_ma[-2]:
                ma_signal = Signal.SELL

            if ma_signal == Signal.HOLD:
                return Signal.HOLD

            # MACD confirmation (optional)
            if self.params["use_macd_confirmation"]:
                macd_line, signal_line = self.calculate_macd(
                    data,
                    self.params["macd_fast"],
                    self.params["macd_slow"],
                    self.params["macd_signal"]
                )

                if ma_signal == Signal.BUY:
                    if macd_line[-1] <= 0:  # MACD below zero = stronger confirmation
                        return Signal.HOLD
                elif ma_signal == Signal.SELL:
                    if macd_line[-1] >= 0:  # MACD above zero = stronger confirmation
                        return Signal.HOLD

            return ma_signal

        except Exception as e:
            logger.error(f"Error in TrendFollowingStrategy: {e}")
            return Signal.HOLD

    @staticmethod
    def simple_moving_average(prices: np.ndarray, period: int) -> np.ndarray:
        return np.convolve(prices, np.ones(period) / period, mode="valid")

    @staticmethod
    def calculate_adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
        plus_dm = np.zeros(len(high))
        minus_dm = np.zeros(len(high))
        tr = np.zeros(len(high))

        for i in range(1, len(high)):
            up_move = high[i] - high[i - 1]
            down_move = low[i - 1] - low[i]

            if up_move > down_move and up_move > 0:
                plus_dm[i] = up_move
            if down_move > up_move and down_move > 0:
                minus_dm[i] = down_move

            tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))

        atr = np.convolve(tr, np.ones(period) / period, mode="valid")
        plus_di = np.convolve(plus_dm, np.ones(period) / period, mode="valid") / atr * 100 if len(atr) > 0 else np.array([0])
        minus_di = np.convolve(minus_dm, np.ones(period) / period, mode="valid") / atr * 100 if len(atr) > 0 else np.array([0])

        di_diff = np.abs(plus_di - minus_di)
        di_sum = plus_di + minus_di
        dx = (di_diff / di_sum * 100) if len(di_sum) > 0 else np.array([0])

        adx = np.convolve(dx, np.ones(period) / period, mode="valid") if len(dx) > period else np.array([0])

        return adx if len(adx) > 0 else np.array([0])


class MeanReversionStrategy(BaseStrategy):
    def __init__(self, params: dict = None):
        default_params = {
            "bb_period": 20,
            "bb_std_dev": 2,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "atr_period": 14,
            "max_atr_ratio": 1.0,
            "use_trend_filter": True,
            "trend_ma_period": 50,
        }
        if params:
            default_params.update(params)

        super().__init__("MeanReversion", default_params)

    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        if not self.validate_data(data, min_rows=30):
            return Signal.HOLD

        try:
            close = data["close"].values
            high = data["high"].values
            low = data["low"].values

            bb_period = self.params["bb_period"]
            bb_std = self.params["bb_std_dev"]

            sma = self.simple_moving_average(close, bb_period)
            std = self.calculate_std(close, bb_period)

            upper_band = sma + (bb_std * std)
            lower_band = sma - (bb_std * std)

            rsi = self.calculate_rsi(close, self.params["rsi_period"])
            rsi_oversold = self.params["rsi_oversold"]
            rsi_overbought = self.params["rsi_overbought"]

            # Volatility filter - only trade mean reversion in LOW volatility
            atr = self.calculate_atr(data, self.params["atr_period"])
            atr_sma = np.mean(atr[-20:]) if len(atr) > 20 else atr[-1]
            atr_ratio = atr[-1] / (atr_sma + 1e-10)

            if atr_ratio > self.params["max_atr_ratio"]:
                return Signal.HOLD

            # Trend filter - don't trade against strong trends
            if self.params["use_trend_filter"]:
                trend_ma = self.simple_moving_average(close, self.params["trend_ma_period"])
                current_price = close[-1]

                if len(trend_ma) > 0:
                    if current_price > trend_ma[-1] * 1.02:
                        if rsi[-1] > rsi_overbought:
                            return Signal.SELL
                        return Signal.HOLD
                    elif current_price < trend_ma[-1] * 0.98:
                        if rsi[-1] < rsi_oversold:
                            return Signal.BUY
                        return Signal.HOLD

            current_price = close[-1]

            # Bollinger Bands + RSI confirmation
            if current_price < lower_band[-1] and rsi[-1] < rsi_oversold:
                return Signal.BUY

            if current_price > upper_band[-1] and rsi[-1] > rsi_overbought:
                return Signal.SELL

            return Signal.HOLD

        except Exception as e:
            logger.error(f"Error in MeanReversionStrategy: {e}")
            return Signal.HOLD

    @staticmethod
    def simple_moving_average(prices: np.ndarray, period: int) -> np.ndarray:
        if len(prices) < period:
            return np.array([])
        return np.convolve(prices, np.ones(period) / period, mode="valid")

    @staticmethod
    def calculate_std(prices: np.ndarray, period: int) -> np.ndarray:
        std = np.array([np.std(prices[i : i + period]) for i in range(len(prices) - period + 1)])
        return std

    @staticmethod
    def calculate_rsi(prices: np.ndarray, period: int) -> np.ndarray:
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.convolve(gains, np.ones(period) / period, mode="valid")
        avg_loss = np.convolve(losses, np.ones(period) / period, mode="valid")

        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))

        return rsi
