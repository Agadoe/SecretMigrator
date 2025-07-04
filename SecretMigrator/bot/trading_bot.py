"""
Main trading bot orchestrator
"""
import asyncio
import logging
from typing import Dict, Any
from .ai_predictor import AIPredictor
from .telegram_handler import TelegramHandler
from .exchange_manager import ExchangeManager
from .demo_exchange import DemoExchangeManager
from .data_manager import DataManager
from .risk_manager import RiskManager
from .signals_aggregator import SignalsAggregator
from utils.logger import setup_logger
from utils.database import DatabaseManager
import time

class TradingBot:
    """Main trading bot class that orchestrates all components"""
    
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger('trading_bot')
        
        # Initialize components
        self.db_manager = DatabaseManager(config.DATABASE_URL)
        
        # Use demo exchange in demo mode, otherwise try real exchange
        if config.TRADING_MODE == 'demo':
            self.logger.info("Initializing in demo mode")
            self.exchange_manager = DemoExchangeManager(config)
        else:
            try:
                self.exchange_manager = ExchangeManager(config)
            except Exception as e:
                self.logger.warning(f"Failed to initialize real exchange, using demo mode: {e}")
                self.exchange_manager = DemoExchangeManager(config)
        
        self.data_manager = DataManager(config, self.exchange_manager)
        self.ai_predictor = AIPredictor(config)
        self.risk_manager = RiskManager(config)
        self.signals_aggregator = SignalsAggregator(config)
        self.telegram_handler = TelegramHandler(config, self)
        
        self.running = False
        self.last_prediction_time = {}
        self.active_positions = {}
        
    async def start(self):
        """Start the trading bot"""
        try:
            # Validate configuration
            self.config.validate()
            
            # Initialize database
            await self.db_manager.initialize()
            
            # Initialize exchange connection
            await self.exchange_manager.initialize()
            
            # Start Telegram bot
            await self.telegram_handler.start()
            
            # Start main trading loop
            self.running = True
            self.logger.info("Trading bot started successfully")
            
            # Start concurrent tasks
            await asyncio.gather(
                self.trading_loop(),
                self.data_collection_loop(),
                self.monitoring_loop()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to start trading bot: {e}")
            raise
    
    async def stop(self):
        """Stop the trading bot"""
        self.running = False
        
        # Close all positions
        await self.close_all_positions()
        
        # Stop components
        await self.telegram_handler.stop()
        await self.exchange_manager.close()
        
        self.logger.info("Trading bot stopped")
    
    async def trading_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                for symbol in self.config.TRADING_PAIRS:
                    await self.process_trading_signal(symbol)
                
                # Sleep between iterations
                await asyncio.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(30)
    
    async def data_collection_loop(self):
        """Data collection and processing loop"""
        while self.running:
            try:
                # Collect market data
                await self.data_manager.collect_market_data()
                
                # Update AI models periodically
                await self.ai_predictor.update_models()
                
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in data collection loop: {e}")
                await asyncio.sleep(60)
    
    async def monitoring_loop(self):
        """Monitor active positions and risk management"""
        while self.running:
            try:
                # Check active positions
                await self.monitor_positions()
                
                # Risk management checks
                await self.risk_manager.check_daily_limits()
                
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def process_trading_signal(self, symbol: str):
        """Process trading signals for a specific symbol"""
        try:
            current_time = time.time()
            
            # Check if enough time has passed since last prediction
            if (symbol not in self.last_prediction_time or 
                current_time - self.last_prediction_time[symbol] >= self.config.PREDICTION_INTERVAL):
                
                # Get market data
                market_data = await self.data_manager.get_market_data(symbol)
                
                if market_data is not None and len(market_data) > 0:
                    # Generate AI prediction
                    prediction = await self.ai_predictor.predict(symbol, market_data)
                    
                    if prediction:
                        # Evaluate trading opportunity
                        await self.evaluate_trading_opportunity(symbol, prediction, market_data)
                    
                    self.last_prediction_time[symbol] = current_time
                    
        except Exception as e:
            self.logger.error(f"Error processing trading signal for {symbol}: {e}")
    
    async def evaluate_trading_opportunity(self, symbol: str, prediction: Dict, market_data: Dict):
        """Evaluate and execute trading opportunities"""
        try:
            # Check risk management constraints
            if not await self.risk_manager.can_open_position(symbol, prediction):
                return
            
            # Get current price
            current_price = await self.exchange_manager.get_current_price(symbol)
            
            if current_price is None:
                return
            
            # Calculate position size
            position_size = await self.risk_manager.calculate_position_size(
                symbol, current_price, prediction
            )
            
            if position_size <= 0:
                return
            
            # Execute trade based on prediction
            if prediction['signal'] == 'BUY' and prediction['confidence'] >= self.config.CONFIDENCE_THRESHOLD:
                await self.execute_buy_order(symbol, position_size, current_price, prediction)
            elif prediction['signal'] == 'SELL' and prediction['confidence'] >= self.config.CONFIDENCE_THRESHOLD:
                await self.execute_sell_order(symbol, position_size, current_price, prediction)
                
        except Exception as e:
            self.logger.error(f"Error evaluating trading opportunity for {symbol}: {e}")
    
    async def execute_buy_order(self, symbol: str, amount: float, price: float, prediction: Dict):
        """Execute a buy order"""
        try:
            # Place market buy order
            order = await self.exchange_manager.place_market_order(symbol, 'buy', amount)
            
            if order:
                # Calculate stop loss and take profit levels
                stop_loss = price * (1 - self.config.STOP_LOSS_PERCENTAGE / 100)
                take_profit = price * (1 + self.config.TAKE_PROFIT_PERCENTAGE / 100)
                
                # Store position information
                position = {
                    'symbol': symbol,
                    'side': 'long',
                    'amount': amount,
                    'entry_price': price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'timestamp': time.time(),
                    'order_id': order['id'],
                    'prediction': prediction
                }
                
                self.active_positions[order['id']] = position
                
                # Save to database
                await self.db_manager.save_trade(position)
                
                # Send notification
                await self.telegram_handler.send_trade_notification(position, 'OPENED')
                
                self.logger.info(f"Opened long position for {symbol}: {amount} at {price}")
                
        except Exception as e:
            self.logger.error(f"Error executing buy order for {symbol}: {e}")
    
    async def execute_sell_order(self, symbol: str, amount: float, price: float, prediction: Dict):
        """Execute a sell order"""
        try:
            # Place market sell order
            order = await self.exchange_manager.place_market_order(symbol, 'sell', amount)
            
            if order:
                # Calculate stop loss and take profit levels
                stop_loss = price * (1 + self.config.STOP_LOSS_PERCENTAGE / 100)
                take_profit = price * (1 - self.config.TAKE_PROFIT_PERCENTAGE / 100)
                
                # Store position information
                position = {
                    'symbol': symbol,
                    'side': 'short',
                    'amount': amount,
                    'entry_price': price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'timestamp': time.time(),
                    'order_id': order['id'],
                    'prediction': prediction
                }
                
                self.active_positions[order['id']] = position
                
                # Save to database
                await self.db_manager.save_trade(position)
                
                # Send notification
                await self.telegram_handler.send_trade_notification(position, 'OPENED')
                
                self.logger.info(f"Opened short position for {symbol}: {amount} at {price}")
                
        except Exception as e:
            self.logger.error(f"Error executing sell order for {symbol}: {e}")
    
    async def monitor_positions(self):
        """Monitor active positions for stop loss and take profit"""
        for order_id, position in list(self.active_positions.items()):
            try:
                current_price = await self.exchange_manager.get_current_price(position['symbol'])
                
                if current_price is None:
                    continue
                
                should_close = False
                close_reason = ""
                
                # Check stop loss and take profit
                if position['side'] == 'long':
                    if current_price <= position['stop_loss']:
                        should_close = True
                        close_reason = "STOP_LOSS"
                    elif current_price >= position['take_profit']:
                        should_close = True
                        close_reason = "TAKE_PROFIT"
                else:  # short position
                    if current_price >= position['stop_loss']:
                        should_close = True
                        close_reason = "STOP_LOSS"
                    elif current_price <= position['take_profit']:
                        should_close = True
                        close_reason = "TAKE_PROFIT"
                
                if should_close:
                    await self.close_position(order_id, close_reason)
                    
            except Exception as e:
                self.logger.error(f"Error monitoring position {order_id}: {e}")
    
    async def close_position(self, order_id: str, reason: str):
        """Close a specific position"""
        try:
            if order_id not in self.active_positions:
                return
            
            position = self.active_positions[order_id]
            
            # Place opposite order to close position
            opposite_side = 'sell' if position['side'] == 'long' else 'buy'
            close_order = await self.exchange_manager.place_market_order(
                position['symbol'], opposite_side, position['amount']
            )
            
            if close_order:
                # Calculate profit/loss
                current_price = await self.exchange_manager.get_current_price(position['symbol'])
                
                if position['side'] == 'long':
                    pnl = (current_price - position['entry_price']) * position['amount']
                else:
                    pnl = (position['entry_price'] - current_price) * position['amount']
                
                # Update position with close information
                position.update({
                    'close_price': current_price,
                    'close_time': time.time(),
                    'close_reason': reason,
                    'pnl': pnl,
                    'status': 'closed'
                })
                
                # Update database
                await self.db_manager.update_trade(order_id, position)
                
                # Send notification
                await self.telegram_handler.send_trade_notification(position, 'CLOSED')
                
                # Remove from active positions
                del self.active_positions[order_id]
                
                self.logger.info(f"Closed position {order_id} for {position['symbol']}: {reason}, P&L: {pnl}")
                
        except Exception as e:
            self.logger.error(f"Error closing position {order_id}: {e}")
    
    async def close_all_positions(self):
        """Close all active positions"""
        for order_id in list(self.active_positions.keys()):
            await self.close_position(order_id, "SHUTDOWN")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        try:
            balance = await self.exchange_manager.get_balance()
            
            return {
                'running': self.running,
                'active_positions': len(self.active_positions),
                'balance': balance,
                'trading_pairs': self.config.TRADING_PAIRS,
                'last_update': time.time()
            }
        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            return {'error': str(e)}
