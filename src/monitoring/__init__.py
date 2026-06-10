import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class TradeJournal:
    """Records and analyzes all trades for performance tracking"""

    def __init__(self, filepath: str = "data/results/trade_journal.json"):
        self.filepath = filepath
        self.trades = []
        self.load()

    def add_trade(self, trade_dict: Dict):
        """Add a completed trade to the journal"""
        self.trades.append(trade_dict)
        self.save()

    def save(self):
        """Save journal to file"""
        with open(self.filepath, "w") as f:
            json.dump(self.trades, f, indent=2, default=str)

    def load(self):
        """Load journal from file"""
        try:
            with open(self.filepath, "r") as f:
                self.trades = json.load(f)
        except FileNotFoundError:
            self.trades = []

    def get_todays_stats(self) -> Dict:
        """Get today's trading statistics"""
        today = datetime.now().date()
        todays_trades = [
            t for t in self.trades
            if datetime.fromisoformat(t.get("entry_time", "")).date() == today
        ]

        if not todays_trades:
            return {
                "trades": 0,
                "profit": 0,
                "win_rate": 0,
                "avg_profit": 0,
            }

        profits = [t.get("profit", 0) for t in todays_trades]
        wins = len([p for p in profits if p > 0])

        return {
            "trades": len(todays_trades),
            "profit": sum(profits),
            "win_rate": wins / len(todays_trades) if todays_trades else 0,
            "avg_profit": sum(profits) / len(profits) if profits else 0,
        }

    def get_weekly_stats(self) -> Dict:
        """Get this week's trading statistics"""
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())

        week_trades = [
            t for t in self.trades
            if datetime.fromisoformat(t.get("entry_time", "")).date() >= week_start
        ]

        if not week_trades:
            return {
                "trades": 0,
                "profit": 0,
                "win_rate": 0,
                "avg_profit": 0,
            }

        profits = [t.get("profit", 0) for t in week_trades]
        wins = len([p for p in profits if p > 0])

        return {
            "trades": len(week_trades),
            "profit": sum(profits),
            "win_rate": wins / len(week_trades) if week_trades else 0,
            "avg_profit": sum(profits) / len(profits) if profits else 0,
        }

    def get_monthly_stats(self) -> Dict:
        """Get this month's trading statistics"""
        today = datetime.now()
        month_start = today.replace(day=1).date()

        month_trades = [
            t for t in self.trades
            if datetime.fromisoformat(t.get("entry_time", "")).date() >= month_start
        ]

        if not month_trades:
            return {
                "trades": 0,
                "profit": 0,
                "win_rate": 0,
                "avg_profit": 0,
            }

        profits = [t.get("profit", 0) for t in month_trades]
        wins = len([p for p in profits if p > 0])

        return {
            "trades": len(month_trades),
            "profit": sum(profits),
            "win_rate": wins / len(month_trades) if month_trades else 0,
            "avg_profit": sum(profits) / len(profits) if profits else 0,
        }

    def get_all_time_stats(self) -> Dict:
        """Get all-time trading statistics"""
        if not self.trades:
            return {
                "trades": 0,
                "profit": 0,
                "win_rate": 0,
                "avg_profit": 0,
                "best_trade": 0,
                "worst_trade": 0,
            }

        profits = [t.get("profit", 0) for t in self.trades]
        wins = len([p for p in profits if p > 0])

        return {
            "trades": len(self.trades),
            "profit": sum(profits),
            "win_rate": wins / len(self.trades) if self.trades else 0,
            "avg_profit": sum(profits) / len(profits) if profits else 0,
            "best_trade": max(profits),
            "worst_trade": min(profits),
        }

    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get most recent trades"""
        return sorted(
            self.trades,
            key=lambda x: x.get("entry_time", ""),
            reverse=True
        )[:limit]

    def get_equity_curve(self) -> List[float]:
        """Generate equity curve from trades"""
        initial_equity = 10000
        equity = initial_equity
        curve = [initial_equity]

        for trade in sorted(self.trades, key=lambda x: x.get("entry_time", "")):
            profit = trade.get("profit", 0)
            equity += profit
            curve.append(equity)

        return curve
