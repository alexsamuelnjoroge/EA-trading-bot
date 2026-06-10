import logging
import pandas as pd
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from enum import Enum
import json

logger = logging.getLogger(__name__)


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"
    HOLD = "HOLD"


class Trade:
    def __init__(self, ticket: int, symbol: str, trade_type: str, volume: float, entry_price: float, entry_time: datetime):
        self.ticket = ticket
        self.symbol = symbol
        self.trade_type = trade_type
        self.volume = volume
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.exit_price = None
        self.exit_time = None
        self.profit = None
        self.stop_loss = None
        self.take_profit = None
        self.strategy_used = None
        self.regime = None

    def close(self, exit_price: float, exit_time: datetime):
        self.exit_price = exit_price
        self.exit_time = exit_time
        if self.trade_type == "BUY":
            self.profit = (exit_price - self.entry_price) * self.volume
        else:
            self.profit = (self.entry_price - exit_price) * self.volume

    def to_dict(self) -> Dict:
        return {
            "ticket": self.ticket,
            "symbol": self.symbol,
            "type": self.trade_type,
            "volume": self.volume,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat(),
            "exit_price": self.exit_price,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "profit": self.profit,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "strategy_used": self.strategy_used,
            "regime": self.regime,
        }


class CoreEngine:
    def __init__(self, mt5_connector, config: Dict):
        self.mt5 = mt5_connector
        self.config = config
        self.running = False
        self.strategies: Dict[str, 'Strategy'] = {}
        self.risk_manager = None
        self.regime_detector = None
        self.trade_journal: List[Trade] = []
        self.open_trades: Dict[int, Trade] = {}
        self.symbol_data: Dict[str, pd.DataFrame] = {}
        self.signal_callbacks: List[Callable] = []

    def register_strategy(self, name: str, strategy: 'Strategy'):
        self.strategies[name] = strategy
        logger.info(f"Strategy registered: {name}")

    def set_risk_manager(self, risk_manager: 'RiskManager'):
        self.risk_manager = risk_manager
        logger.info("Risk manager set")

    def set_regime_detector(self, regime_detector: 'RegimeDetector'):
        self.regime_detector = regime_detector
        logger.info("Regime detector set")

    def add_signal_callback(self, callback: Callable):
        self.signal_callbacks.append(callback)

    def update_market_data(self, symbol: str, timeframe: str = "H1", count: int = 100) -> bool:
        try:
            rates = self.mt5.get_rates(symbol, timeframe, count)

            if rates is None:
                logger.warning(f"Failed to get rates for {symbol}")
                return False

            self.symbol_data[symbol] = rates
            return True

        except Exception as e:
            logger.error(f"Error updating market data for {symbol}: {e}")
            return False

    def evaluate_signals(self, symbol: str) -> Dict[str, 'Signal']:
        if symbol not in self.symbol_data:
            logger.warning(f"No data for {symbol}")
            return {}

        data = self.symbol_data[symbol]
        signals = {}

        for strategy_name, strategy in self.strategies.items():
            try:
                signal = strategy.generate_signal(data, symbol)
                signals[strategy_name] = signal
            except Exception as e:
                logger.error(f"Error evaluating {strategy_name}: {e}")
                signals[strategy_name] = Signal.HOLD

        return signals

    def detect_market_regime(self, symbol: str) -> Optional[str]:
        if not self.regime_detector or symbol not in self.symbol_data:
            return None

        try:
            data = self.symbol_data[symbol]
            regime = self.regime_detector.detect(data, symbol)
            return regime
        except Exception as e:
            logger.error(f"Error detecting regime for {symbol}: {e}")
            return None

    def calculate_position_size(self, symbol: str, signal: Signal) -> Optional[float]:
        if not self.risk_manager:
            logger.warning("Risk manager not set")
            return None

        try:
            account_info = self.mt5.get_account_info()
            symbol_info = self.mt5.get_symbol_info(symbol)

            if not symbol_info:
                return None

            position_size = self.risk_manager.calculate_position_size(
                account_equity=account_info["equity"],
                symbol=symbol,
                signal=signal,
                current_price=symbol_info["ask"] if signal == Signal.BUY else symbol_info["bid"]
            )

            return position_size

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return None

    def on_signal(self, symbol: str, signals: Dict[str, Signal], regime: Optional[str]):
        for callback in self.signal_callbacks:
            try:
                callback({
                    "symbol": symbol,
                    "signals": {k: v.value for k, v in signals.items()},
                    "regime": regime,
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.error(f"Error in signal callback: {e}")

    def process_symbol(self, symbol: str):
        logger.info(f"Processing {symbol}")

        if not self.update_market_data(symbol):
            logger.warning(f"Failed to update data for {symbol}")
            return

        signals = self.evaluate_signals(symbol)
        regime = self.detect_market_regime(symbol)

        self.on_signal(symbol, signals, regime)

        consensus_signal = self.aggregate_signals(signals)

        if consensus_signal == Signal.BUY:
            self.execute_buy(symbol, regime)
        elif consensus_signal == Signal.SELL:
            self.execute_sell(symbol, regime)

    def aggregate_signals(self, signals: Dict[str, Signal]) -> Signal:
        if not signals:
            return Signal.HOLD

        buy_count = sum(1 for s in signals.values() if s == Signal.BUY)
        sell_count = sum(1 for s in signals.values() if s == Signal.SELL)

        if buy_count > len(signals) / 2:
            return Signal.BUY
        elif sell_count > len(signals) / 2:
            return Signal.SELL

        return Signal.HOLD

    def execute_buy(self, symbol: str, regime: Optional[str]):
        logger.info(f"Executing BUY for {symbol}")

        position_size = self.calculate_position_size(symbol, Signal.BUY)

        if position_size is None or position_size == 0:
            logger.warning(f"Invalid position size for {symbol}")
            return

        try:
            symbol_info = self.mt5.get_symbol_info(symbol)
            entry_price = symbol_info["ask"]

            ticket = self.mt5.place_order(
                symbol=symbol,
                order_type="BUY",
                volume=position_size,
                price=entry_price,
                comment=f"Buy signal from regime: {regime}"
            )

            if ticket:
                trade = Trade(
                    ticket=ticket,
                    symbol=symbol,
                    trade_type="BUY",
                    volume=position_size,
                    entry_price=entry_price,
                    entry_time=datetime.now()
                )
                trade.regime = regime
                self.open_trades[ticket] = trade
                logger.info(f"BUY order executed: {symbol} {position_size} @ {entry_price}")

        except Exception as e:
            logger.error(f"Error executing BUY: {e}")

    def execute_sell(self, symbol: str, regime: Optional[str]):
        logger.info(f"Executing SELL for {symbol}")

        positions = self.mt5.get_open_positions(symbol)

        for position in positions:
            if position["type"] == "BUY":
                try:
                    closed = self.mt5.close_position(symbol, position["volume"])

                    if closed and position["ticket"] in self.open_trades:
                        trade = self.open_trades.pop(position["ticket"])
                        trade.close(position["current_price"], datetime.now())
                        self.trade_journal.append(trade)
                        logger.info(f"SELL executed: {symbol} P&L: {trade.profit}")

                except Exception as e:
                    logger.error(f"Error executing SELL: {e}")

    def run(self, symbols: List[str], process_interval: int = 60):
        if not self.mt5.connected:
            logger.error("MT5 not connected")
            return

        self.running = True
        logger.info(f"Engine started. Processing {len(symbols)} symbols every {process_interval}s")

        try:
            while self.running:
                for symbol in symbols:
                    self.process_symbol(symbol)

                import time
                time.sleep(process_interval)

        except KeyboardInterrupt:
            logger.info("Engine stopped by user")
        except Exception as e:
            logger.error(f"Engine error: {e}")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        logger.info(f"Engine stopped. Processed {len(self.trade_journal)} trades")

    def get_stats(self) -> Dict:
        if not self.trade_journal:
            return {"total_trades": 0}

        profits = [t.profit for t in self.trade_journal if t.profit is not None]
        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p < 0]

        return {
            "total_trades": len(self.trade_journal),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(self.trade_journal) if self.trade_journal else 0,
            "total_profit": sum(profits),
            "avg_profit": sum(profits) / len(profits) if profits else 0,
            "max_profit": max(profits) if profits else 0,
            "max_loss": min(profits) if profits else 0,
        }

    def save_trade_journal(self, filepath: str):
        trades_data = [t.to_dict() for t in self.trade_journal]

        with open(filepath, "w") as f:
            json.dump(trades_data, f, indent=2)

        logger.info(f"Trade journal saved to {filepath}")


class Strategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        pass


class RiskManager(ABC):
    @abstractmethod
    def calculate_position_size(self, account_equity: float, symbol: str, signal: Signal, current_price: float) -> float:
        pass


class RegimeDetector(ABC):
    @abstractmethod
    def detect(self, data: pd.DataFrame, symbol: str) -> str:
        pass
