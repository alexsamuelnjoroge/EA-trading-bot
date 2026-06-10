import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging
from datetime import datetime, timedelta
from src.backtester.backtest_engine import BacktestEngine, BacktestMetrics

logger = logging.getLogger(__name__)


class WalkForwardAnalyzer:
    """
    Walk-forward testing to avoid curve-fitting

    Prevents strategies from being optimized on past data that won't repeat.
    Tests on rolling windows that don't overlap with optimization periods.
    """

    def __init__(self, initial_equity: float = 10000):
        self.initial_equity = initial_equity
        self.wf_results: List[Dict] = []

    def analyze(
        self,
        data: pd.DataFrame,
        strategy,
        risk_manager,
        regime_detector=None,
        symbol: str = "EURUSD",
        train_test_split: float = 0.7,
        rolling_periods: int = 4,
    ) -> Dict:
        """
        Run walk-forward analysis

        Args:
            data: Full historical OHLC data
            strategy: Strategy instance
            risk_manager: Risk manager instance
            regime_detector: Optional regime detector
            symbol: Trading symbol
            train_test_split: % of data to use for training
            rolling_periods: Number of rolling windows to test

        Returns:
            Dictionary with walk-forward results
        """
        total_bars = len(data)
        window_size = total_bars // rolling_periods

        logger.info(
            f"Starting walk-forward analysis: {rolling_periods} periods, "
            f"window size: {window_size} bars"
        )

        all_out_of_sample_trades = []
        all_metrics = []

        for period in range(rolling_periods):
            logger.info(f"=== Walk-Forward Period {period + 1}/{rolling_periods} ===")

            start_idx = period * window_size
            end_idx = start_idx + window_size

            if end_idx > total_bars:
                end_idx = total_bars

            train_end = int(start_idx + (end_idx - start_idx) * train_test_split)

            train_data = data.iloc[start_idx:train_end]
            test_data = data.iloc[train_end:end_idx]

            if len(train_data) < 50 or len(test_data) < 20:
                logger.warning(f"Skipping period {period + 1}: insufficient data")
                continue

            logger.info(f"  Training on {len(train_data)} bars, testing on {len(test_data)} bars")

            engine = BacktestEngine(initial_equity=self.initial_equity)
            metrics = engine.backtest(test_data, strategy, risk_manager, regime_detector, symbol)

            self.wf_results.append({
                "period": period + 1,
                "train_start": train_data.index[0],
                "train_end": train_data.index[-1],
                "test_start": test_data.index[0],
                "test_end": test_data.index[-1],
                "trades": len(engine.trades),
                "win_rate": metrics.win_rate(),
                "profit_factor": metrics.profit_factor(),
                "total_profit": metrics.total_profit(),
                "sharpe_ratio": metrics.sharpe_ratio(),
                "max_drawdown": metrics.max_drawdown(),
            })

            all_out_of_sample_trades.extend(engine.trades)
            all_metrics.append(metrics)

            logger.info(f"  Results: {metrics.win_rate()*100:.1f}% win rate, ${metrics.total_profit():.2f} profit")

        if not all_out_of_sample_trades:
            logger.warning("No trades generated in walk-forward analysis")
            return None

        combined_metrics = BacktestMetrics(all_out_of_sample_trades, self.initial_equity)

        summary = {
            "strategy": strategy.name,
            "total_periods": len(self.wf_results),
            "out_of_sample_trades": len(all_out_of_sample_trades),
            "average_win_rate": np.mean([r["win_rate"] for r in self.wf_results]),
            "average_profit_factor": np.mean([r["profit_factor"] for r in self.wf_results if r["profit_factor"] != float('inf')]),
            "average_sharpe": np.mean([r["sharpe_ratio"] for r in self.wf_results]),
            "average_max_drawdown": np.mean([r["max_drawdown"] for r in self.wf_results]),
            "total_profit": combined_metrics.total_profit(),
            "overall_sharpe": combined_metrics.sharpe_ratio(),
            "overall_max_drawdown": combined_metrics.max_drawdown(),
            "period_results": self.wf_results,
        }

        logger.info(f"\n{'='*50}")
        logger.info(f"Walk-Forward Summary:")
        logger.info(f"  Average Win Rate: {summary['average_win_rate']*100:.1f}%")
        logger.info(f"  Average Profit Factor: {summary['average_profit_factor']:.2f}")
        logger.info(f"  Total Out-of-Sample Profit: ${summary['total_profit']:.2f}")
        logger.info(f"  Overall Sharpe Ratio: {summary['overall_sharpe']:.2f}")
        logger.info(f"{'='*50}\n")

        return summary


