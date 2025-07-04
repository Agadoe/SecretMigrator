"""
Demo exchange manager for testing without real exchange connectivity
"""
import asyncio
import logging
import random
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from utils.logger import setup_logger

class DemoExchangeManager:
    """Demo exchange manager for testing purposes"""
    
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger('demo_exchange')
        
        # Demo market data
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
        
        # Order tracking
        self.open_orders = {}
        self.order_counter = 1
        
    async def initialize(self):
        """Initialize demo exchange"""
        self.logger.info("Demo exchange initialized successfully")
        
    async def close(self):
        """Close demo exchange"""
        self.logger.info("Demo exchange closed")
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get simulated current price"""
        try:
            base_price = self.demo_prices.get(symbol, 100.0)
            # Add small random variation (±2%)
            variation = random.uniform(-0.02, 0.02)
            price = base_price * (1 + variation)
            return round(price, 4)
        except Exception as e:
            self.logger.error(f"Error getting demo price for {symbol}: {e}")
            return None
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """Get simulated orderbook"""
        try:
            price = await self.get_current_price(symbol)
            if not price:
                return None
                
            # Generate fake orderbook
            bids = []
            asks = []
            
            for i in range(limit):
                bid_price = price * (1 - (i + 1) * 0.001)
                ask_price = price * (1 + (i + 1) * 0.001)
                
                bids.append([bid_price, random.uniform(0.1, 5.0)])
                asks.append([ask_price, random.uniform(0.1, 5.0)])
            
            return {
                'symbol': symbol,
                'bids': bids,
                'asks': asks,
                'timestamp': int(time.time() * 1000)
            }
        except Exception as e:
            self.logger.error(f"Error getting demo orderbook for {symbol}: {e}")
            return None
    
    async def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> Optional[List]:
        """Get simulated OHLCV data"""
        try:
            current_price = self.demo_prices.get(symbol, 100.0)
            ohlcv_data = []
            
            # Generate historical data
            timestamp = int(time.time() * 1000) - (limit * 3600 * 1000)  # Start from limit hours ago
            
            for i in range(limit):
                # Generate realistic OHLCV
                open_price = current_price * (1 + random.uniform(-0.05, 0.05))
                close_price = open_price * (1 + random.uniform(-0.03, 0.03))
                high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
                low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
                volume = random.uniform(100, 1000)
                
                ohlcv_data.append([
                    timestamp,
                    round(open_price, 4),
                    round(high_price, 4),
                    round(low_price, 4),
                    round(close_price, 4),
                    round(volume, 2)
                ])
                
                timestamp += 3600 * 1000  # Next hour
            
            return ohlcv_data
        except Exception as e:
            self.logger.error(f"Error getting demo OHLCV for {symbol}: {e}")
            return None
    
    async def get_balance(self) -> Optional[Dict]:
        """Get simulated balance"""
        return self.demo_balance.copy()
    
    async def place_market_order(self, symbol: str, side: str, amount: float) -> Optional[Dict]:
        """Place simulated market order"""
        try:
            price = await self.get_current_price(symbol)
            if not price:
                return None
            
            order_id = f"demo_{self.order_counter}"
            self.order_counter += 1
            
            # Simulate order execution
            order = {
                'id': order_id,
                'symbol': symbol,
                'type': 'market',
                'side': side,
                'amount': amount,
                'price': price,
                'status': 'closed',
                'filled': amount,
                'timestamp': int(time.time() * 1000),
                'fee': {'cost': amount * price * 0.001, 'currency': 'USDT'}
            }
            
            # Update demo balance
            self._update_demo_balance(symbol, side, amount, price)
            
            self.logger.info(f"Demo order executed: {side} {amount} {symbol} @ {price}")
            return order
            
        except Exception as e:
            self.logger.error(f"Error placing demo market order: {e}")
            return None
    
    async def place_limit_order(self, symbol: str, side: str, amount: float, price: float) -> Optional[Dict]:
        """Place simulated limit order"""
        try:
            order_id = f"demo_{self.order_counter}"
            self.order_counter += 1
            
            order = {
                'id': order_id,
                'symbol': symbol,
                'type': 'limit',
                'side': side,
                'amount': amount,
                'price': price,
                'status': 'open',
                'filled': 0,
                'timestamp': int(time.time() * 1000),
                'fee': {'cost': 0, 'currency': 'USDT'}
            }
            
            self.open_orders[order_id] = order
            
            self.logger.info(f"Demo limit order placed: {side} {amount} {symbol} @ {price}")
            return order
            
        except Exception as e:
            self.logger.error(f"Error placing demo limit order: {e}")
            return None
    
    async def place_stop_loss_order(self, symbol: str, side: str, amount: float, stop_price: float) -> Optional[Dict]:
        """Place simulated stop-loss order"""
        return await self.place_limit_order(symbol, side, amount, stop_price)
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel simulated order"""
        try:
            if order_id in self.open_orders:
                del self.open_orders[order_id]
                self.logger.info(f"Demo order cancelled: {order_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error cancelling demo order: {e}")
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Dict]:
        """Get simulated order status"""
        return self.open_orders.get(order_id)
    
    async def get_trading_fees(self, symbol: str) -> Optional[Dict]:
        """Get simulated trading fees"""
        return {
            'maker': 0.001,
            'taker': 0.001,
            'percentage': True
        }
    
    async def get_positions(self) -> Optional[List[Dict]]:
        """Get simulated positions"""
        positions = []
        
        for symbol in self.demo_prices.keys():
            base_currency = symbol.split('/')[0]
            balance = self.demo_balance.get(base_currency, 0)
            
            if balance > 0:
                price = await self.get_current_price(symbol)
                positions.append({
                    'symbol': symbol,
                    'side': 'long',
                    'size': balance,
                    'notional': balance * price if price else 0,
                    'unrealizedPnl': 0,
                    'percentage': 0
                })
        
        return positions
    
    async def get_market_info(self, symbol: str) -> Optional[Dict]:
        """Get simulated market info"""
        return {
            'symbol': symbol,
            'base': symbol.split('/')[0],
            'quote': symbol.split('/')[1],
            'active': True,
            'precision': {'amount': 8, 'price': 4},
            'limits': {
                'amount': {'min': 0.00001, 'max': 1000000},
                'price': {'min': 0.0001, 'max': 1000000}
            }
        }
    
    async def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol is tradable"""
        return symbol in self.demo_prices
    
    async def get_minimum_order_size(self, symbol: str) -> Optional[float]:
        """Get minimum order size"""
        return 0.00001
    
    def _update_demo_balance(self, symbol: str, side: str, amount: float, price: float):
        """Update demo balance after trade"""
        base_currency = symbol.split('/')[0]
        quote_currency = symbol.split('/')[1]
        
        if side.lower() == 'buy':
            # Buy: decrease quote currency, increase base currency
            cost = amount * price
            self.demo_balance[quote_currency] -= cost
            self.demo_balance[base_currency] += amount
        else:
            # Sell: increase quote currency, decrease base currency
            proceeds = amount * price
            self.demo_balance[quote_currency] += proceeds
            self.demo_balance[base_currency] -= amount
        
        # Ensure balances don't go negative
        for currency in self.demo_balance:
            self.demo_balance[currency] = max(0, self.demo_balance[currency])