import MetaTrader5 as mt5
import pandas as pd
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MT5ConnectionError(Exception):
    pass


class MT5Connector:
    def __init__(self, account: int, password: str, server: str = "MetaQuotes-Demo"):
        self.account = account
        self.password = password
        self.server = server
        self.connected = False
        self.last_error = None

    def connect(self) -> bool:
        try:
            if not mt5.initialize(login=self.account, password=self.password, server=self.server):
                self.last_error = f"MT5 init failed: {mt5.last_error()}"
                logger.error(self.last_error)
                return False

            self.connected = True
            logger.info(f"Connected to MT5 - Account: {self.account}, Server: {self.server}")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Connection error: {self.last_error}")
            return False

    def disconnect(self) -> bool:
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5")
            return True
        return False

    def get_account_info(self) -> Dict:
        if not self.connected:
            raise MT5ConnectionError("Not connected to MT5")

        info = mt5.account_info()
        return {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.free_margin,
            "margin_level": info.margin_level,
            "profit": info.profit,
            "currency": info.currency,
        }

    def get_symbol_info(self, symbol: str) -> Dict:
        if not self.connected:
            raise MT5ConnectionError("Not connected to MT5")

        info = mt5.symbol_info(symbol)
        if info is None:
            logger.warning(f"Symbol {symbol} not found")
            return {}

        return {
            "symbol": info.name,
            "bid": info.bid,
            "ask": info.ask,
            "spread": info.ask - info.bid,
            "point": info.point,
            "digits": info.digits,
            "volume": info.volume,
        }

    def get_rates(
        self,
        symbol: str,
        timeframe: str = "H1",
        count: int = 100,
        start_time: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        if not self.connected:
            raise MT5ConnectionError("Not connected to MT5")

        try:
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1,
                "W1": mt5.TIMEFRAME_W1,
                "MN1": mt5.TIMEFRAME_MN1,
            }

            if timeframe not in tf_map:
                logger.error(f"Invalid timeframe: {timeframe}")
                return None

            if start_time is None:
                rates = mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, count)
            else:
                rates = mt5.copy_rates_from(symbol, tf_map[timeframe], start_time, count)

            if rates is None or len(rates) == 0:
                logger.warning(f"No rates found for {symbol} {timeframe}")
                return None

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df.set_index("time", inplace=True)

            return df[["open", "high", "low", "close", "tick_volume", "real_volume"]]

        except Exception as e:
            logger.error(f"Error getting rates: {e}")
            return None

    def place_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: str = ""
    ) -> Optional[int]:
        if not self.connected:
            raise MT5ConnectionError("Not connected to MT5")

        try:
            type_map = {
                "BUY": mt5.ORDER_TYPE_BUY,
                "SELL": mt5.ORDER_TYPE_SELL,
                "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
                "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
                "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP,
                "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP,
            }

            if order_type not in type_map:
                logger.error(f"Invalid order type: {order_type}")
                return None

            if price is None:
                symbol_info = mt5.symbol_info(symbol)
                price = symbol_info.ask if order_type in ["BUY", "BUY_LIMIT", "BUY_STOP"] else symbol_info.bid

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": type_map[order_type],
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
            }

            result = mt5.order_send(request)

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Order placed: {symbol} {order_type} {volume} @ {price}")
                return result.order
            else:
                self.last_error = f"Order failed: {result.comment} (code: {result.retcode})"
                logger.error(self.last_error)
                return None

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def close_position(self, symbol: str, volume: Optional[float] = None) -> bool:
        if not self.connected:
            raise MT5ConnectionError("Not connected to MT5")

        try:
            positions = mt5.positions_get(symbol=symbol)

            if not positions:
                logger.warning(f"No open position for {symbol}")
                return False

            position = positions[0]
            close_volume = volume if volume else position.volume

            order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            symbol_info = mt5.symbol_info(symbol)
            price = symbol_info.ask if order_type == mt5.ORDER_TYPE_BUY else symbol_info.bid

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": close_volume,
                "type": order_type,
                "price": price,
                "position": position.ticket,
                "comment": "Close position",
                "type_time": mt5.ORDER_TIME_GTC,
            }

            result = mt5.order_send(request)

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Position closed: {symbol} {close_volume}")
                return True
            else:
                logger.error(f"Close failed: {result.comment}")
                return False

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False

    def modify_position(
        self,
        ticket: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> bool:
        if not self.connected:
            raise MT5ConnectionError("Not connected to MT5")

        try:
            position = mt5.positions_get(ticket=ticket)

            if not position:
                logger.warning(f"Position {ticket} not found")
                return False

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "sl": stop_loss,
                "tp": take_profit,
            }

            result = mt5.order_send(request)

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Position {ticket} modified")
                return True
            else:
                logger.error(f"Modify failed: {result.comment}")
                return False

        except Exception as e:
            logger.error(f"Error modifying position: {e}")
            return False

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        if not self.connected:
            raise MT5ConnectionError("Not connected to MT5")

        try:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()

            result = []
            for pos in positions:
                result.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": pos.volume,
                    "open_price": pos.price_open,
                    "current_price": pos.price_current,
                    "profit": pos.profit,
                    "stop_loss": pos.sl,
                    "take_profit": pos.tp,
                })

            return result

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def wait_for_order_completion(self, order_ticket: int, timeout: int = 30) -> bool:
        start_time = time.time()

        while time.time() - start_time < timeout:
            orders = mt5.orders_get(ticket=order_ticket)

            if not orders or len(orders) == 0:
                return True

            time.sleep(0.1)

        logger.warning(f"Order {order_ticket} did not complete within {timeout} seconds")
        return False
