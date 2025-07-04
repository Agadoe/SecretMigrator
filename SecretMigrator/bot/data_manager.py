"""
Data management module for collecting and storing market data
"""
import pandas as pd
import asyncio
import logging
from typing import Dict, List, Optional, Any
import time
import json
from utils.logger import setup_logger
from utils.database import DatabaseManager

class DataManager:
    """Manages market data collection and storage"""
    
    def __init__(self, config, exchange_manager):
        self.config = config
        self.exchange_manager = exchange_manager
        self.logger = setup_logger('data_manager')
        
        # Data storage
        self.market_data = {}
        self.price_cache = {}
        
        # Database manager
        self.db_manager = DatabaseManager(config.DATABASE_URL)
        
        # Data collection settings
        self.data_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        self.max_candles = 1000
        
    async def initialize(self):
        """Initialize data manager"""
        try:
            await self.db_manager.initialize()
            self.logger.info("Data manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize data manager: {e}")
            raise
    
    async def collect_market_data(self):
        """Collect market data for all trading pairs"""
        try:
            for symbol in self.config.TRADING_PAIRS:
                await self.collect_symbol_data(symbol)
                
            self.logger.debug("Market data collection completed")
            
        except Exception as e:
            self.logger.error(f"Error collecting market data: {e}")
    
    async def collect_symbol_data(self, symbol: str):
        """Collect data for a specific symbol"""
        try:
            # Collect OHLCV data for different timeframes
            for timeframe in self.data_timeframes:
                ohlcv_data = await self.exchange_manager.get_ohlcv(
                    symbol, timeframe, self.max_candles
                )
                
                if ohlcv_data:
                    # Convert to DataFrame
                    df = self._ohlcv_to_dataframe(ohlcv_data)
                    
                    # Store in memory cache
                    cache_key = f"{symbol}_{timeframe}"
                    self.market_data[cache_key] = df
                    
                    # Store in database
                    await self.store_ohlcv_data(symbol, timeframe, df)
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.1)
            
            # Collect current price
            current_price = await self.exchange_manager.get_current_price(symbol)
            if current_price:
                self.price_cache[symbol] = {
                    'price': current_price,
                    'timestamp': time.time()
                }
            
        except Exception as e:
            self.logger.error(f"Error collecting data for {symbol}: {e}")
    
    def _ohlcv_to_dataframe(self, ohlcv_data: List) -> pd.DataFrame:
        """Convert OHLCV data to pandas DataFrame"""
        try:
            df = pd.DataFrame(ohlcv_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume'
            ])
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Convert price columns to float
            price_columns = ['open', 'high', 'low', 'close']
            df[price_columns] = df[price_columns].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error converting OHLCV to DataFrame: {e}")
            return pd.DataFrame()
    
    async def get_market_data(self, symbol: str, timeframe: str = '1h', limit: int = None) -> Optional[pd.DataFrame]:
        """Get market data for a symbol"""
        try:
            cache_key = f"{symbol}_{timeframe}"
            
            # Try to get from cache first
            if cache_key in self.market_data:
                df = self.market_data[cache_key].copy()
                
                if limit:
                    df = df.tail(limit)
                
                return df
            
            # If not in cache, fetch from exchange
            ohlcv_data = await self.exchange_manager.get_ohlcv(
                symbol, timeframe, limit or self.config.LOOKBACK_PERIODS
            )
            
            if ohlcv_data:
                df = self._ohlcv_to_dataframe(ohlcv_data)
                
                # Cache the data
                self.market_data[cache_key] = df
                
                return df
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Get historical data from database"""
        try:
            # Query database for historical data
            query = """
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv_data
            WHERE symbol = ? AND timeframe = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
            """
            
            # Execute query (this would need to be implemented in DatabaseManager)
            # For now, return cached data or fetch from exchange
            return await self.get_market_data(symbol, timeframe)
            
        except Exception as e:
            self.logger.error(f"Error getting historical data: {e}")
            return None
    
    async def store_ohlcv_data(self, symbol: str, timeframe: str, data: pd.DataFrame):
        """Store OHLCV data in database"""
        try:
            if data.empty:
                return
            
            # Prepare data for database insertion
            records = []
            for timestamp, row in data.iterrows():
                records.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'timestamp': timestamp.isoformat(),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume'])
                })
            
            # Store in database (batch insert)
            await self.db_manager.store_ohlcv_batch(records)
            
        except Exception as e:
            self.logger.error(f"Error storing OHLCV data: {e}")
    
    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol"""
        try:
            # Check cache first
            if symbol in self.price_cache:
                cache_entry = self.price_cache[symbol]
                # Use cached price if it's less than 10 seconds old
                if time.time() - cache_entry['timestamp'] < 10:
                    return cache_entry['price']
            
            # Fetch current price
            current_price = await self.exchange_manager.get_current_price(symbol)
            
            if current_price:
                # Update cache
                self.price_cache[symbol] = {
                    'price': current_price,
                    'timestamp': time.time()
                }
                
                return current_price
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting latest price for {symbol}: {e}")
            return None
    
    async def calculate_indicators(self, symbol: str, timeframe: str = '1h') -> Optional[Dict]:
        """Calculate technical indicators for a symbol"""
        try:
            data = await self.get_market_data(symbol, timeframe)
            
            if data is None or data.empty:
                return None
            
            indicators = {}
            
            # Simple Moving Averages
            indicators['sma_20'] = data['close'].rolling(20).mean().iloc[-1]
            indicators['sma_50'] = data['close'].rolling(50).mean().iloc[-1]
            
            # Exponential Moving Averages
            indicators['ema_12'] = data['close'].ewm(span=12).mean().iloc[-1]
            indicators['ema_26'] = data['close'].ewm(span=26).mean().iloc[-1]
            
            # MACD
            macd_line = indicators['ema_12'] - indicators['ema_26']
            indicators['macd'] = macd_line
            
            # RSI
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            indicators['rsi'] = (100 - (100 / (1 + rs))).iloc[-1]
            
            # Bollinger Bands
            bb_middle = data['close'].rolling(20).mean()
            bb_std = data['close'].rolling(20).std()
            indicators['bb_upper'] = (bb_middle + (bb_std * 2)).iloc[-1]
            indicators['bb_lower'] = (bb_middle - (bb_std * 2)).iloc[-1]
            
            # Volume
            indicators['volume_avg'] = data['volume'].rolling(20).mean().iloc[-1]
            indicators['volume_current'] = data['volume'].iloc[-1]
            
            # Price levels
            indicators['high_24h'] = data['high'].tail(24).max()
            indicators['low_24h'] = data['low'].tail(24).min()
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators for {symbol}: {e}")
            return None
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """Get market summary for all trading pairs"""
        try:
            summary = {}
            
            for symbol in self.config.TRADING_PAIRS:
                # Get current price
                price = await self.get_latest_price(symbol)
                
                # Get 24h data
                data_24h = await self.get_market_data(symbol, '1h', 24)
                
                if price and data_24h is not None and not data_24h.empty:
                    price_24h_ago = data_24h['close'].iloc[0]
                    change_24h = ((price - price_24h_ago) / price_24h_ago) * 100
                    
                    volume_24h = data_24h['volume'].sum()
                    high_24h = data_24h['high'].max()
                    low_24h = data_24h['low'].min()
                    
                    summary[symbol] = {
                        'price': price,
                        'change_24h': change_24h,
                        'volume_24h': volume_24h,
                        'high_24h': high_24h,
                        'low_24h': low_24h
                    }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting market summary: {e}")
            return {}
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to save storage space"""
        try:
            cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=days_to_keep)
            
            # Remove old data from memory cache
            for key in list(self.market_data.keys()):
                df = self.market_data[key]
                if not df.empty:
                    # Keep only recent data
                    recent_data = df[df.index > cutoff_date]
                    self.market_data[key] = recent_data
            
            # Clean up database (this would need to be implemented)
            await self.db_manager.cleanup_old_ohlcv_data(cutoff_date.isoformat())
            
            self.logger.info(f"Cleaned up data older than {days_to_keep} days")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
