# EA Trading Bot - MetaTrader 5 Expert Advisor Framework
__version__ = "0.1.0"
__author__ = "EA Development Team"

# Lazy imports to avoid requiring MT5 when just backtesting
def __getattr__(name):
    if name == "MT5Connector":
        from src.mt5_connector import MT5Connector
        return MT5Connector
    elif name == "CoreEngine":
        from src.core_engine import CoreEngine
        return CoreEngine
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["MT5Connector", "CoreEngine"]
