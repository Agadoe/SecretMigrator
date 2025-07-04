"""
Exchange management module for handling cryptocurrency exchange operations
"""
import ccxt
import asyncio
import logging
from typing import Dict, List, Optional, Any
import time
from utils.logger import setup_logger

class ExchangeManager:
    """Manages cryptocurrency exchange operations"""
    
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger('exchange_manager')
        
        # Exchange instance
        self.exchange = None
        self.exchange_id = config.EXCHANGE_NAME.lower()
        
        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Order tracking
        self.open_orders = {}
        
        # Demo mode data
        self.demo_prices = {
            'BTC/USDT': 45000.0,
            'ETH/USDT': 3000.0,
            'ADA/USDT': 1.5
        }
        self.demo_balance = {
            'USDT': 1000.0,
            'BTC': 0.0,
            'ETH': 0.0,
            'ADA': 0.0
        }
        
    async def initialize(self):
        """Initialize exchange connection"""
        try:
            # Check if we should use demo mode due to API restrictions
            if self.config.TRADING_MODE == 'demo' or not self.config.EXCHANGE_API_KEY:
                self.logger.info("Initializing in demo mode - no real exchange connection")
                self.exchange = None
                return
            
            # Get exchange class
            exchange_class = getattr(ccxt, self.exchange_id)
            
            # Initialize exchange with configuration
            self.exchange = exchange_class(self.config.get_exchange_config())
            
            # Test connection
            await self._test_connection()
            
            self.logger.info(f"Exchange {self.exchange_id} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize exchange: {e}")
            # Fall back to demo mode
            self.logger.info("Falling back to demo mode")
            self.exchange = None
    
    async def close(self):
        """Close exchange connection"""
        if self.exchange:
            try:
                await self.exchange.close()
                self.logger.info("Exchange connection closed")
            except Exception as e:
                self.logger.error(f"Error closing exchange connection: {e}")
    
    async def _test_connection(self):
        """Test exchange connection"""
        try:
            # Test by fetching exchange status
            status = await asyncio.to_thread(self.exchange.fetch_status)
            
            if status['status'] != 'ok':
                raise Exception(f"Exchange status: {status['status']}")
            
            # Test API credentials by fetching balance
            balance = await asyncio.to_thread(self.exchange.fetch_balance)
            
            self.logger.info("Exchange connection test successful")
            
        except Exception as e:
            self.logger.error(f"Exchange connection test failed: {e}")
            raise
    
    async def _rate_limit(self, endpoint: str):
        """Implement rate limiting"""
        current_time = time.time()
        
        if endpoint in self.last_request_time:
            time_since_last = current_time - self.last_request_time[endpoint]
            
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                await asyncio.sleep(sleep_time)
        
        self.last_request_time[endpoint] = time.time()
    
    def _get_demo_price(self, symbol: str) -> float:
        """Get simulated price for demo mode"""
        import random
        base_price = self.demo_prices.get(symbol, 100.0)
        # Add small random variation (±1%)
        variation = random.uniform(-0.01, 0.01)
        return base_price * (1 + variation)
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            # Demo mode simulation
            if not self.exchange:
                return self._get_demo_price(symbol)
            
            await self._rate_limit('ticker')
            
            ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
            return ticker['last']
            
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return self._get_demo_price(symbol)
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """Get orderbook for a symbol"""
        try:
            await self._rate_limit('orderbook')
            
            orderbook = await asyncio.to_thread(
                self.exchange.fetch_order_book, symbol, limit
            )
            return orderbook
            
        except Exception as e:
            self.logger.error(f"Error getting orderbook for {symbol}: {e}")
            return None
    
    async def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> Optional[List]:
        """Get OHLCV data for a symbol"""
        try:
            await self._rate_limit('ohlcv')
            
            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit
            )
            return ohlcv
            
        except Exception as e:
            self.logger.error(f"Error getting OHLCV for {symbol}: {e}")
            return None
    
    async def get_balance(self) -> Optional[Dict]:
        """Get account balance"""
        try:
            # Demo mode simulation
            if not self.exchange:
                return self.demo_balance.copy()
            
            await self._rate_limit('balance')
            
            balance = await asyncio.to_thread(self.exchange.fetch_balance)
            
            # Return free balances
            return balance['free']
            
        except Exception as e:
            self.logger.error(f"Error getting balance: {e}")
            return self.demo_balance.copy()
    
    async def place_market_order(self, symbol: str, side: str, amount: float) -> Optional[Dict]:
        """Place a market order"""
        try:
            await self._rate_limit('order')
            
            # Validate parameters
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            if side not in ['buy', 'sell']:
                raise ValueError("Side must be 'buy' or 'sell'")
            
            # Place order
            order = await asyncio.to_thread(
                self.exchange.create_market_order,
                symbol, side, amount
            )
            
            # Track order
            self.open_orders[order['id']] = order
            
            self.logger.info(f"Market {side} order placed: {symbol} {amount} - Order ID: {order['id']}")
            
            return order
            
        except Exception as e:
            self.logger.error(f"Error placing market order: {e}")
            return None
    
    async def place_limit_order(self, symbol: str, side: str, amount: float, price: float) -> Optional[Dict]:
        """Place a limit order"""
        try:
            await self._rate_limit('order')
            
            # Validate parameters
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            if price <= 0:
                raise ValueError("Price must be positive")
            
            if side not in ['buy', 'sell']:
                raise ValueError("Side must be 'buy' or 'sell'")
            
            # Place order
            order = await asyncio.to_thread(
                self.exchange.create_limit_order,
                symbol, side, amount, price
            )
            
            # Track order
            self.open_orders[order['id']] = order
            
            self.logger.info(f"Limit {side} order placed: {symbol} {amount} @ {price} - Order ID: {order['id']}")
            
            return order
            
        except Exception as e:
            self.logger.error(f"Error placing limit order: {e}")
            return None
    
    async def place_stop_loss_order(self, symbol: str, side: str, amount: float, stop_price: float) -> Optional[Dict]:
        """Place a stop-loss order"""
        try:
            await self._rate_limit('order')
            
            # Note: Stop-loss implementation varies by exchange
            # This is a simplified version
            
            params = {
                'stopPrice': stop_price,
                'type': 'stop_market'
            }
            
            order = await asyncio.to_thread(
                self.exchange.create_order,
                symbol, 'market', side, amount, None, params
            )
            
            # Track order
            self.open_orders[order['id']] = order
            
            self.logger.info(f"Stop-loss order placed: {symbol} {amount} @ {stop_price} - Order ID: {order['id']}")
            
            return order
            
        except Exception as e:
            self.logger.error(f"Error placing stop-loss order: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        try:
            await self._rate_limit('cancel_order')
            
            await asyncio.to_thread(
                self.exchange.cancel_order, order_id, symbol
            )
            
            # Remove from tracking
            if order_id in self.open_orders:
                del self.open_orders[order_id]
            
            self.logger.info(f"Order cancelled: {order_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Dict]:
        """Get order status"""
        try:
            await self._rate_limit('order_status')
            
            order = await asyncio.to_thread(
                self.exchange.fetch_order, order_id, symbol
            )
            
            return order
            
        except Exception as e:
            self.logger.error(f"Error getting order status for {order_id}: {e}")
            return None
    
    async def get_trading_fees(self, symbol: str) -> Optional[Dict]:
        """Get trading fees for a symbol"""
        try:
            await self._rate_limit('fees')
            
            fees = await asyncio.to_thread(
                self.exchange.fetch_trading_fees
            )
            
            return fees.get(symbol, fees.get('trading', {}))
            
        except Exception as e:
            self.logger.error(f"Error getting trading fees for {symbol}: {e}")
            return None
    
    async def get_positions(self) -> Optional[List[Dict]]:
        """Get open positions (for derivatives exchanges)"""
        try:
            if not hasattr(self.exchange, 'fetch_positions'):
                return []
            
            await self._rate_limit('positions')
            
            positions = await asyncio.to_thread(self.exchange.fetch_positions)
            
            # Filter out zero positions
            active_positions = [pos for pos in positions if pos['size'] != 0]
            
            return active_positions
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return None
    
    async def get_market_info(self, symbol: str) -> Optional[Dict]:
        """Get market information for a symbol"""
        try:
            if not hasattr(self.exchange, 'markets') or not self.exchange.markets:
                await asyncio.to_thread(self.exchange.load_markets)
            
            return self.exchange.markets.get(symbol)
            
        except Exception as e:
            self.logger.error(f"Error getting market info for {symbol}: {e}")
            return None
    
    async def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol is tradable"""
        try:
            market_info = await self.get_market_info(symbol)
            
            if not market_info:
                return False
            
            return market_info.get('active', False)
            
        except Exception as e:
            self.logger.error(f"Error validating symbol {symbol}: {e}")
            return False
    
    async def get_minimum_order_size(self, symbol: str) -> Optional[float]:
        """Get minimum order size for a symbol"""
        try:
            market_info = await self.get_market_info(symbol)
            
            if not market_info:
                return None
            
            limits = market_info.get('limits', {})
            amount_limits = limits.get('amount', {})
            
            return amount_limits.get('min')
            
        except Exception as e:
            self.logger.error(f"Error getting minimum order size for {symbol}: {e}")
            return None
