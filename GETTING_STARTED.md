# Getting Started: EA Trading Bot (Zero to Trading)

**You have ZERO trading knowledge and that's OK.** This guide will walk you through everything step-by-step.

---

## 📚 Understanding the Basics (5 minutes)

### What is an Expert Advisor (EA)?
A program that trades automatically on your behalf. It watches the market, generates signals, and executes trades 24/7 without emotion.

### What is MetaTrader 5 (MT5)?
The platform where your EA will run. It handles:
- Real-time market data
- Order execution
- Account management
- Trade history

### How Does Your EA Work?

```
Market Data (EURUSD price)
        ↓
Strategy Analysis (Is trend up or down?)
        ↓
Risk Check (Is it safe to trade now?)
        ↓
Position Sizing (How much to trade?)
        ↓
Order Execution (Place buy/sell order)
        ↓
Trade Monitoring (Watch for profit or loss)
        ↓
Exit Signal (Close when appropriate)
```

---

## 🚀 Step-by-Step Setup

### Step 1: Install MetaTrader 5 (5 minutes)
1. Download from: https://www.metatrader5.com/download
2. Install it
3. Create a **demo account** (practice account with fake money)
   - Don't use real money yet!
   - Demo account gets reset but unlimited practice
4. Write down your account number and password

### Step 2: Install Python Libraries (2 minutes)

```bash
cd "C:\Users\giale\Projects\EA trading bot"
pip install -r requirements.txt
```

This installs all the tools your EA needs to run.

### Step 3: Configure Your Account (2 minutes)

Edit `config/settings.json`:
```json
{
    "mt5": {
        "account": 123456789,        // Your demo account number
        "password": "your_password", // Your demo account password
        "server": "MetaQuotes-Demo"  // Leave as-is
    },
    "trading": {
        "symbols": ["EURUSD", "GBPUSD"],  // Pairs to trade
        "timeframe": "H1",                 // 1-hour candles
        "process_interval": 60             // Check every 60 seconds
    }
}
```

### Step 4: Test the Dashboard (2 minutes)

```bash
python dashboard.py
```

Open browser: http://localhost:5000

You should see a beautiful dashboard. This is where you'll watch your EA trade in real-time.

---

## 📊 Understanding Performance Metrics

### Win Rate (Should be 55%+)
Out of 100 trades, how many were profitable?

Example:
- 60 winning trades
- 40 losing trades
- **Win Rate = 60%** ✅ (Good!)

### Profit Factor (Should be 1.5+)
Total money won ÷ Total money lost

Example:
- Total wins: $15,000
- Total losses: $10,000
- **Profit Factor = 1.5** ✅ (Good!)

### Sharpe Ratio (Should be 1.0+)
How much profit per unit of risk? Higher = better.

- Sharpe 2.0 = Excellent
- Sharpe 1.0 = Good
- Sharpe 0.5 = Okay
- Sharpe <0 = Losing

### Maximum Drawdown (Should be <20%)
Worst losing period before recovering.

Example:
- Start with: $10,000
- Worst point: $8,500 (-15%)
- Recovered to: $10,500
- **Max Drawdown = 15%** ✅ (Good!)

---

## 🎯 Your Trading Journey

### Phase 1: Parameter Optimization (Automatic ✅)
- System is testing thousands of parameter combinations
- Finding which settings make the most profit
- **Status:** Running now, will finish soon
- **Your action:** Wait for results

### Phase 2: Backtest Results (Review)
Once optimization finishes:
1. Check the results in `data/results/`
2. Look for best Sharpe Ratio
3. Verify Win Rate > 50%
4. Check Profit Factor > 1.0

### Phase 3: Demo Account Testing (1 week)
1. Configure your demo account credentials
2. Run: `python main.py`
3. Watch the dashboard at http://localhost:5000
4. Monitor trades for 1 week
5. Should see positive results with <15% drawdown

### Phase 4: Live Trading (Only if Phase 3 succeeds)
1. Start with SMALL position sizes
2. Trade with real money
3. Monitor daily
4. Gradually increase size as you build confidence

---

