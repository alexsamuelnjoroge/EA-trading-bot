import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class HistoricalDataFetcher:
    """Fetch and cache historical OHLC data for backtesting"""

    def __init__(self, cache_dir: str = "data/historical"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_from_mt5(
        self,
        mt5_connector,
        symbol: str,
        timeframe: str = "D1",
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> pd.DataFrame:
        """
        Fetch historical data from MT5

        Args:
            mt5_connector: MT5Connector instance
            symbol: Trading symbol
            timeframe: H1, D1, W1, MN1, etc.
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with OHLC data
        """
        if not mt5_connector.connected:
            logger.error("MT5 not connected")
            return None

        if start_date is None:
            start_date = datetime.now() - timedelta(days=365*5)

        if end_date is None:
            end_date = datetime.now()

        logger.info(f"Fetching {symbol} data from {start_date.date()} to {end_date.date()}")

        try:
            data = mt5_connector.get_rates(
                symbol=symbol,
                timeframe=timeframe,
                count=10000,
                start_time=start_date
            )

            if data is not None and len(data) > 0:
                data = data[data.index <= end_date]
                logger.info(f"Fetched {len(data)} bars for {symbol}")
                self._cache_data(symbol, timeframe, data)
                return data
            else:
                logger.warning(f"No data fetched for {symbol}")
                return None

        except Exception as e:
            logger.error(f"Error fetching data from MT5: {e}")
            return None

    def load_cached_data(self, symbol: str, timeframe: str = "D1") -> pd.DataFrame:
        """Load cached historical data"""
        cache_file = self.cache_dir / f"{symbol}_{timeframe}.csv"

        if cache_file.exists():
            try:
                data = pd.read_csv(cache_file, index_col="time", parse_dates=True)
                logger.info(f"Loaded cached data for {symbol}: {len(data)} bars")
                return data
            except Exception as e:
                logger.error(f"Error loading cached data: {e}")
                return None

        logger.warning(f"No cached data found for {symbol}_{timeframe}")
        return None

    def _cache_data(self, symbol: str, timeframe: str, data: pd.DataFrame):
        """Cache data to CSV file"""
        cache_file = self.cache_dir / f"{symbol}_{timeframe}.csv"

        try:
            data.to_csv(cache_file)
            logger.info(f"Cached data saved to {cache_file}")
        except Exception as e:
            logger.error(f"Error saving cached data: {e}")

    @staticmethod
    def generate_sample_data(
        symbol: str = "EURUSD",
        days: int = 1825,
        base_price: float = 1.0850,
        volatility: float = 0.008,
    ) -> pd.DataFrame:
        """
        Generate realistic synthetic OHLC data for testing

        Useful when real data isn't available yet.
        """
        logger.info(f"Generating {days} days of sample data for {symbol}")

        dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

        returns = np.random.normal(0.0005, volatility, days)
        prices = base_price * np.exp(np.cumsum(returns))

        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            daily_return = 0.001 if i % 5 == 0 else -0.0005
            close = price * (1 + daily_return)
            open_price = prices[i-1] if i > 0 else base_price
            high = max(open_price, close) * (1 + abs(np.random.normal(0, volatility)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, volatility)))

            data.append({
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "tick_volume": np.random.randint(1000, 100000),
                "real_volume": np.random.randint(500, 50000),
            })

        df = pd.DataFrame(data, index=dates)
        df.index.name = "time"

        logger.info(f"Generated sample data: {len(df)} bars, price range: {df['low'].min():.5f} - {df['high'].max():.5f}")

        return df


class DataValidator:
    """Validate historical data quality"""

    @staticmethod
    def validate(data: pd.DataFrame, symbol: str = "UNKNOWN") -> bool:
        """
        Check data for common issues

        Returns:
            True if data passes validation, False otherwise
        """
        if data is None or len(data) == 0:
            logger.error(f"{symbol}: Empty data")
            return False

        if len(data) < 100:
            logger.warning(f"{symbol}: Only {len(data)} bars (recommend 100+)")
            return False

        required_columns = ["open", "high", "low", "close"]
        if not all(col in data.columns for col in required_columns):
            logger.error(f"{symbol}: Missing OHLC columns")
            return False

        if (data["high"] < data["low"]).any():
            logger.error(f"{symbol}: High < Low found")
            return False

        if (data["close"] > data["high"]).any() or (data["close"] < data["low"]).any():
            logger.error(f"{symbol}: Close outside high-low range")
            return False

        if data.isnull().any().any():
            logger.warning(f"{symbol}: Null values found")
            return False

        if (data["high"] == data["low"]).sum() > len(data) * 0.1:
            logger.warning(f"{symbol}: >10% bars with no range")
            return False

        logger.info(f"{symbol}: Data validation passed - {len(data)} bars")
        return True
