# EA Trading Bot - MetaTrader 5 Expert Advisor Framework

A professional-grade MetaTrader 5 Expert Advisor framework built with Python, featuring institutional-grade risk management, adaptive multi-strategy architecture, and advanced backtesting capabilities.

## Features

### Core Architecture
- **Modular Design**: Plug-and-play strategies, indicators, and risk managers
- **Adaptive Multi-Strategy**: Automatic market regime detection and strategy selection
- **Institutional Risk Management**: Kelly Criterion, volatility-adjusted sizing, correlation tracking
- **Professional Backtesting**: Walk-forward analysis, Monte Carlo simulation, bootstrap resampling

### Trading Capabilities
- **Multiple Asset Classes**: Forex, Stocks, Cryptocurrencies, Commodities
- **Real-time Monitoring**: Trade journal, equity curves, performance metrics
- **Signal Generation**: Technical analysis based strategy engine
- **Risk Controls**: Daily loss limits, maximum drawdown enforcement, leverage limits

### Included Strategies
- **Trend Following**: MA crossover with ADX confirmation
- **Mean Reversion**: Bollinger Bands + RSI combo
- **Volatility-Based**: Regime-aware position sizing

## Project Structure

```
ea-trading-bot/
├── src/
│   ├── mt5_connector.py          # MT5 API wrapper
│   ├── core_engine.py             # Main trading engine & event loop
│   ├── regime_detector.py          # Market regime detection
│   ├── strategies/                 # Strategy implementations
│   │   └── __init__.py             # TrendFollowing, MeanReversion strategies
│   ├── risk_management/            # Risk management system
│   │   └── __init__.py             # InstitutionalRiskManager, VolatilityAdjustedRiskManager
│   ├── backtester/                 # Backtesting framework (Phase 4)
│   ├── monitoring/                 # Trade journal & dashboard (Phase 5)
│   └── config/                     # Configuration files
├── tests/                          # Unit tests
├── data/
│   ├── historical/                 # Historical market data
│   └── results/                    # Backtest results
├── docs/                           # Documentation
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Quick Start

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure MT5 Connection

Create `config/settings.json`:

```json
{
    "mt5": {
        "account": 123456789,
        "password": "your_password",
        "server": "MetaQuotes-Demo"
    },
    "trading": {
        "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
        "timeframe": "H1",
        "process_interval": 60
    },
    "risk": {
        "daily_loss_limit": -500,
        "max_drawdown": 0.20,
        "risk_per_trade": 0.02,
        "kelly_factor": 0.25
    }
}
```

### 3. Run the EA

```python
from src.mt5_connector import MT5Connector
from src.core_engine import CoreEngine
from src.strategies import TrendFollowingStrategy, MeanReversionStrategy
from src.regime_detector import MarketRegimeDetector
from src.risk_management import InstitutionalRiskManager
import json

# Load config
with open('config/settings.json') as f:
    config = json.load(f)

# Initialize MT5
mt5 = MT5Connector(
    account=config['mt5']['account'],
    password=config['mt5']['password'],
    server=config['mt5']['server']
)

if not mt5.connect():
    print(f"Connection failed: {mt5.last_error}")
    exit(1)

# Create engine
engine = CoreEngine(mt5, config)

# Register strategies
engine.register_strategy("TrendFollowing", TrendFollowingStrategy())
engine.register_strategy("MeanReversion", MeanReversionStrategy())

# Set risk management
engine.set_risk_manager(InstitutionalRiskManager(config['risk']))
engine.set_regime_detector(MarketRegimeDetector())

# Run
symbols = config['trading']['symbols']
engine.run(symbols, process_interval=config['trading']['process_interval'])