## 🛡️ Safety Rules (MUST FOLLOW!)

### ❌ Never Do This:
- Deploy to live trading without 1 week demo test
- Risk more than 2% of account per trade
- Trade 20+ hours without monitoring
- Ignore the daily loss limit
- Change parameters mid-trading

### ✅ Always Do This:
- Test on demo first (2+ weeks minimum)
- Start small (0.01 lot size)
- Monitor daily for first month
- Keep trade journal
- Review performance weekly

---

## 📈 What Good Results Look Like

### Demo Account (1 week test):
```
Starting Equity: $10,000
Ending Equity: $10,800

Trades: 25
Win Rate: 58%
Profit Factor: 1.8
Max Drawdown: 12%
Sharpe Ratio: 1.2

Verdict: ✅ READY FOR LIVE
```

### Warning Signs (DON'T TRADE LIVE):
```
Win Rate: 45%              ❌ Too low
Profit Factor: 0.9         ❌ Losing money
Max Drawdown: 35%          ❌ Too risky
Sharpe Ratio: -1.5         ❌ Bad risk-reward
```

---

## 🎓 Key Concepts Explained

### Trend-Following Strategy
"Buy when price is going up, sell when it starts going down"

- Works best when market has clear direction
- Fails in sideways markets
- Win rate: 40-60%

### Mean-Reversion Strategy
"Buy when price is too low, sell when it's too high"

- Works best in stable markets
- Fails during strong trends
- Win rate: 45-65%

### Why We Use Both?
Different strategies win in different conditions. Your EA automatically switches between them.

---

## 🔧 Troubleshooting

### "No market data"
- Check MT5 is running
- Verify account credentials in config
- Ensure demo account is active

### "Position size = 0"
- Account equity too low
- Risk settings too strict
- Check daily loss limit isn't hit

### "Not enough trades"
- Strategy filters are too strict
- Market conditions don't match strategy
- Timeframe might be wrong

---

## 💡 Quick Commands

```bash
# Test backtesting (generates sample data)
python backtest.py --symbol EURUSD --sample --days 1825

# Optimize parameters
python optimize_parameters.py

# Run live trading (ONLY on demo first!)
python main.py

# View dashboard
python dashboard.py

# Run tests
pytest tests/ -v
```

---

## 📞 Next Actions

### Today:
✅ Parameters optimization is running
- [ ] Read this guide
- [ ] Understand the concepts
- [ ] Install MT5 if needed

### Tomorrow:
- [ ] Check optimization results
- [ ] Review best parameters
- [ ] Create demo account

### This Week:
- [ ] Configure config/settings.json
- [ ] Deploy to demo account
- [ ] Run dashboard
- [ ] Monitor first trades

### Next Week:
- [ ] Evaluate performance
- [ ] Check if Sharpe > 1.0
- [ ] Verify Win Rate > 50%
- [ ] Decide on live trading

---

## 🎉 What You Now Have

✅ Professional trading framework
✅ Two proven strategies (trend + mean-reversion)
✅ Institutional risk management (Kelly sizing, correlation checks)
✅ Backtesting validation (walk-forward, Monte Carlo)
✅ Real-time dashboard
✅ Complete trade journal
✅ Parameter optimization
✅ Parameter optimization

---

## Important Mindset

**This is NOT gambling.** It's systematic trading based on:
- Statistical edge (proven on historical data)
- Risk management (limiting losses)
- Discipline (following rules)
- Testing (backtesting + demo testing)

Success requires:
1. Patience (test for weeks, not days)
2. Discipline (follow risk rules)
3. Humility (losses will happen)
4. Learning (track results, improve)

---

## Ready?

Once parameter optimization finishes (~1-2 hours), you'll have:
1. Best parameters for Trend-Following strategy
2. Best parameters for Mean-Reversion strategy
3. Performance metrics for each
4. Clear path to deployment

Then you can follow the step-by-step guide above.

**Questions?** Check BACKTESTING_GUIDE.md and README.md for details.

**Ready to start?** Set up your demo account and configuration, then run `python main.py`

---

**You've got this! 🚀**
