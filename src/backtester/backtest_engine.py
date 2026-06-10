import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from src.core_engine import Signal, Trade
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BacktestMetrics:
    """Calculate trading performance metrics"""

    def __init__(self, trades: List[Trade], initial_equity: float):
        self.trades = trades
        self.initial_equity = initial_equity
        self.profitable_trades = [t for t in trades if t.profit and t.profit > 0]
        self.losing_trades = [t for t in trades if t.profit and t.profit < 0]

    def win_rate(self) -> float:
        """Percentage of winning trades"""
        if not self.trades:
            return 0
        return len(self.profitable_trades) / len(self.trades)

    def profit_factor(self) -> float:
        """Total wins / Total losses"""
        if not self.losing_trades:
            return float('inf') if self.profitable_trades else 0

        total_wins = sum(t.profit for t in self.profitable_trades)
        total_losses = abs(sum(t.profit for t in self.losing_trades))

        if total_losses == 0:
            return float('inf') if total_wins > 0 else 0

        return total_wins / total_losses

    def total_profit(self) -> float:
        """Total profit/loss from all trades"""
        return sum(t.profit for t in self.trades if t.profit is not None)

    def average_profit(self) -> float:
        """Average profit per trade"""
        if not self.trades:
            return 0
        return self.total_profit() / len(self.trades)

    def max_profit(self) -> float:
        """Largest single profit"""
        profits = [t.profit for t in self.profitable_trades]
        return max(profits) if profits else 0

    def max_loss(self) -> float:
        """Largest single loss"""
        losses = [t.profit for t in self.losing_trades]
        return min(losses) if losses else 0

    def consecutive_wins(self) -> int:
        """Longest winning streak"""
        max_streak = 0
        current_streak = 0

        for trade in self.trades:
            if trade.profit and trade.profit > 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    def consecutive_losses(self) -> int:
        """Longest losing streak"""
        max_streak = 0
        current_streak = 0

        for trade in self.trades:
            if trade.profit and trade.profit < 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    def sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Risk-adjusted return metric (higher is better)"""
        if not self.trades:
            return 0

        profits = [t.profit for t in self.trades if t.profit is not None]

        if len(profits) < 2:
            return 0

        returns = np.array(profits) / self.initial_equity
        excess_returns = returns - (risk_free_rate / 252)
        std_returns = np.std(excess_returns)

        if std_returns == 0:
            return 0

        return np.mean(excess_returns) / std_returns * np.sqrt(252)

    def sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Risk-adjusted return focusing only on downside"""
        if not self.trades:
            return 0

        profits = [t.profit for t in self.trades if t.profit is not None]

        if len(profits) < 2:
            return 0

        returns = np.array(profits) / self.initial_equity
        excess_returns = returns - (risk_free_rate / 252)

        downside_returns = np.array([r for r in excess_returns if r < 0])
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0

        if downside_std == 0:
            return 0

        return np.mean(excess_returns) / downside_std * np.sqrt(252)

    def max_drawdown(self) -> float:
        """Largest peak-to-valley decline"""
        if not self.trades:
            return 0

        cumulative_profit = 0
        peak = 0
        max_dd = 0

        for trade in self.trades:
            if trade.profit:
                cumulative_profit += trade.profit
                peak = max(peak, cumulative_profit)
                drawdown = (peak - cumulative_profit) / (peak + self.initial_equity) if peak > 0 else 0
                max_dd = max(max_dd, drawdown)

        return max_dd

    def recovery_factor(self) -> float:
        """Total profit / Max drawdown (higher is better)"""
        max_dd = self.max_drawdown()
        if max_dd == 0:
            return float('inf') if self.total_profit() > 0 else 0

        return self.total_profit() / (max_dd * self.initial_equity)

    def calmar_ratio(self) -> float:
        """Annual return / Max drawdown"""
        max_dd = self.max_drawdown()
        if max_dd == 0 or not self.trades:
            return 0

        total_return = self.total_profit() / self.initial_equity

        if self.trades:
            first_date = self.trades[0].entry_time
            last_date = self.trades[-1].exit_time or datetime.now()
            days = (last_date - first_date).days
            years = max(days / 365, 0.01)
            annual_return = total_return / years
        else:
            annual_return = 0

        return annual_return / max_dd if max_dd > 0 else 0

    def summary(self) -> Dict:
        """Get all metrics as dictionary"""
        return {
            "total_trades": len(self.trades),
            "winning_trades": len(self.profitable_trades),
            "losing_trades": len(self.losing_trades),
            "win_rate": f"{self.win_rate()*100:.1f}%",
            "profit_factor": f"{self.profit_factor():.2f}",
            "total_profit": f"${self.total_profit():.2f}",
            "average_profit": f"${self.average_profit():.2f}",
            "max_profit": f"${self.max_profit():.2f}",
            "max_loss": f"${self.max_loss():.2f}",
            "consecutive_wins": self.consecutive_wins(),
            "consecutive_losses": self.consecutive_losses(),
            "sharpe_ratio": f"{self.sharpe_ratio():.2f}",
            "sortino_ratio": f"{self.sortino_ratio():.2f}",
            "max_drawdown": f"{self.max_drawdown()*100:.1f}%",
            "recovery_factor": f"{self.recovery_factor():.2f}",
            "calmar_ratio": f"{self.calmar_ratio():.2f}",
        }


