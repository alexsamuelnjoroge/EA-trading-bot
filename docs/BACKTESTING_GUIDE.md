# Backtesting Guide

This guide explains the backtesting framework and how to validate strategies before going live.

## Why Backtesting Matters

**The Problem:** Most traders think "my strategy looks good in my head" but then lose money when they actually trade it. Why?

- Emotional decisions
- Parameter over-optimization (curve-fitting)
- Survivorship bias
- Randomness vs. edge

**The Solution:** Rigorous backtesting on historical data to prove the strategy works statistically.

## What We'll Test

### 1. **Simple Backtest**
Replays historical prices, executes trades, measures profit/loss.

```
Real Price History: 1.0850 → 1.0860 → 1.0855
│
├─ BUY Signal at 1.0850
├─ Price moves to 1.0860 (profit)
├─ SELL Signal triggers
└─ Exit at 1.0860 = +$100 profit
```

### 2. **Walk-Forward Analysis**
Tests on data the strategy never saw before (prevents luck).

```
5 Years of Data
├─ Period 1: Train on 2014-2016, Test on 2016-2017
├─ Period 2: Train on 2016-2017, Test on 2017-2018
├─ Period 3: Train on 2017-2018, Test on 2018-2019
└─ Period 4: Train on 2018-2019, Test on 2019-2020

Average Results = Real Expected Performance
```

### 3. **Monte Carlo Simulation**
Shuffles trades 1,000 times to test robustness.

```
If you got 100 winning trades and 50 losing trades...
│
├─ Simulation 1: [WIN, LOSS, WIN, WIN, LOSS, ...]
├─ Simulation 2: [WIN, WIN, WIN, LOSS, WIN, ...]
├─ Simulation 3: [LOSS, WIN, WIN, WIN, LOSS, ...]
└─ ...
│
Result: "Strategy works 95% of the time, regardless of order"
```

## Key Metrics Explained

### **Win Rate: 55%+**
Out of 100 trades, 55+ are profitable. (Sounds low but is actually good!)

```
100 trades
├─ 55 winners
└─ 45 losers
```

### **Profit Factor: 1.5+**
Total wins / Total losses. You win $150 for every $100 you lose.

```
Total Profit: $15,000
Total Loss: $10,000
Profit Factor: 15,000 / 10,000 = 1.5 ✅
```

### **Sharpe Ratio: 1.0+**
Risk-adjusted returns. How many units of return per unit of risk.

```
Sharpe = 2.0: Excellent (2x return per unit of risk)
Sharpe = 1.0: Good (1x return per unit of risk)
Sharpe = 0.5: Okay
Sharpe = <0: Losing strategy
```

### **Max Drawdown: <20%**
Worst losing period. If you started with $10,000, worst you'd be is $8,000.

```
Account: $10,000
  ↓ (losses)
$8,500 (15% drawdown)
  ↑ (recovery)
$10,500 ✓
```

## How to Run Backtests

### **Option 1: Use Generated Sample Data** (Easiest)

```bash
python backtest.py --symbol EURUSD --sample --days 1825
```

This generates 5 years of realistic fake data and tests both strategies.

**Output:**
- `data/results/EURUSD_TrendFollowing_backtest.json` - Trade list and metrics
- `data/results/EURUSD_MeanReversion_backtest.json` - Trade list and metrics
- `data/results/EURUSD_summary.json` - Overall results comparison
- `logs/backtest.log` - Detailed execution log

### **Option 2: Use Real MT5 Data** (When Ready)

```python
from src.mt5_connector import MT5Connector
from src.backtester import HistoricalDataFetcher
from datetime import datetime

# Connect to MT5
mt5 = MT5Connector(account=YOUR_ACCOUNT, password=YOUR_PASSWORD)
mt5.connect()

# Fetch historical data
fetcher = HistoricalDataFetcher()
data = fetcher.fetch_from_mt5(mt5, "EURUSD", timeframe="D1")

# Now run backtest.py or use BacktestEngine directly
```

### **Option 3: Custom Backtest Script**

```python
from src.backtester import BacktestEngine, HistoricalDataFetcher
from src.strategies import TrendFollowingStrategy
from src.risk_management import InstitutionalRiskManager

# Get data
data = HistoricalDataFetcher.generate_sample_data("EURUSD", days=1825)

# Setup
engine = BacktestEngine(initial_equity=10000)
strategy = TrendFollowingStrategy()
risk_manager = InstitutionalRiskManager()

# Run
metrics = engine.backtest(data, strategy, risk_manager, symbol="EURUSD")

# See results
print(metrics.summary())
```

## Interpreting Results