# Save results
engine.save_trade_journal('results/trades.json')
print(engine.get_stats())
```

## Development Phases

### Phase 1: Foundation & Core Engine ✅
- MT5 Connector with API communication
- Core event engine and main loop
- Data infrastructure (OHLC, indicators)
- Basic risk manager

### Phase 2: Strategies & Regime Detection ✅
- Market regime detector
- Strategy framework
- Trend-following strategy
- Mean-reversion strategy

### Phase 3: Institutional Risk Management ✅
- Advanced position sizing (Kelly Criterion)
- Multi-level risk controls
- Smart stop-loss/take-profit logic

### Phase 4: Advanced Backtesting (In Progress)
- Historical data replay with slippage
- Walk-forward analysis
- Monte Carlo resampling
- Performance metrics

### Phase 5: Monitoring & Dashboard (Pending)
- Real-time trade journal
- Web dashboard
- Email/SMS alerts
- Performance analytics

### Phase 6: Integration & Testing (Pending)
- End-to-end testing
- Configuration system
- Documentation
- Demo account testing

### Phase 7: Continuous Improvement (Pending)
- Performance monitoring
- Strategy expansion
- Advanced features (ML, options, etc.)

## Key Components Explained

### MT5Connector
Wrapper around MetaTrader5 API providing:
- Connection/disconnection management
- Market data retrieval (OHLC rates)
- Order placement and management
- Position tracking
- Account information

### CoreEngine
Main orchestrator that:
- Manages trading lifecycle
- Evaluates multiple strategies simultaneously
- Aggregates signals
- Executes trades based on signals
- Maintains trade journal

### Strategies
Base class with two implementations:
- **TrendFollowingStrategy**: MA crossover + ADX confirmation
- **MeanReversionStrategy**: Bollinger Bands + RSI

### RegimeDetector
Identifies market conditions:
- **Volatility Classification**: High/Low
- **Trend Identification**: Strong/Weak/Ranging
- **Momentum Detection**: Up/Down/Neutral

### RiskManager
Institutional-grade controls:
- **Position Sizing**: Kelly Criterion, volatility-adjusted
- **Stop-Loss/Take-Profit**: ATR-based
- **Daily Loss Limits**: Circuit breaker functionality
- **Maximum Drawdown**: Equity protection

## Performance Metrics

The EA tracks:
- Win Rate: % of profitable trades
- Profit Factor: Total wins / Total losses
- Sharpe Ratio: Risk-adjusted returns
- Maximum Drawdown: Largest peak-to-valley decline
- Calmar Ratio: Return / Maximum Drawdown

## Configuration

### Risk Settings
- `daily_loss_limit`: Stop trading after this daily loss
- `max_drawdown`: Maximum equity drawdown allowed
- `risk_per_trade`: % of equity risked per trade
- `kelly_factor`: Conservative Kelly Criterion multiplier

### Strategy Settings
Each strategy has configurable parameters:
- **Trend Following**: MA periods, ADX thresholds
- **Mean Reversion**: BB periods, RSI levels

### Market Settings
- `symbols`: Which instruments to trade
- `timeframe`: H1, D1, etc.
- `process_interval`: How often to check for signals (seconds)

## Testing

Run unit tests:

```bash
pytest tests/
pytest tests/ --cov=src --cov-report=html
```

## Security Considerations

- Store credentials securely (use `.env` file, never commit passwords)
- Validate all external inputs
- Use demo accounts for initial testing
- Monitor all live trading activity
- Implement circuit breakers for extreme losses

## Next Steps

1. **Backtest Historical Data**: Validate strategy performance before live trading
2. **Optimize Parameters**: Use walk-forward optimization to find best settings
3. **Demo Account Testing**: Run on demo for 4+ weeks to verify profitability
4. **Risk Assessment**: Stress test under extreme market conditions
5. **Live Deployment**: Start with small position sizes, scale gradually

## Troubleshooting

### Connection Issues
```
MT5 init failed: Check MT5 is running and credentials are correct
```

### No Market Data
```
No rates found for EURUSD - Symbol may not exist or have no data
```

### Position Size = 0
```
Invalid position size - Check account equity and risk parameters
```

## Resources

- [MetaTrader5 Python Documentation](https://www.mql5.com/en/docs/integration/python_metatrader5)
- [Technical Analysis Guide](https://en.wikipedia.org/wiki/Technical_analysis)
- [Kelly Criterion](https://en.wikipedia.org/wiki/Kelly_criterion)
- [Risk Management](https://www.investopedia.com/articles/trading/09/money-management.asp)

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or feature requests, please open an issue on the project repository.