class BacktestEngine:
    """Backtesting engine that replays historical data"""

    def __init__(self, initial_equity: float = 10000, commission: float = 0.0002, slippage_pips: int = 2):
        self.initial_equity = initial_equity
        self.commission = commission
        self.slippage_pips = slippage_pips
        self.equity = initial_equity
        self.trades: List[Trade] = []
        self.equity_history: List[float] = [initial_equity]

    def backtest(
        self,
        data: pd.DataFrame,
        strategy,
        risk_manager,
        regime_detector=None,
        symbol: str = "EURUSD",
    ) -> BacktestMetrics:
        """
        Run backtest on historical data

        Args:
            data: DataFrame with OHLC data
            strategy: Strategy instance with generate_signal method
            risk_manager: Risk manager instance
            regime_detector: Optional regime detector
            symbol: Trading symbol

        Returns:
            BacktestMetrics with performance statistics
        """
        logger.info(f"Starting backtest for {symbol} with {len(data)} bars")

        self.trades = []
        self.equity = self.initial_equity
        self.equity_history = [self.initial_equity]
        open_position = None

        for i in range(1, len(data)):
            current_bar = data.iloc[i]
            lookback_data = data.iloc[:i+1]

            signal = strategy.generate_signal(lookback_data.copy(), symbol)

            if open_position is None and signal in [Signal.BUY, Signal.SELL]:
                open_position = self._enter_position(
                    current_bar, signal, symbol, risk_manager, lookback_data
                )

            elif open_position is not None:
                closed = self._check_exit(open_position, current_bar)

                if closed:
                    self.trades.append(open_position)
                    self.equity += open_position.profit
                    self.equity_history.append(self.equity)
                    open_position = None

            self.equity_history.append(self.equity)

        if open_position is not None:
            self._close_position_at_current_price(open_position, data.iloc[-1])
            self.trades.append(open_position)

        logger.info(f"Backtest complete: {len(self.trades)} trades, Equity: ${self.equity:.2f}")

        return BacktestMetrics(self.trades, self.initial_equity)

    def _enter_position(
        self, bar, signal: Signal, symbol: str, risk_manager, lookback_data: pd.DataFrame
    ) -> Trade:
        """Calculate position size and enter trade"""
        current_price = bar["close"]

        atr = self._calculate_atr(lookback_data)
        position_size = risk_manager.calculate_position_size(
            account_equity=self.equity,
            symbol=symbol,
            signal=signal,
            current_price=current_price,
        )

        if position_size <= 0:
            return None

        entry_price = current_price + (self.slippage_pips * 0.0001) if signal == Signal.BUY else current_price - (
            self.slippage_pips * 0.0001
        )

        stop_loss = risk_manager.calculate_stop_loss(entry_price, atr, signal)
        take_profit = risk_manager.calculate_take_profit(entry_price, atr, signal)

        trade = Trade(
            ticket=len(self.trades) + 1,
            symbol=symbol,
            trade_type=signal.value,
            volume=position_size,
            entry_price=entry_price,
            entry_time=bar.name if isinstance(bar.name, datetime) else datetime.now(),
        )
        trade.stop_loss = stop_loss
        trade.take_profit = take_profit

        logger.debug(f"Entered {signal.value} at {entry_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")

        return trade

    def _check_exit(self, trade: Trade, current_bar) -> bool:
        """Check if position should be closed"""
        high = current_bar["high"]
        low = current_bar["low"]

        if trade.trade_type == "BUY":
            if high >= trade.take_profit:
                exit_price = trade.take_profit
                exit_reason = "TakeProfit"
            elif low <= trade.stop_loss:
                exit_price = trade.stop_loss
                exit_reason = "StopLoss"
            else:
                return False
        else:
            if low <= trade.take_profit:
                exit_price = trade.take_profit
                exit_reason = "TakeProfit"
            elif high >= trade.stop_loss:
                exit_price = trade.stop_loss
                exit_reason = "StopLoss"
            else:
                return False

        self._close_position(trade, exit_price, current_bar.name, exit_reason)
        return True

    def _close_position(self, trade: Trade, exit_price: float, exit_time, reason: str = "Manual"):
        """Close a position and update equity"""
        commission = trade.entry_price * trade.volume * self.commission

        if trade.trade_type == "BUY":
            profit = (exit_price - trade.entry_price) * trade.volume - commission
        else:
            profit = (trade.entry_price - exit_price) * trade.volume - commission

        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.profit = profit

        logger.debug(f"Closed {trade.trade_type} at {exit_price:.5f}, P&L: ${profit:.2f} ({reason})")

    def _close_position_at_current_price(self, trade: Trade, last_bar):
        """Close remaining position at market close"""
        exit_price = last_bar["close"]
        self._close_position(trade, exit_price, last_bar.name, "Market Close")

    @staticmethod
    def _calculate_atr(data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(data) < period:
            return 0

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

        return np.mean(tr[-period:])

    def get_equity_curve(self) -> pd.Series:
        """Return equity curve as time series"""
        return pd.Series(self.equity_history)

    def save_results(self, filepath: str, metrics: BacktestMetrics):
        """Save backtest results to file"""
        import json

        results = {
            "metrics": metrics.summary(),
            "trades": [t.to_dict() for t in self.trades],
            "equity_history": [float(e) for e in self.equity_history],
        }

        with open(filepath, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Results saved to {filepath}")
