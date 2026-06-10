#!/usr/bin/env python3
"""
EA Trading Bot - Main Entry Point

This script initializes and runs the Expert Advisor trading system.
"""

import json
import logging
import sys
from pathlib import Path

from src.mt5_connector import MT5Connector
from src.core_engine import CoreEngine
from src.strategies import TrendFollowingStrategy, MeanReversionStrategy
from src.regime_detector import AdaptiveRegimeDetector
from src.risk_management import InstitutionalRiskManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/ea_trading.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def load_config(config_file: str = "config/settings.json") -> dict:
    """Load configuration from JSON file"""
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        logger.info(f"Configuration loaded from {config_file}")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file {config_file} not found")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {config_file}")
        sys.exit(1)


def initialize_mt5(config: dict) -> MT5Connector:
    """Initialize MT5 connection"""
    mt5_config = config["mt5"]
    mt5 = MT5Connector(
        account=mt5_config["account"],
        password=mt5_config["password"],
        server=mt5_config["server"],
    )

    if not mt5.connect():
        logger.error(f"Failed to connect to MT5: {mt5.last_error}")
        sys.exit(1)

    logger.info("MT5 connection established")
    return mt5


def initialize_engine(mt5: MT5Connector, config: dict) -> CoreEngine:
    """Initialize trading engine with strategies and managers"""
    engine = CoreEngine(mt5, config)

    # Register strategies
    trend_params = config["strategies"].get("TrendFollowing", {})
    engine.register_strategy("TrendFollowing", TrendFollowingStrategy(trend_params))

    mean_rev_params = config["strategies"].get("MeanReversion", {})
    engine.register_strategy("MeanReversion", MeanReversionStrategy(mean_rev_params))

    logger.info("Strategies registered")

    # Set risk manager
    risk_config = config.get("risk", {})
    engine.set_risk_manager(InstitutionalRiskManager(risk_config))
    logger.info("Risk manager initialized")

    # Set regime detector
    regime_config = config.get("regime_detector", {})
    engine.set_regime_detector(AdaptiveRegimeDetector(regime_config))
    logger.info("Regime detector initialized")

    return engine


def main():
    """Main execution function"""
    logger.info("=" * 50)
    logger.info("EA Trading Bot Started")
    logger.info("=" * 50)

    config = load_config()

    mt5 = initialize_mt5(config)

    engine = initialize_engine(mt5, config)

    symbols = config["trading"]["symbols"]
    process_interval = config["trading"]["process_interval"]

    logger.info(f"Trading {len(symbols)} symbols: {', '.join(symbols)}")
    logger.info(f"Process interval: {process_interval}s")

    try:
        engine.run(symbols, process_interval=process_interval)

    except KeyboardInterrupt:
        logger.info("Trading interrupted by user")

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

    finally:
        engine.stop()

        stats = engine.get_stats()
        logger.info(f"Final Statistics: {stats}")

        trade_journal_file = config["monitoring"]["trade_journal_file"]
        engine.save_trade_journal(trade_journal_file)

        mt5.disconnect()

        logger.info("=" * 50)
        logger.info("EA Trading Bot Stopped")
        logger.info("=" * 50)


if __name__ == "__main__":
    main()
