"""
Logging configuration and utilities
"""
import logging
import logging.handlers
import os
from datetime import datetime

def setup_logger(name: str, level: str = None) -> logging.Logger:
    """Setup logger with file and console handlers"""
    
    # Get log level from environment or use INFO as default
    log_level = level or os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(name)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = os.getenv('LOG_FILE', 'trading_bot.log')
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    except:
        pass  # Use current directory if path creation fails
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler for critical issues
    error_log_file = log_file.replace('.log', '_errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    return logger

class TradingBotFilter(logging.Filter):
    """Custom filter for trading bot logs"""
    
    def filter(self, record):
        # Add custom fields to log records
        record.bot_session = getattr(record, 'bot_session', 'default')
        return True

def log_trade(logger: logging.Logger, action: str, symbol: str, amount: float, price: float, **kwargs):
    """Log trading actions with structured format"""
    
    extra_info = ' '.join([f"{k}={v}" for k, v in kwargs.items()])
    
    log_message = f"TRADE - {action.upper()} {symbol} Amount:{amount:.8f} Price:${price:.4f}"
    if extra_info:
        log_message += f" {extra_info}"
    
    logger.info(log_message)

def log_error_with_context(logger: logging.Logger, error: Exception, context: dict = None):
    """Log errors with additional context"""
    
    error_message = f"ERROR: {str(error)}"
    
    if context:
        context_str = ' '.join([f"{k}={v}" for k, v in context.items()])
        error_message += f" Context: {context_str}"
    
    logger.error(error_message, exc_info=True)

def setup_trading_logger() -> logging.Logger:
    """Setup specialized logger for trading operations"""
    
    logger = setup_logger('trading_operations')
    
    # Add custom filter
    custom_filter = TradingBotFilter()
    for handler in logger.handlers:
        handler.addFilter(custom_filter)
    
    return logger
