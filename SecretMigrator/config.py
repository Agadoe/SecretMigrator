"""
Configuration settings for the trading bot
"""
import os
from typing import Dict, Any

class Config:
    """Configuration class"""
    
    def __init__(self):
        # Trading settings
        self.TRADING_MODE = os.getenv('TRADING_MODE', 'live')  # 'live' or 'demo'
        self.TRADING_PAIRS = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
        self.CONFIDENCE_THRESHOLD = 0.75
        self.STOP_LOSS_PERCENTAGE = 2.0
        self.TAKE_PROFIT_PERCENTAGE = 4.0
        self.MAX_POSITIONS = 3
        self.POSITION_SIZE_PERCENTAGE = 10.0  # Percentage of available balance
        self.DAILY_LOSS_LIMIT_PERCENTAGE = 5.0
        
        # Exchange settings
        self.EXCHANGE_NAME = os.getenv('EXCHANGE_NAME', 'binance')
        self.EXCHANGE_API_KEY = os.getenv('TRADING_API_KEY')
        self.EXCHANGE_SECRET = os.getenv('TRADING_SECRET')
        
        # Database settings
        self.DATABASE_URL = 'sqlite:///trading_bot.db'
        
        # Telegram settings
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
        
        # Technical analysis settings
        self.LOOKBACK_PERIODS = 100
        self.TIMEFRAMES = ['1h', '4h', '1d']
        
        # Risk management settings
        self.MAX_DRAWDOWN_PERCENTAGE = 15.0
        self.RISK_FREE_RATE = 0.02  # For Sharpe ratio calculation
        
    def validate(self):
        """Validate configuration settings"""
        if self.TRADING_MODE == 'live':
            assert self.EXCHANGE_API_KEY, "Exchange API key is required for live trading"
            assert self.EXCHANGE_SECRET, "Exchange secret is required for live trading"
        
        assert self.TELEGRAM_BOT_TOKEN, "Telegram bot token is required"
        assert self.TELEGRAM_CHAT_ID, "Telegram chat ID is required"
        
        assert 0 < self.CONFIDENCE_THRESHOLD <= 1, "Confidence threshold must be between 0 and 1"
        assert 0 < self.STOP_LOSS_PERCENTAGE < 100, "Stop loss percentage must be between 0 and 100"
        assert 0 < self.TAKE_PROFIT_PERCENTAGE < 100, "Take profit percentage must be between 0 and 100"
        assert self.MAX_POSITIONS > 0, "Maximum positions must be positive"
        
    def get_exchange_config(self) -> Dict[str, Any]:
        """Get exchange configuration"""
        return {
            'apiKey': self.EXCHANGE_API_KEY,
            'secret': self.EXCHANGE_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
                'recvWindow': 60000
            }
        }
