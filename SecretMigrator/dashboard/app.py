"""
Web dashboard for monitoring trading bot
"""
from flask import Flask, render_template, jsonify, request
import asyncio
import logging
from typing import Dict, Any
import json
import time
from utils.logger import setup_logger
from utils.database import DatabaseManager
from bot.exchange_manager import ExchangeManager
import threading
import pandas as pd
from datetime import datetime, timedelta

class DashboardApp:
    """Web dashboard application"""
    
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger('dashboard')
        self.app = Flask(__name__)
        self.db_manager = DatabaseManager(config.DATABASE_URL)
        self.exchange_manager = ExchangeManager(config)
        
        # Initialize exchange
        asyncio.run(self.exchange_manager.initialize())
        
        # Setup routes
        self.setup_routes()
        
        # Dashboard data cache
        self.cache = {
            'last_update': 0,
            'data': {}
        }
        
        self.cache_timeout = 10  # seconds
        
        # Add startup time for uptime tracking
        self.start_time = time.time()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health')
        def health_check():
            """Health check endpoint for Railway"""
            try:
                # Check database connection
                asyncio.run(self.db_manager.initialize())
                
                # Check exchange connection
                balance = asyncio.run(self.exchange_manager.get_balance())
                
                # Calculate uptime
                uptime = time.time() - self.start_time
                
                return jsonify({
                    'status': 'healthy',
                    'uptime_seconds': int(uptime),
                    'database': 'connected',
                    'exchange': 'connected' if balance is not None else 'error',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            return render_template('index.html')
        
        @self.app.route('/api/status')
        def api_status():
            """Get bot status"""
            try:
                data = self.get_cached_data()
                return jsonify(data.get('status', {}))
            except Exception as e:
                self.logger.error(f"Error getting status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/trades')
        def api_trades():
            """Get recent trades"""
            try:
                limit = request.args.get('limit', 50, type=int)
                trades = asyncio.run(self.db_manager.get_trades(limit=limit))
                
                # Calculate additional metrics for each trade
                for trade in trades:
                    if trade.get('exit_price') and trade.get('entry_price'):
                        pnl = (trade['exit_price'] - trade['entry_price']) * trade['amount']
                        if trade['side'] == 'sell':
                            pnl = -pnl
                        trade['pnl'] = round(pnl, 2)
                        trade['pnl_percentage'] = round((pnl / (trade['entry_price'] * trade['amount'])) * 100, 2)
                    
                return jsonify(trades)
            except Exception as e:
                self.logger.error(f"Error getting trades: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/performance')
        def api_performance():
            """Get performance metrics"""
            try:
                days = request.args.get('days', 30, type=int)
                
                # Get all trades within the period
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                trades = asyncio.run(self.db_manager.get_trades_in_period(start_date, end_date))
                
                # Calculate performance metrics
                total_trades = len(trades)
                winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
                total_pnl = sum(t.get('pnl', 0) for t in trades)
                
                # Calculate daily returns for Sharpe ratio
                daily_returns = []
                current_date = start_date
                while current_date <= end_date:
                    day_trades = [t for t in trades if t['timestamp'].date() == current_date.date()]
                    daily_pnl = sum(t.get('pnl', 0) for t in day_trades)
                    daily_returns.append(daily_pnl)
                    current_date += timedelta(days=1)
                
                # Calculate Sharpe ratio
                if daily_returns:
                    returns_series = pd.Series(daily_returns)
                    excess_returns = returns_series - (self.config.RISK_FREE_RATE / 365)
                    sharpe_ratio = (excess_returns.mean() / excess_returns.std()) * (252 ** 0.5) if excess_returns.std() != 0 else 0
                else:
                    sharpe_ratio = 0
                
                metrics = {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                    'total_pnl': total_pnl,
                    'sharpe_ratio': round(sharpe_ratio, 2),
                    'daily_returns': daily_returns
                }
                
                return jsonify(metrics)
            except Exception as e:
                self.logger.error(f"Error getting performance: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/statistics')
        def api_statistics():
            """Get trading statistics"""
            try:
                # Get current positions
                positions = asyncio.run(self.exchange_manager.get_positions())
                
                # Get account balance
                balance = asyncio.run(self.exchange_manager.get_balance())
                
                # Calculate total equity
                total_equity = sum(float(bal) for bal in balance.values())
                
                # Get recent trades for daily P&L
                today = datetime.now().date()
                today_trades = asyncio.run(self.db_manager.get_trades_in_period(
                    datetime.combine(today, datetime.min.time()),
                    datetime.now()
                ))
                daily_pnl = sum(t.get('pnl', 0) for t in today_trades)
                
                stats = {
                    'total_equity': total_equity,
                    'daily_pnl': daily_pnl,
                    'active_positions': len(positions) if positions else 0,
                    'total_trades': asyncio.run(self.db_manager.get_total_trades_count())
                }
                
                return jsonify(stats)
            except Exception as e:
                self.logger.error(f"Error getting statistics: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/market-data')
        def api_market_data():
            """Get market data summary"""
            try:
                market_data = {}
                
                for symbol in self.config.TRADING_PAIRS:
                    # Get current price
                    price = asyncio.run(self.exchange_manager.get_current_price(symbol))
                    
                    # Get 24h OHLCV data
                    ohlcv = asyncio.run(self.exchange_manager.get_ohlcv(symbol, '1d', 2))
                    
                    if price and ohlcv and len(ohlcv) >= 2:
                        prev_close = ohlcv[-2][4]  # Previous day's close price
                        change_24h = ((price - prev_close) / prev_close) * 100
                        
                        market_data[symbol] = {
                            'price': price,
                            'change_24h': round(change_24h, 2)
                        }
                
                return jsonify(market_data)
            except Exception as e:
                self.logger.error(f"Error getting market data: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/positions')
        def api_positions():
            """Get active positions"""
            try:
                positions = asyncio.run(self.exchange_manager.get_positions())
                
                # Enhance position data with current prices and P&L
                for position in positions:
                    symbol = position['symbol']
                    current_price = asyncio.run(self.exchange_manager.get_current_price(symbol))
                    
                    if current_price:
                        entry_price = position.get('entryPrice', position.get('entry_price', 0))
                        size = position.get('size', position.get('amount', 0))
                        
                        # Calculate unrealized P&L
                        pnl = (current_price - entry_price) * size
                        if position['side'] == 'sell':
                            pnl = -pnl
                        
                        position['current_price'] = current_price
                        position['unrealized_pnl'] = round(pnl, 2)
                        position['pnl_percentage'] = round((pnl / (entry_price * size)) * 100, 2)
                
                return jsonify(positions or [])
            except Exception as e:
                self.logger.error(f"Error getting positions: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/signals')
        def api_signals():
            """Get trading signals"""
            try:
                signals = {
                    'market_sentiment': self._calculate_market_sentiment(),
                    'technical_signals': self._get_technical_signals(),
                    'risk_level': self._calculate_risk_level()
                }
                return jsonify(signals)
            except Exception as e:
                self.logger.error(f"Error getting signals: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _calculate_market_sentiment(self) -> Dict[str, Any]:
        """Calculate overall market sentiment"""
        try:
            sentiment_data = {}
            
            for symbol in self.config.TRADING_PAIRS:
                # Get recent price data
                ohlcv = asyncio.run(self.exchange_manager.get_ohlcv(symbol, '1h', 24))
                
                if ohlcv:
                    # Convert to DataFrame for analysis
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    
                    # Calculate basic indicators
                    df['returns'] = df['close'].pct_change()
                    volatility = df['returns'].std() * (24 ** 0.5)  # Annualized volatility
                    trend = 'bullish' if df['close'].iloc[-1] > df['close'].mean() else 'bearish'
                    
                    sentiment_data[symbol] = {
                        'trend': trend,
                        'volatility': round(volatility * 100, 2),
                        'volume_change': round((df['volume'].iloc[-1] / df['volume'].mean() - 1) * 100, 2)
                    }
            
            return sentiment_data
            
        except Exception as e:
            self.logger.error(f"Error calculating market sentiment: {e}")
            return {}
    
    def _get_technical_signals(self) -> Dict[str, Any]:
        """Get technical analysis signals"""
        try:
            signals = {}
            
            for symbol in self.config.TRADING_PAIRS:
                # Get OHLCV data
                ohlcv = asyncio.run(self.exchange_manager.get_ohlcv(symbol, '1h', 100))
                
                if ohlcv:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    
                    # Calculate technical indicators
                    df['sma_20'] = df['close'].rolling(window=20).mean()
                    df['sma_50'] = df['close'].rolling(window=50).mean()
                    
                    # Generate signals
                    last_row = df.iloc[-1]
                    signals[symbol] = {
                        'trend': 'bullish' if last_row['sma_20'] > last_row['sma_50'] else 'bearish',
                        'strength': 'strong' if abs(last_row['sma_20'] - last_row['sma_50']) / last_row['sma_50'] > 0.02 else 'weak'
                    }
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error getting technical signals: {e}")
            return {}
    
    def _calculate_risk_level(self) -> str:
        """Calculate current risk level"""
        try:
            # Get positions
            positions = asyncio.run(self.exchange_manager.get_positions())
            
            # Get account balance
            balance = asyncio.run(self.exchange_manager.get_balance())
            total_equity = sum(float(bal) for bal in balance.values())
            
            # Calculate risk metrics
            position_exposure = sum(float(pos['notional']) for pos in positions) if positions else 0
            exposure_ratio = position_exposure / total_equity if total_equity > 0 else 0
            
            # Determine risk level
            if exposure_ratio > 0.8:
                return 'HIGH'
            elif exposure_ratio > 0.5:
                return 'MEDIUM'
            else:
                return 'LOW'
            
        except Exception as e:
            self.logger.error(f"Error calculating risk level: {e}")
            return 'UNKNOWN'
    
    def get_cached_data(self) -> Dict[str, Any]:
        """Get cached dashboard data"""
        current_time = time.time()
        
        if (current_time - self.cache['last_update']) > self.cache_timeout:
            # Update cache
            self.cache['data'] = self.fetch_dashboard_data()
            self.cache['last_update'] = current_time
        
        return self.cache['data']
    
    def fetch_dashboard_data(self) -> Dict[str, Any]:
        """Fetch fresh dashboard data"""
        try:
            data = {
                'status': {
                    'running': True,  # This would come from the actual bot
                    'uptime': '0h 0m',  # Calculate actual uptime
                    'last_update': time.time()
                },
                'market_data': {
                    'BTC/USDT': {
                        'price': 45000.0,  # Placeholder - get from actual data
                        'change_24h': 2.5
                    },
                    'ETH/USDT': {
                        'price': 3000.0,
                        'change_24h': -1.2
                    }
                }
            }
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error fetching dashboard data: {e}")
            return {}
    
    def run(self, host='0.0.0.0', port=5000):
        """Run the dashboard application"""
        self.app.run(host=host, port=port)

def start_dashboard(config):
    """Start dashboard in a separate thread"""
    try:
        dashboard = DashboardApp(config)
        dashboard.run(
            host=config.DASHBOARD_HOST,
            port=config.DASHBOARD_PORT,
            debug=False
        )
    except Exception as e:
        logging.error(f"Error starting dashboard: {e}")

if __name__ == '__main__':
    from config import Config
    config = Config()
    start_dashboard(config)
