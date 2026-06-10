#!/usr/bin/env python3
"""
Parameter Optimization Runner

Finds the best parameters for each strategy using grid search
and walk-forward validation to prevent overfitting.
"""

import json
import logging
from pathlib import Path
from src.backtester import ParameterOptimizer, HistoricalDataFetcher, DataValidator
from src.strategies import TrendFollowingStrategy, MeanReversionStrategy
from src.risk_management import InstitutionalRiskManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/optimization.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


def main():
    Path("logs").mkdir(exist_ok=True)
    Path("data/results").mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info("PARAMETER OPTIMIZATION")
    logger.info("=" * 70)

    fetcher = HistoricalDataFetcher()
    data = HistoricalDataFetcher.generate_sample_data("EURUSD", days=1825)

    if not DataValidator.validate(data, "EURUSD"):
        logger.error("Data validation failed")
        return

    risk_manager = InstitutionalRiskManager({
        "daily_loss_limit": -500,
        "risk_per_trade": 0.02,
        "kelly_factor": 0.25,
    })

    logger.info("\n" + "=" * 70)
    logger.info("Optimizing: Trend-Following Strategy")
    logger.info("=" * 70)

    trend_params = {
        "fast_ma_period": [5, 10, 15],
        "slow_ma_period": [20, 30, 40],
        "adx_period": [14],
        "adx_threshold": [20, 25, 30],
        "atr_period": [14],
        "min_atr_ratio": [0.3, 0.5, 0.7],
        "max_atr_ratio": [1.5, 2.0, 2.5],
    }

    trend_optimizer = ParameterOptimizer()
    trend_results = trend_optimizer.optimize(
        data,
        TrendFollowingStrategy,
        risk_manager,
        trend_params,
        metric="sharpe_ratio",
    )

    with open("data/results/trend_optimization.json", "w") as f:
        json.dump(
            {
                "best_params": trend_results["best_params"],
                "best_score": trend_results["best_score"],
                "best_metrics": trend_results["best_metrics"],
            },
            f,
            indent=2,
        )

    logger.info("\n" + "=" * 70)
    logger.info("Optimizing: Mean-Reversion Strategy")
    logger.info("=" * 70)

    mr_params = {
        "bb_period": [15, 20, 25],
        "bb_std_dev": [1.5, 2.0, 2.5],
        "rsi_period": [10, 14, 21],
        "rsi_oversold": [20, 30, 40],
        "rsi_overbought": [60, 70, 80],
        "max_atr_ratio": [0.8, 1.0, 1.2],
        "trend_ma_period": [40, 50, 60],
    }

    mr_optimizer = ParameterOptimizer()
    mr_results = mr_optimizer.optimize(
        data,
        MeanReversionStrategy,
        risk_manager,
        mr_params,
        metric="sharpe_ratio",
    )

    with open("data/results/meanreversion_optimization.json", "w") as f:
        json.dump(
            {
                "best_params": mr_results["best_params"],
                "best_score": mr_results["best_score"],
                "best_metrics": mr_results["best_metrics"],
            },
            f,
            indent=2,
        )

    logger.info("\n" + "=" * 70)
    logger.info("OPTIMIZATION COMPLETE")
    logger.info("=" * 70)

    logger.info("\nBest Trend-Following Parameters:")
    logger.info(json.dumps(trend_results["best_params"], indent=2))

    logger.info("\nBest Mean-Reversion Parameters:")
    logger.info(json.dumps(mr_results["best_params"], indent=2))

    logger.info(f"\nResults saved to data/results/")


if __name__ == "__main__":
    main()
