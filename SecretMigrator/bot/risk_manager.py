"""
Risk management module for controlling trading exposure and losses
"""
import logging
import time
from typing import Dict, Optional, Any
from utils.logger import setup_logger
from utils.database import DatabaseManager

class RiskManager:
    """Risk management system for trading bot"""
    
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger('risk_manager')
        
        # Risk tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_reset_time = self._get_daily_reset_time()
        
        # Position tracking
        self.total_exposure = 0.0
        self.open_positions_count = 0
        
        # Risk limits
        self.max_daily_loss = config.MAX_DAILY_LOSS
        self.max_open_positions = config.MAX_OPEN_POSITIONS
        self.max_position_size = config.MAX_POSITION_SIZE
        self.position_size_percentage = config.POSITION_SIZE_PERCENTAGE
        
    def _get_daily_reset_time(self) -> float:
        """Get the time for daily reset (midnight UTC)"""
        import datetime
        now = datetime.datetime.utcnow()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        return tomorrow.timestamp()
    
    async def check_daily_limits(self) -> bool:
        """Check if daily trading limits are exceeded"""
        try:
            current_time = time.time()
            
            # Reset daily counters if new day
            if current_time >= self.daily_reset_time:
                await self._reset_daily_counters()
            
            # Check daily loss limit
            if abs(self.daily_pnl) >= self.max_daily_loss:
                self.logger.warning(f"Daily loss limit reached: ${abs(self.daily_pnl):.2f}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking daily limits: {e}")
            return False
    
    async def _reset_daily_counters(self):
        """Reset daily counters"""
        try:
            self.logger.info("Resetting daily risk counters")
            
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.daily_reset_time = self._get_daily_reset_time()
            
        except Exception as e:
            self.logger.error(f"Error resetting daily counters: {e}")
    
    async def can_open_position(self, symbol: str, prediction: Dict) -> bool:
        """Check if a new position can be opened"""
        try:
            # Check daily limits
            if not await self.check_daily_limits():
                self.logger.info(f"Cannot open position for {symbol}: daily limits exceeded")
                return False
            
            # Check maximum open positions
            if self.open_positions_count >= self.max_open_positions:
                self.logger.info(f"Cannot open position for {symbol}: max positions limit reached")
                return False
            
            # Check prediction confidence
            if prediction['confidence'] < self.config.CONFIDENCE_THRESHOLD:
                self.logger.info(f"Cannot open position for {symbol}: confidence too low ({prediction['confidence']:.3f})")
                return False
            
            # Check if symbol is already traded (avoid multiple positions in same symbol)
            # This would need to be implemented based on active positions tracking
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking if position can be opened for {symbol}: {e}")
            return False
    
    async def calculate_position_size(self, symbol: str, price: float, prediction: Dict) -> float:
        """Calculate appropriate position size based on risk management rules"""
        try:
            # Get account balance (this would need to be passed or fetched)
            # For now, use a base calculation
            
            # Calculate position size based on percentage of balance
            base_position_value = self.max_position_size * (self.position_size_percentage / 100.0)
            
            # Adjust based on prediction confidence
            confidence_multiplier = min(prediction['confidence'] / self.config.CONFIDENCE_THRESHOLD, 1.5)
            adjusted_position_value = base_position_value * confidence_multiplier
            
            # Calculate position size in base currency
            position_size = adjusted_position_value / price
            
            # Apply maximum position size limit
            if adjusted_position_value > self.max_position_size:
                position_size = self.max_position_size / price
            
            # Ensure minimum position size (exchange-specific)
            min_position_size = 0.001  # This should come from exchange info
            if position_size < min_position_size:
                self.logger.warning(f"Calculated position size too small for {symbol}: {position_size}")
                return 0.0
            
            self.logger.info(f"Calculated position size for {symbol}: {position_size:.8f} (${adjusted_position_value:.2f})")
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size for {symbol}: {e}")
            return 0.0
    
    async def calculate_stop_loss(self, symbol: str, entry_price: float, side: str) -> float:
        """Calculate stop-loss price"""
        try:
            stop_loss_percentage = self.config.STOP_LOSS_PERCENTAGE / 100.0
            
            if side.lower() == 'long' or side.lower() == 'buy':
                # For long positions, stop loss is below entry price
                stop_loss = entry_price * (1 - stop_loss_percentage)
            else:
                # For short positions, stop loss is above entry price
                stop_loss = entry_price * (1 + stop_loss_percentage)
            
            return stop_loss
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss for {symbol}: {e}")
            return entry_price
    
    async def calculate_take_profit(self, symbol: str, entry_price: float, side: str) -> float:
        """Calculate take-profit price"""
        try:
            take_profit_percentage = self.config.TAKE_PROFIT_PERCENTAGE / 100.0
            
            if side.lower() == 'long' or side.lower() == 'buy':
                # For long positions, take profit is above entry price
                take_profit = entry_price * (1 + take_profit_percentage)
            else:
                # For short positions, take profit is below entry price
                take_profit = entry_price * (1 - take_profit_percentage)
            
            return take_profit
            
        except Exception as e:
            self.logger.error(f"Error calculating take profit for {symbol}: {e}")
            return entry_price
    
    async def update_daily_pnl(self, pnl: float):
        """Update daily P&L tracking"""
        try:
            self.daily_pnl += pnl
            self.daily_trades += 1
            
            self.logger.info(f"Updated daily P&L: ${self.daily_pnl:.2f} (Trades: {self.daily_trades})")
            
            # Check if daily loss limit is approached
            if abs(self.daily_pnl) >= self.max_daily_loss * 0.8:  # 80% of limit
                self.logger.warning(f"Approaching daily loss limit: ${abs(self.daily_pnl):.2f}")
            
        except Exception as e:
            self.logger.error(f"Error updating daily P&L: {e}")
    
    async def update_position_count(self, change: int):
        """Update open positions count"""
        try:
            self.open_positions_count += change
            
            # Ensure count doesn't go negative
            if self.open_positions_count < 0:
                self.open_positions_count = 0
            
            self.logger.debug(f"Open positions count: {self.open_positions_count}")
            
        except Exception as e:
            self.logger.error(f"Error updating position count: {e}")
    
    async def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics"""
        try:
            current_time = time.time()
            
            # Reset daily counters if new day
            if current_time >= self.daily_reset_time:
                await self._reset_daily_counters()
            
            metrics = {
                'daily_pnl': self.daily_pnl,
                'daily_trades': self.daily_trades,
                'open_positions': self.open_positions_count,
                'max_positions': self.max_open_positions,
                'daily_loss_limit': self.max_daily_loss,
                'daily_loss_used': abs(self.daily_pnl),
                'daily_loss_remaining': max(0, self.max_daily_loss - abs(self.daily_pnl)),
                'risk_level': self._calculate_risk_level(),
                'can_trade': await self.check_daily_limits()
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting risk metrics: {e}")
            return {}
    
    def _calculate_risk_level(self) -> str:
        """Calculate current risk level"""
        try:
            # Risk level based on daily P&L usage
            pnl_usage = abs(self.daily_pnl) / self.max_daily_loss
            
            if pnl_usage < 0.3:
                return "LOW"
            elif pnl_usage < 0.6:
                return "MEDIUM"
            elif pnl_usage < 0.8:
                return "HIGH"
            else:
                return "CRITICAL"
                
        except Exception as e:
            self.logger.error(f"Error calculating risk level: {e}")
            return "UNKNOWN"
    
    async def emergency_stop_check(self) -> bool:
        """Check if emergency stop should be triggered"""
        try:
            # Emergency stop conditions
            emergency_conditions = [
                abs(self.daily_pnl) >= self.max_daily_loss,  # Daily loss limit exceeded
                self.daily_pnl <= -self.max_daily_loss * 1.2,  # Severe losses
            ]
            
            if any(emergency_conditions):
                self.logger.critical("Emergency stop conditions met!")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking emergency stop: {e}")
            return True  # Err on the side of caution
    
    async def validate_trade_parameters(self, symbol: str, side: str, amount: float, price: float) -> Dict[str, Any]:
        """Validate trade parameters against risk rules"""
        try:
            validation_result = {
                'valid': True,
                'warnings': [],
                'errors': []
            }
            
            # Check position size
            position_value = amount * price
            if position_value > self.max_position_size:
                validation_result['errors'].append(f"Position size too large: ${position_value:.2f} > ${self.max_position_size:.2f}")
                validation_result['valid'] = False
            
            # Check minimum position size
            if position_value < 10.0:  # Minimum $10 position
                validation_result['warnings'].append(f"Position size very small: ${position_value:.2f}")
            
            # Check if daily limits allow this trade
            if not await self.check_daily_limits():
                validation_result['errors'].append("Daily trading limits exceeded")
                validation_result['valid'] = False
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating trade parameters: {e}")
            return {'valid': False, 'errors': [f"Validation error: {e}"], 'warnings': []}
