#!/usr/bin/env python3
"""
Real-time Trading Dashboard

Visual monitoring of EA trading performance.
Shows equity curve, trades, win rate, and profitability metrics.

Run with: python dashboard.py
Then open: http://localhost:5000
"""

from flask import Flask, render_string, jsonify
import json
import os
from datetime import datetime
from src.monitoring import TradeJournal

app = Flask(__name__)

# Simple HTML template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>EA Trading Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 32px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
        }
        .stat-label {
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: #333;
        }
        .stat-value.positive { color: #10b981; }
        .stat-value.negative { color: #ef4444; }
        .stat-value.neutral { color: #667eea; }
        .chart-container {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            margin-bottom: 30px;
        }
        .chart-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }
        .trades-table {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }
        tr:hover { background: #f9f9f9; }
        .profit-positive { color: #10b981; font-weight: bold; }
        .profit-negative { color: #ef4444; font-weight: bold; }
        .info-section {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .info-title {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        .info-text {
            color: #666;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 EA Trading Dashboard</h1>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Today's Trades</div>
                <div class="stat-value neutral" id="today-trades">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Today's P&L</div>
                <div class="stat-value" id="today-profit">$0.00</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Win Rate (Today)</div>
                <div class="stat-value" id="today-winrate">0%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">This Month P&L</div>
                <div class="stat-value" id="month-profit">$0.00</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Trades</div>
                <div class="stat-value neutral" id="total-trades">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">All-Time P&L</div>
                <div class="stat-value" id="total-profit">$0.00</div>
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-title">📈 Equity Curve</div>
            <canvas id="equityChart"></canvas>
        </div>

        <div class="chart-container">
            <div class="chart-title">📊 Win Rate Over Time</div>
            <canvas id="winrateChart"></canvas>
        </div>

        <div class="info-section">
            <div class="info-title">⚙️ System Status</div>
            <div class="info-text">
                Last Update: <span id="last-update">Never</span><br>
                Status: <span id="status" style="color: #10b981;">Ready</span><br>
                Strategy: Trend-Following + Mean-Reversion (Adaptive)
            </div>
        </div>

        <div class="trades-table">
            <table>
                <thead>
                    <tr>
                        <th>Entry Time</th>
                        <th>Symbol</th>
                        <th>Type</th>
                        <th>Entry Price</th>
                        <th>Exit Price</th>
                        <th>Profit/Loss</th>
                    </tr>
                </thead>
                <tbody id="trades-body">
                    <tr><td colspan="6" style="text-align: center; color: #999;">No trades yet</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // Fetch and display dashboard data
        async function updateDashboard() {
            const response = await fetch('/api/stats');
            const data = await response.json();

            // Update stat cards
            document.getElementById('today-trades').textContent = data.today.trades;
            document.getElementById('today-profit').textContent = '$' + data.today.profit.toFixed(2);
            document.getElementById('today-profit').className = 'stat-value ' + (data.today.profit >= 0 ? 'positive' : 'negative');
            document.getElementById('today-winrate').textContent = (data.today.win_rate * 100).toFixed(1) + '%';

            document.getElementById('month-profit').textContent = '$' + data.month.profit.toFixed(2);
            document.getElementById('month-profit').className = 'stat-value ' + (data.month.profit >= 0 ? 'positive' : 'negative');

            document.getElementById('total-trades').textContent = data.all_time.trades;
            document.getElementById('total-profit').textContent = '$' + data.all_time.profit.toFixed(2);
            document.getElementById('total-profit').className = 'stat-value ' + (data.all_time.profit >= 0 ? 'positive' : 'negative');

            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();

            // Update trades table
            const tbody = document.getElementById('trades-body');
            if (data.recent_trades && data.recent_trades.length > 0) {
                tbody.innerHTML = data.recent_trades.map(trade => `
                    <tr>
                        <td>${new Date(trade.entry_time).toLocaleString()}</td>
                        <td>${trade.symbol}</td>
                        <td>${trade.type}</td>
                        <td>${parseFloat(trade.entry_price).toFixed(5)}</td>
                        <td>${trade.exit_price ? parseFloat(trade.exit_price).toFixed(5) : '-'}</td>
                        <td class="${trade.profit >= 0 ? 'profit-positive' : 'profit-negative'}">
                            $${trade.profit.toFixed(2)}
                        </td>
                    </tr>
                `).join('');
            }

            // Update charts
            updateCharts(data);
        }

        function updateCharts(data) {
            // Equity curve chart
            const equityCtx = document.getElementById('equityChart').getContext('2d');
            new Chart(equityCtx, {
                type: 'line',
                data: {
                    labels: Array.from({length: data.equity_curve.length}, (_, i) => i),
                    datasets: [{
                        label: 'Account Equity',
                        data: data.equity_curve,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.3,
                        fill: true,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: true } }
                }
            });

            // Win rate chart
            const winrateCtx = document.getElementById('winrateChart').getContext('2d');
            new Chart(winrateCtx, {
                type: 'bar',
                data: {
                    labels: ['Today', 'This Week', 'This Month', 'All Time'],
                    datasets: [{
                        label: 'Win Rate %',
                        data: [
                            data.today.win_rate * 100,
                            data.week.win_rate * 100,
                            data.month.win_rate * 100,
                            data.all_time.win_rate ? (data.all_time.win_rate.toFixed ? data.all_time.win_rate * 100 : 0) : 0
                        ],
                        backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#4facfe'],
                    }]
                },
                options: {
                    responsive: true,
                    scales: { y: { min: 0, max: 100 } }
                }
            });
        }

        // Update every 5 seconds
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    """Render main dashboard"""
    return render_string(DASHBOARD_HTML)


@app.route('/api/stats')
def get_stats():
    """Get trading statistics as JSON"""
    journal = TradeJournal()

    return jsonify({
        'today': journal.get_todays_stats(),
        'week': journal.get_weekly_stats(),
        'month': journal.get_monthly_stats(),
        'all_time': journal.get_all_time_stats(),
        'recent_trades': journal.get_recent_trades(10),
        'equity_curve': journal.get_equity_curve(),
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 EA Trading Dashboard Started")
    print("="*60)
    print("\n📊 Open your browser and go to:")
    print("   http://localhost:5000")
    print("\nThe dashboard will show:")
    print("   ✅ Live equity curve")
    print("   ✅ Daily/weekly/monthly P&L")
    print("   ✅ Win rates and trade history")
    print("   ✅ Real-time performance metrics")
    print("\nPress Ctrl+C to stop the dashboard")
    print("="*60 + "\n")

    app.run(debug=False, port=5000)
