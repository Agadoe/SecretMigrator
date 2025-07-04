"""
Backtesting engine for testing trading strategies
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import asyncio
from bot.ai_predictor import AIPredictor
from bot.risk_manager import RiskManager
from utils.logger import setup_logger
import json

class BacktestEngine:
    """Backtesting engine for evaluating trading strategies"""
    
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger('backtest_engine')
        
        # Initialize components
        self.ai_predictor = AIPredictor(config)
        self.risk_manager = RiskManager(config)
        
        # Backtest state
        self.initial_balance = 10000.0  # Starting balance
        self.current_balance = self.initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_drawdown = 0.0
        self.peak_balance = self.initial_balance
        
        # Trading parameters
        self.transaction_cost = 0.001  # 0.1% per trade
        self.slippage = 0.0005  # 0.05% slippage
    
    async def run_backtest(self, 
                          symbol: str, 
                          start_date: str, 
                          end_date: str, 
                          timeframe: str = '1h') -> Dict[str, Any]:
        """Run backtest for a specific symbol and date range"""
        try:
            self.logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
            
            # Reset backtest state
            self._reset_backtest()
            
            # Load historical data
            historical_data = await self._load_historical_data(symbol, start_date, end_date, timeframe)
            
            if historical_data.empty:
                raise ValueError("No historical data available for backtesting")
            
            # Train AI model on initial data
            training_data = historical_data.iloc[:int(len(historical_data) * 0.3)]  # Use first 30% for training
            await self.ai_predictor.train_model(symbol, training_data)
            
            # Run backtest simulation
            await self._simulate_trading(symbol, historical_data)
            
            # Calculate performance metrics
            results = self._calculate_performance_metrics()
            
            self.logger.info(f"Backtest completed. Total return: {results['total_return']:.2%}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error running backtest: {e}")
            raise
    
    async def _load_historical_data(self, symbol: str, start_date: str, end_date: str, timeframe: str) -> pd.DataFrame:
        """Load historical OHLCV data for backtesting"""
        try:
            # In a real implementation, this would fetch data from the exchange or database
            # For now, we'll generate sample data based on the date range
            
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            
            # Generate sample OHLCV data
            date_range = pd.date_range(start=start, end=end, freq='1H')
            
            # Generate realistic price data with some trend and volatility
            base_price = 45000 if 'BTC' in symbol else 3000  # Different base for different coins
            np.random.seed(42)  # For reproducible results
            
            price_changes = np.random.normal(0, 0.01, len(date_range))  # 1% volatility
            prices = [base_price]
            
            for change in price_changes[1:]:
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, base_price * 0.5))  # Prevent unrealistic drops
            
            # Create OHLCV data
            data = []
            for i, (timestamp, price) in enumerate(zip(date_range, prices)):
                volatility = abs(np.random.normal(0, 0.005))
                high = price * (1 + volatility)
                low = price * (1 - volatility)
                open_price = prices[i-1] if i > 0 else price
                close_price = price
                volume = np.random.uniform(100, 1000)
                
                data.append({
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close_price,
                    'volume': volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            self.logger.info(f"Loaded {len(df)} data points for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading historical data: {e}")
            return pd.DataFrame()
    
    async def _simulate_trading(self, symbol: str, data: pd.DataFrame):
        """Simulate trading based on AI predictions"""
        try:
            lookback_window = self.config.LOOKBACK_PERIODS
            
            for i in range(lookback_window, len(data)):
                current_timestamp = data.index[i]
                current_price = data.iloc[i]['close']
                
                # Get historical data up to current point
                historical_slice = data.iloc[:i+1]
                
                # Generate AI prediction
                prediction = await self.ai_predictor.predict(symbol, historical_slice.tail(lookback_window))
                
                if prediction:
                    await self._process_trading_signal(symbol, prediction, current_price, current_timestamp)
                
                # Update positions and check for exits
                await self._update_positions(symbol, current_price, current_timestamp)
                
                # Record equity curve
                self._record_equity_point(current_timestamp)
                
                # Update drawdown tracking
                self._update_drawdown()
            
        except Exception as e:
            self.logger.error(f"Error in trading simulation: {e}")
    
    async def _process_trading_signal(self, symbol: str, prediction: Dict, price: float, timestamp: pd.Timestamp):
        """Process trading signal from AI prediction"""
        try:
            # Check if we can open a position
            if not await self.risk_manager.can_open_position(symbol, prediction):
                return
            
            # Check if we already have a position in this symbol
            if symbol in self.positions:
                return
            
            signal = prediction['signal']
            confidence = prediction['confidence']
            
            if signal in ['BUY', 'SELL'] and confidence >= self.config.CONFIDENCE_THRESHOLD:
                # Calculate position size
                position_size = await self._calculate_backtest_position_size(symbol, price, prediction)
                
                if position_size > 0:
                    # Apply transaction costs and slippage
                    actual_price = self._apply_costs_and_slippage(price, signal)
                    
                    # Open position
                    await self._open_position(symbol, signal, position_size, actual_price, timestamp, prediction)
        
        except Exception as e:
            self.logger.error(f"Error processing trading signal: {e}")
    
    async def _calculate_backtest_position_size(self, symbol: str, price: float, prediction: Dict) -> float:
        """Calculate position size for backtesting"""
        try:
            # Use a percentage of current balance for position sizing
            position_percentage = self.config.POSITION_SIZE_PERCENTAGE / 100.0
            position_value = self.current_balance * position_percentage
            
            # Adjust based on confidence
            confidence_multiplier = min(prediction['confidence'] / self.config.CONFIDENCE_THRESHOLD, 1.5)
            adjusted_position_value = position_value * confidence_multiplier
            
            # Calculate position size
            position_size = adjusted_position_value / price
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def _apply_costs_and_slippage(self, price: float, side: str) -> float:
        """Apply transaction costs and slippage"""
        # Apply slippage
        if side == 'BUY':
            price_with_slippage = price * (1 + self.slippage)
        else:
            price_with_slippage = price * (1 - self.slippage)
        
        return price_with_slippage
    
    async def _open_position(self, symbol: str, side: str, size: float, price: float, timestamp: pd.Timestamp, prediction: Dict):
        """Open a new position"""
        try:
            # Calculate stop loss and take profit
            stop_loss = await self.risk_manager.calculate_stop_loss(symbol, price, side)
            take_profit = await self.risk_manager.calculate_take_profit(symbol, price, side)
            
            # Calculate position value and fees
            position_value = size * price
            transaction_fee = position_value * self.transaction_cost
            
            # Check if we have enough balance
            if position_value + transaction_fee > self.current_balance:
                self.logger.warning(f"Insufficient balance for position: need {position_value + transaction_fee}, have {self.current_balance}")
                return
            
            # Create position
            position = {
                'symbol': symbol,
                'side': side.lower(),
                'size': size,
                'entry_price': price,
                'entry_time': timestamp,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'unrealized_pnl': 0.0,
                'prediction': prediction
            }
            
            self.positions[symbol] = position
            
            # Update balance
            self.current_balance -= (position_value + transaction_fee)
            
            self.logger.debug(f"Opened {side} position: {symbol} {size:.8f} @ {price:.4f}")
            
        except Exception as e:
            self.logger.error(f"Error opening position: {e}")
    
    async def _update_positions(self, symbol: str, current_price: float, timestamp: pd.Timestamp):
        """Update existing positions and check for exits"""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            entry_price = position['entry_price']
            side = position['side']
            size = position['size']
            
            # Calculate unrealized P&L
            if side == 'long':
                unrealized_pnl = (current_price - entry_price) * size
            else:
                unrealized_pnl = (entry_price - current_price) * size
            
            position['unrealized_pnl'] = unrealized_pnl
            
            # Check exit conditions
            should_exit = False
            exit_reason = ""
            
            if side == 'long':
                if current_price <= position['stop_loss']:
                    should_exit = True
                    exit_reason = "STOP_LOSS"
                elif current_price >= position['take_profit']:
                    should_exit = True
                    exit_reason = "TAKE_PROFIT"
            else:  # short position
                if current_price >= position['stop_loss']:
                    should_exit = True
                    exit_reason = "STOP_LOSS"
                elif current_price <= position['take_profit']:
                    should_exit = True
                    exit_reason = "TAKE_PROFIT"
            
            if should_exit:
                await self._close_position(symbol, current_price, timestamp, exit_reason)
        
        except Exception as e:
            self.logger.error(f"Error updating positions: {e}")
    
    async def _close_position(self, symbol: str, price: float, timestamp: pd.Timestamp, reason: str):
        """Close an existing position"""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            
            # Apply costs and slippage for exit
            opposite_side = 'SELL' if position['side'] == 'long' else 'BUY'
            actual_exit_price = self._apply_costs_and_slippage(price, opposite_side)
            
            # Calculate realized P&L
            entry_price = position['entry_price']
            size = position['size']
            
            if position['side'] == 'long':
                gross_pnl = (actual_exit_price - entry_price) * size
            else:
                gross_pnl = (entry_price - actual_exit_price) * size
            
            # Calculate fees
            exit_value = size * actual_exit_price
            exit_fee = exit_value * self.transaction_cost
            
            # Net P&L after fees
            net_pnl = gross_pnl - exit_fee
            
            # Create trade record
            trade = {
                'symbol': symbol,
                'side': position['side'],
                'size': size,
                'entry_price': entry_price,
                'exit_price': actual_exit_price,
                'entry_time': position['entry_time'],
                'exit_time': timestamp,
                'gross_pnl': gross_pnl,
                'net_pnl': net_pnl,
                'exit_reason': reason,
                'prediction': position['prediction']
            }
            
            self.trades.append(trade)
            
            # Update balance
            self.current_balance += exit_value - exit_fee
            
            # Update trade statistics
            self.total_trades += 1
            if net_pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            # Remove position
            del self.positions[symbol]
            
            self.logger.debug(f"Closed position: {symbol} P&L: {net_pnl:.2f} ({reason})")
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
    
    def _record_equity_point(self, timestamp: pd.Timestamp):
        """Record current equity for equity curve"""
        # Calculate current equity (balance + unrealized P&L)
        unrealized_pnl = sum(pos['unrealized_pnl'] for pos in self.positions.values())
        current_equity = self.current_balance + unrealized_pnl
        
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': current_equity,
            'balance': self.current_balance,
            'unrealized_pnl': unrealized_pnl
        })
    
    def _update_drawdown(self):
        """Update maximum drawdown tracking"""
        if not self.equity_curve:
            return
        
        current_equity = self.equity_curve[-1]['equity']
        
        if current_equity > self.peak_balance:
            self.peak_balance = current_equity
        
        drawdown = (self.peak_balance - current_equity) / self.peak_balance
        
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
    
    def _reset_backtest(self):
        """Reset backtest state"""
        self.current_balance = self.initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_drawdown = 0.0
        self.peak_balance = self.initial_balance
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        try:
            final_balance = self.equity_curve[-1]['equity'] if self.equity_curve else self.initial_balance
            
            # Basic metrics
            total_return = (final_balance - self.initial_balance) / self.initial_balance
            win_rate = self.winning_trades / max(self.total_trades, 1)
            
            # Calculate returns for advanced metrics
            returns = []
            if len(self.equity_curve) > 1:
                for i in range(1, len(self.equity_curve)):
                    prev_equity = self.equity_curve[i-1]['equity']
                    curr_equity = self.equity_curve[i]['equity']
                    if prev_equity > 0:
                        returns.append((curr_equity - prev_equity) / prev_equity)
            
            # Advanced metrics
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            sortino_ratio = self._calculate_sortino_ratio(returns)
            calmar_ratio = total_return / max(self.max_drawdown, 0.001)
            
            # Trade statistics
            winning_trades_pnl = [t['net_pnl'] for t in self.trades if t['net_pnl'] > 0]
            losing_trades_pnl = [t['net_pnl'] for t in self.trades if t['net_pnl'] < 0]
            
            avg_winning_trade = np.mean(winning_trades_pnl) if winning_trades_pnl else 0
            avg_losing_trade = np.mean(losing_trades_pnl) if losing_trades_pnl else 0
            
            profit_factor = abs(sum(winning_trades_pnl) / sum(losing_trades_pnl)) if losing_trades_pnl else float('inf')
            
            # Time-based metrics
            start_time = self.equity_curve[0]['timestamp'] if self.equity_curve else datetime.now()
            end_time = self.equity_curve[-1]['timestamp'] if self.equity_curve else datetime.now()
            duration_days = (end_time - start_time).days
            
            results = {
                'initial_balance': self.initial_balance,
                'final_balance': final_balance,
                'total_return': total_return,
                'total_return_pct': total_return * 100,
                'max_drawdown': self.max_drawdown,
                'max_drawdown_pct': self.max_drawdown * 100,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': calmar_ratio,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': win_rate,
                'win_rate_pct': win_rate * 100,
                'avg_winning_trade': avg_winning_trade,
                'avg_losing_trade': avg_losing_trade,
                'profit_factor': profit_factor,
                'duration_days': duration_days,
                'trades_per_day': self.total_trades / max(duration_days, 1),
                'equity_curve': self.equity_curve,
                'trades': self.trades
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {}
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0.0
        
        try:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
            
            return (mean_return - risk_free_rate) / std_return
            
        except Exception:
            return 0.0
    
    def _calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sortino ratio (uses downside deviation instead of total volatility)"""
        if not returns or len(returns) < 2:
            return 0.0
        
        try:
            mean_return = np.mean(returns)
            downside_returns = [r for r in returns if r < risk_free_rate]
            
            if not downside_returns:
                return float('inf') if mean_return > risk_free_rate else 0.0
            
            downside_deviation = np.std(downside_returns)
            
            if downside_deviation == 0:
                return 0.0
            
            return (mean_return - risk_free_rate) / downside_deviation
            
        except Exception:
            return 0.0
    
    async def run_parameter_optimization(self, 
                                       symbol: str, 
                                       start_date: str, 
                                       end_date: str,
                                       parameters: Dict[str, List]) -> Dict[str, Any]:
        """Run parameter optimization using grid search"""
        try:
            self.logger.info("Starting parameter optimization")
            
            results = []
            best_result = None
            best_return = float('-inf')
            
            # Generate parameter combinations
            param_combinations = self._generate_parameter_combinations(parameters)
            
            for i, params in enumerate(param_combinations):
                self.logger.info(f"Testing parameter set {i+1}/{len(param_combinations)}: {params}")
                
                # Update config with test parameters
                original_config = self._backup_config()
                self._apply_parameters(params)
                
                try:
                    # Run backtest
                    result = await self.run_backtest(symbol, start_date, end_date)
                    result['parameters'] = params.copy()
                    results.append(result)
                    
                    # Track best result
                    if result['total_return'] > best_return:
                        best_return = result['total_return']
                        best_result = result
                    
                except Exception as e:
                    self.logger.error(f"Error in parameter test {i+1}: {e}")
                    continue
                
                finally:
                    # Restore original config
                    self._restore_config(original_config)
            
            optimization_results = {
                'best_parameters': best_result['parameters'] if best_result else {},
                'best_result': best_result,
                'all_results': results,
                'total_combinations_tested': len(results)
            }
            
            self.logger.info(f"Parameter optimization completed. Best return: {best_return:.2%}")
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Error in parameter optimization: {e}")
            raise
    
    def _generate_parameter_combinations(self, parameters: Dict[str, List]) -> List[Dict]:
        """Generate all combinations of parameters"""
        import itertools
        
        keys = parameters.keys()
        values = parameters.values()
        
        combinations = []
        for combination in itertools.product(*values):
            combinations.append(dict(zip(keys, combination)))
        
        return combinations
    
    def _backup_config(self) -> Dict:
        """Backup current configuration"""
        return {
            'CONFIDENCE_THRESHOLD': self.config.CONFIDENCE_THRESHOLD,
            'STOP_LOSS_PERCENTAGE': self.config.STOP_LOSS_PERCENTAGE,
            'TAKE_PROFIT_PERCENTAGE': self.config.TAKE_PROFIT_PERCENTAGE,
            'POSITION_SIZE_PERCENTAGE': self.config.POSITION_SIZE_PERCENTAGE,
            'MAX_POSITION_SIZE': self.config.MAX_POSITION_SIZE
        }
    
    def _apply_parameters(self, params: Dict):
        """Apply test parameters to config"""
        for key, value in params.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def _restore_config(self, backup: Dict):
        """Restore configuration from backup"""
        for key, value in backup.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def generate_backtest_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive backtest report"""
        try:
            report = []
            report.append("=" * 60)
            report.append("BACKTEST REPORT")
            report.append("=" * 60)
            report.append("")
            
            # Performance Summary
            report.append("PERFORMANCE SUMMARY")
            report.append("-" * 20)
            report.append(f"Initial Balance:      ${results['initial_balance']:,.2f}")
            report.append(f"Final Balance:        ${results['final_balance']:,.2f}")
            report.append(f"Total Return:         {results['total_return_pct']:+.2f}%")
            report.append(f"Max Drawdown:         {results['max_drawdown_pct']:-.2f}%")
            report.append("")
            
            # Risk Metrics
            report.append("RISK METRICS")
            report.append("-" * 12)
            report.append(f"Sharpe Ratio:         {results['sharpe_ratio']:.3f}")
            report.append(f"Sortino Ratio:        {results['sortino_ratio']:.3f}")
            report.append(f"Calmar Ratio:         {results['calmar_ratio']:.3f}")
            report.append("")
            
            # Trading Statistics
            report.append("TRADING STATISTICS")
            report.append("-" * 18)
            report.append(f"Total Trades:         {results['total_trades']}")
            report.append(f"Winning Trades:       {results['winning_trades']}")
            report.append(f"Losing Trades:        {results['losing_trades']}")
            report.append(f"Win Rate:             {results['win_rate_pct']:.1f}%")
            report.append(f"Avg Winning Trade:    ${results['avg_winning_trade']:,.2f}")
            report.append(f"Avg Losing Trade:     ${results['avg_losing_trade']:,.2f}")
            report.append(f"Profit Factor:        {results['profit_factor']:.2f}")
            report.append("")
            
            # Duration and Frequency
            report.append("TIME ANALYSIS")
            report.append("-" * 13)
            report.append(f"Duration (days):       {results['duration_days']}")
            report.append(f"Trades per Day:       {results['trades_per_day']:.2f}")
            report.append("")
            
            return "\n".join(report)
            
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return "Error generating backtest report"