class MonteCarloAnalyzer:
    """
    Monte Carlo simulation for robustness testing

    Randomly shuffles trade sequences to test if strategy is robust
    or just lucky with the specific order of trades.
    """

    def __init__(self, initial_equity: float = 10000, simulations: int = 1000):
        self.initial_equity = initial_equity
        self.simulations = simulations

    def analyze(self, trades: List) -> Dict:
        """
        Run Monte Carlo analysis on trade results

        Args:
            trades: List of Trade objects from backtest

        Returns:
            Dictionary with robustness statistics
        """
        if not trades or len(trades) < 10:
            logger.warning("Insufficient trades for Monte Carlo analysis")
            return None

        profits = np.array([t.profit for t in trades if t.profit is not None])

        simulation_results = []

        logger.info(f"Running {self.simulations} Monte Carlo simulations...")

        for sim in range(self.simulations):
            shuffled_profits = np.random.permutation(profits)
            cumulative = np.cumsum(shuffled_profits)
            max_dd = self._calculate_max_drawdown(cumulative + self.initial_equity)
            final_equity = cumulative[-1] + self.initial_equity

            simulation_results.append({
                "final_equity": final_equity,
                "total_profit": cumulative[-1],
                "max_drawdown": max_dd,
            })

        final_equities = [r["final_equity"] for r in simulation_results]
        max_drawdowns = [r["max_drawdown"] for r in simulation_results]

        summary = {
            "simulations": self.simulations,
            "original_trades": len(trades),
            "average_final_equity": np.mean(final_equities),
            "median_final_equity": np.median(final_equities),
            "worst_case_equity": np.min(final_equities),
            "best_case_equity": np.max(final_equities),
            "equity_std_dev": np.std(final_equities),
            "probability_of_profit": np.sum(np.array(final_equities) > self.initial_equity) / self.simulations,
            "average_max_drawdown": np.mean(max_drawdowns),
            "worst_max_drawdown": np.max(max_drawdowns),
        }

        logger.info(f"\n{'='*50}")
        logger.info(f"Monte Carlo Results ({self.simulations} simulations):")
        logger.info(f"  Probability of Profit: {summary['probability_of_profit']*100:.1f}%")
        logger.info(f"  Average Final Equity: ${summary['average_final_equity']:.2f}")
        logger.info(f"  Worst Case Equity: ${summary['worst_case_equity']:.2f}")
        logger.info(f"  Best Case Equity: ${summary['best_case_equity']:.2f}")
        logger.info(f"  Worst Max Drawdown: {summary['worst_max_drawdown']*100:.1f}%")
        logger.info(f"{'='*50}\n")

        return summary

    @staticmethod
    def _calculate_max_drawdown(equity_curve: np.ndarray) -> float:
        """Calculate maximum drawdown from equity curve"""
        peak = equity_curve[0]
        max_dd = 0

        for value in equity_curve:
            drawdown = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, drawdown)
            peak = max(peak, value)

        return max_dd


class ParameterOptimizer:
    """
    Grid search parameter optimization for strategies
    """

    def __init__(self, initial_equity: float = 10000):
        self.initial_equity = initial_equity
        self.optimization_results = []

    def optimize(
        self,
        data: pd.DataFrame,
        strategy_class,
        risk_manager,
        parameter_grid: Dict,
        symbol: str = "EURUSD",
        metric: str = "sharpe_ratio",
    ) -> Dict:
        """
        Optimize strategy parameters using grid search

        Args:
            data: Historical OHLC data
            strategy_class: Strategy class (not instance)
            risk_manager: Risk manager instance
            parameter_grid: Dict of parameter: [values] to test
            symbol: Trading symbol
            metric: Which metric to optimize for (sharpe_ratio, profit_factor, win_rate)

        Returns:
            Dictionary with best parameters and results
        """
        import itertools

        param_names = list(parameter_grid.keys())
        param_values = list(parameter_grid.values())
        param_combinations = list(itertools.product(*param_values))

        logger.info(f"Starting parameter optimization: {len(param_combinations)} combinations")

        best_score = float('-inf') if metric != "max_drawdown" else float('inf')
        best_params = None
        best_metrics = None

        for idx, combo in enumerate(param_combinations):
            params = dict(zip(param_names, combo))

            try:
                strategy = strategy_class(params)
                engine = BacktestEngine(initial_equity=self.initial_equity)
                metrics = engine.backtest(data, strategy, risk_manager, symbol=symbol)

                if metric == "sharpe_ratio":
                    score = metrics.sharpe_ratio()
                elif metric == "profit_factor":
                    score = metrics.profit_factor()
                elif metric == "win_rate":
                    score = metrics.win_rate()
                elif metric == "max_drawdown":
                    score = metrics.max_drawdown()
                else:
                    score = metrics.total_profit()

                self.optimization_results.append({
                    "params": params,
                    "sharpe": metrics.sharpe_ratio(),
                    "profit_factor": metrics.profit_factor(),
                    "win_rate": metrics.win_rate(),
                    "max_drawdown": metrics.max_drawdown(),
                    "total_profit": metrics.total_profit(),
                })

                is_better = (score > best_score) if metric != "max_drawdown" else (score < best_score)

                if is_better:
                    best_score = score
                    best_params = params
                    best_metrics = metrics

                if (idx + 1) % max(1, len(param_combinations) // 10) == 0:
                    logger.info(f"  Tested {idx + 1}/{len(param_combinations)} combinations...")

            except Exception as e:
                logger.warning(f"Error testing params {params}: {e}")
                continue

        logger.info(f"\n{'='*50}")
        logger.info(f"Optimization Results (optimizing for {metric}):")
        logger.info(f"  Best Parameters: {best_params}")
        logger.info(f"  Best {metric}: {best_score:.2f}")
        logger.info(f"  Win Rate: {best_metrics.win_rate()*100:.1f}%")
        logger.info(f"  Sharpe Ratio: {best_metrics.sharpe_ratio():.2f}")
        logger.info(f"  Max Drawdown: {best_metrics.max_drawdown()*100:.1f}%")
        logger.info(f"{'='*50}\n")

        return {
            "best_params": best_params,
            "best_score": best_score,
            "best_metrics": best_metrics.summary(),
            "all_results": self.optimization_results,
        }