### Good Strategy
```
Win Rate: 58%
Profit Factor: 2.1
Sharpe Ratio: 1.8
Max Drawdown: 12%
Total Profit: $8,500 (+85% on $10K)
```
✅ Ready for demo account testing

### Weak Strategy
```
Win Rate: 48%
Profit Factor: 0.9
Sharpe Ratio: -0.2
Max Drawdown: 35%
Total Profit: -$2,100
```
❌ Needs improvement - maybe adjust parameters or modify signals

### Lucky but Fragile
```
Win Rate: 75%
Profit Factor: 3.2
Sharpe Ratio: 0.4
Max Drawdown: 48%
Total Profit: $12,000
```
⚠️ High win rate but high drawdown. Likely over-optimized. Walk-forward test will reveal true edge.

## Next Steps: Parameter Optimization

Once you have a baseline strategy, you can optimize parameters:

```python
from src.backtester import ParameterOptimizer

optimizer = ParameterOptimizer()

# Test different moving average periods
parameter_grid = {
    "fast_ma_period": [5, 10, 15, 20],
    "slow_ma_period": [20, 30, 40, 50],
    "adx_threshold": [20, 25, 30, 35],
}

best = optimizer.optimize(
    data,
    TrendFollowingStrategy,
    risk_manager,
    parameter_grid,
    metric="sharpe_ratio"  # or "profit_factor", "win_rate"
)

print(f"Best parameters: {best['best_params']}")
print(f"Best Sharpe Ratio: {best['best_score']:.2f}")
```

## Common Mistakes to Avoid

### ❌ "My strategy won 80% in backtest!"
**Problem:** Probably over-optimized. The specific parameters worked great on this specific data, but won't work on new data.

**Solution:** Use walk-forward analysis. If walk-forward results are much worse than backtest, parameters are over-fit.

### ❌ "Let me just tweak the parameters once more..."
**Problem:** Each tweak makes it fit the historical data better but worse on real data (curve-fitting death spiral).

**Solution:** Stick with original parameters. Only change if walk-forward analysis reveals systematic issues.

### ❌ "The backtest shows +300% return!"
**Problem:** Probably using unrealistic assumptions (no slippage, instant execution, no commissions).

**Solution:** Add realistic costs: 2 pips slippage, 0.002% commission, include bid-ask spreads.

### ❌ "I'll just trade live with this strategy"
**Problem:** Backtests can't capture market structure changes, gaps, black swans, or execution delays.

**Solution:** Always run demo account for 4+ weeks before live trading.

## Real Example

Let's say we backtest the Trend-Following strategy on 5 years of EURUSD data:

**Backtest Results:**
- Win Rate: 56%
- Sharpe Ratio: 1.2
- Max Drawdown: 18%
- Total Profit: $4,200 (42% on $10K)

**Walk-Forward Results:**
- Win Rate: 54% (close to backtest ✓)
- Sharpe Ratio: 1.1 (close to backtest ✓)
- Max Drawdown: 16% (close to backtest ✓)
- Total Profit: $3,800 (close to backtest ✓)

**Verdict:** ✅ **Strategy is robust.** Walk-forward results are similar to backtest results, so the edge is real, not just luck.

**Monte Carlo Results:**
- Probability of Profit: 94%
- Worst Case: $8,200
- Best Case: $15,300

**Verdict:** ✅ **Strategy is robust.** 94% of random trade orders still profit.

**Next Step:** Deploy to demo account for 4 weeks to validate in real market conditions.

---

## File Locations

After running a backtest:

```
data/results/
├── EURUSD_TrendFollowing_backtest.json        # All trades + metrics
├── EURUSD_TrendFollowing_walkforward.json     # Walk-forward results
├── EURUSD_TrendFollowing_montecarlo.json      # MC simulation results
├── EURUSD_MeanReversion_backtest.json
├── EURUSD_MeanReversion_walkforward.json
├── EURUSD_MeanReversion_montecarlo.json
└── EURUSD_summary.json                        # Overall comparison
```

Open these JSON files to see:
- Individual trades (entry price, exit price, P&L)
- Equity curve history
- Performance metrics
- Walk-forward period-by-period results

---

## Summary

**Backtesting = Risk-Free Validation**

1. **Backtest** - Prove strategy works on historical data
2. **Walk-Forward** - Ensure it's not just lucky
3. **Monte Carlo** - Verify robustness to trade order
4. **Analyze** - Calculate Sharpe, drawdown, etc.
5. **Optimize** - Find best parameters
6. **Demo Account** - Test in real market with fake money
7. **Live Trading** - Finally, put real money at risk

This framework lets you do all of this in minutes, not months.

---

**Ready to test? Run:**
```bash
python backtest.py --symbol EURUSD --sample
```
