#!/usr/bin/env python3
"""
Backtester Runner

Complete backtesting workflow:
1. Get historical data (from MT5 or generate sample)
2. Run backtest on all strategies
3. Run walk-forward analysis
4. Run Monte Carlo simulation
5. Generate report

Usage:
    python backtest.py --symbol EURUSD --days 1825 --sample
"""

import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

from src.backtester.backtest_engine import BacktestEngine, BacktestMetrics
from src.backtester.walforward_analyzer import WalkForwardAnalyzer, MonteCarloAnalyzer, ParameterOptimizer
from src.backtester.data_fetcher import HistoricalDataFetcher, DataValidator
from src.strategies import TrendFollowingStrategy, MeanReversionStrategy
from src.risk_management import InstitutionalRiskManager
from src.regime_detector import AdaptiveRegimeDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/backtest.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


def run_backtest(
    data,
    symbol="EURUSD",
    initial_equity=10000,
    output_dir="data/results",
):
    """Run complete backtesting workflow"""

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    config = {
        "risk": {
            "daily_loss_limit": -500,
            "max_drawdown": 0.20,
            "risk_per_trade": 0.02,
            "kelly_factor": 0.25,
        },
        "strategies": {
            "TrendFollowing": {
                "fast_ma_period": 10,
                "slow_ma_period": 20,
                "adx_period": 14,
                "adx_threshold": 25,
            },
            "MeanReversion": {
                "bb_period": 20,
                "bb_std_dev": 2,
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
            },
        },
    }

    risk_manager = InstitutionalRiskManager(config["risk"])
    regime_detector = AdaptiveRegimeDetector()

    strategies = {
        "TrendFollowing": TrendFollowingStrategy(config["strategies"]["TrendFollowing"]),
        "MeanReversion": MeanReversionStrategy(config["strategies"]["MeanReversion"]),
    }

    results = {}

    logger.info("=" * 60)
    logger.info(f"BACKTESTING: {symbol}")
    logger.info("=" * 60)

    for strategy_name, strategy in strategies.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Strategy: {strategy_name}")
        logger.info(f"{'='*60}")

        engine = BacktestEngine(initial_equity=initial_equity)
        metrics = engine.backtest(data, strategy, risk_manager, regime_detector, symbol)

        logger.info("\nBacktest Results:")
        for key, value in metrics.summary().items():
            logger.info(f"  {key}: {value}")

        engine.save_results(f"{output_dir}/{symbol}_{strategy_name}_backtest.json", metrics)

        logger.info(f"\nRunning Walk-Forward Analysis...")
        wf_analyzer = WalkForwardAnalyzer(initial_equity=initial_equity)
        wf_results = wf_analyzer.analyze(
            data, strategy, risk_manager, regime_detector, symbol, rolling_periods=4
        )

        if wf_results:
            logger.info(f"Walk-Forward Analysis:")
            logger.info(f"  Average Win Rate: {wf_results['average_win_rate']*100:.1f}%")
            logger.info(f"  Average Sharpe: {wf_results['average_sharpe']:.2f}")
            logger.info(f"  Total Profit: ${wf_results['total_profit']:.2f}")

            with open(f"{output_dir}/{symbol}_{strategy_name}_walkforward.json", "w") as f:
                json.dump(wf_results, f, indent=2, default=str)

        logger.info(f"\nRunning Monte Carlo Simulation ({1000} simulations)...")
        mc_analyzer = MonteCarloAnalyzer(initial_equity=initial_equity, simulations=1000)
        mc_results = mc_analyzer.analyze(engine.trades)

        if mc_results:
            logger.info(f"Monte Carlo Results:")
            logger.info(f"  Probability of Profit: {mc_results['probability_of_profit']*100:.1f}%")
            logger.info(f"  Worst Case: ${mc_results['worst_case_equity']:.2f}")
            logger.info(f"  Best Case: ${mc_results['best_case_equity']:.2f}")

            with open(f"{output_dir}/{symbol}_{strategy_name}_montecarlo.json", "w") as f:
                json.dump(mc_results, f, indent=2, default=str)

        results[strategy_name] = {
            "backtest": metrics.summary(),
            "walkforward": wf_results,
            "montecarlo": mc_results,
        }

    logger.info("\n" + "=" * 60)
    logger.info("BACKTEST SUMMARY")
    logger.info("=" * 60)

    for strategy_name, result in results.items():
        logger.info(f"\n{strategy_name}:")
        logger.info(f"  Win Rate: {result['backtest'].get('win_rate', 'N/A')}")
        logger.info(f"  Profit Factor: {result['backtest'].get('profit_factor', 'N/A')}")
        logger.info(f"  Sharpe Ratio: {result['backtest'].get('sharpe_ratio', 'N/A')}")
        logger.info(f"  Max Drawdown: {result['backtest'].get('max_drawdown', 'N/A')}")

    with open(f"{output_dir}/{symbol}_summary.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\nResults saved to {output_dir}/")

    return results


def main():
    parser = argparse.ArgumentParser(description="Run EA backtests")
    parser.add_argument("--symbol", default="EURUSD", help="Trading symbol")
    parser.add_argument("--days", type=int, default=1825, help="Days of historical data (5 years)")
    parser.add_argument("--sample", action="store_true", help="Use generated sample data")
    parser.add_argument("--equity", type=int, default=10000, help="Initial account equity")
    parser.add_argument("--output", default="data/results", help="Output directory")

    args = parser.parse_args()

    data_fetcher = HistoricalDataFetcher()

    if args.sample:
        logger.info(f"Generating sample data for {args.symbol}...")
        data = HistoricalDataFetcher.generate_sample_data(
            symbol=args.symbol,
            days=args.days,
        )
    else:
        logger.info(f"Loading cached data for {args.symbol}...")
        data = data_fetcher.load_cached_data(args.symbol)

        if data is None:
            logger.error(f"No data available for {args.symbol}")
            logger.info("Use --sample flag to generate sample data for testing")
            return

    if not DataValidator.validate(data, args.symbol):
        logger.error("Data validation failed")
        return

    results = run_backtest(
        data,
        symbol=args.symbol,
        initial_equity=args.equity,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()
