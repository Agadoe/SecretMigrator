"""
Helper utilities and common functions
"""
import asyncio
import time
import hashlib
import hmac
import base64
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100

def format_currency(amount: float, currency: str = 'USD', decimals: int = 2) -> str:
    """Format currency amount with proper symbols"""
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'BTC': '₿',
        'ETH': 'Ξ'
    }
    
    symbol = currency_symbols.get(currency.upper(), currency.upper())
    
    if currency.upper() in ['BTC', 'ETH']:
        decimals = 8
    
    return f"{symbol}{amount:,.{decimals}f}"

def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage with proper sign"""
    sign = '+' if value > 0 else ''
    return f"{sign}{value:.{decimals}f}%"

def truncate_float(value: float, decimals: int) -> float:
    """Truncate float to specified decimal places"""
    multiplier = 10 ** decimals
    return int(value * multiplier) / multiplier

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, return default if division by zero"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default

def timestamp_to_datetime(timestamp: Union[int, float], unit: str = 's') -> datetime:
    """Convert timestamp to datetime object"""
    try:
        if unit == 'ms':
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp)
    except (ValueError, OSError):
        return datetime.now()

def datetime_to_timestamp(dt: datetime, unit: str = 's') -> Union[int, float]:
    """Convert datetime to timestamp"""
    timestamp = dt.timestamp()
    if unit == 'ms':
        timestamp *= 1000
        return int(timestamp)
    return timestamp

def generate_order_id(symbol: str, side: str, timestamp: float = None) -> str:
    """Generate unique order ID"""
    if timestamp is None:
        timestamp = time.time()
    
    data = f"{symbol}_{side}_{timestamp}"
    return hashlib.md5(data.encode()).hexdigest()[:12]

def validate_trading_pair(symbol: str) -> bool:
    """Validate trading pair format"""
    try:
        if '/' not in symbol:
            return False
        
        base, quote = symbol.split('/')
        
        # Check if both parts are valid
        if len(base) < 2 or len(quote) < 2:
            return False
        
        # Check for valid characters (alphanumeric)
        if not (base.isalnum() and quote.isalnum()):
            return False
        
        return True
        
    except Exception:
        return False

def calculate_trade_fee(amount: float, price: float, fee_rate: float) -> float:
    """Calculate trading fee"""
    trade_value = amount * price
    return trade_value * fee_rate

def calculate_position_value(amount: float, price: float) -> float:
    """Calculate position value in quote currency"""
    return amount * price

def is_within_percentage(value: float, target: float, percentage: float) -> bool:
    """Check if value is within percentage range of target"""
    tolerance = abs(target * percentage / 100)
    return abs(value - target) <= tolerance

def round_to_precision(value: float, precision: int) -> float:
    """Round value to specified precision"""
    return round(value, precision)

def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp value between min and max"""
    return max(min_value, min(value, max_value))

async def retry_async(func, max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry async function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            await asyncio.sleep(delay * (backoff ** attempt))

def create_api_signature(secret: str, message: str, algorithm: str = 'sha256') -> str:
    """Create API signature using HMAC"""
    if algorithm.lower() == 'sha256':
        hash_func = hashlib.sha256
    elif algorithm.lower() == 'sha1':
        hash_func = hashlib.sha1
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hash_func
    )
    
    return base64.b64encode(signature.digest()).decode('utf-8')

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """Flatten nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def safe_get(dictionary: Dict, keys: Union[str, List[str]], default: Any = None) -> Any:
    """Safely get nested dictionary value"""
    if isinstance(keys, str):
        keys = [keys]
    
    current = dictionary
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current

def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio for returns"""
    if not returns or len(returns) < 2:
        return 0.0
    
    try:
        import statistics
        
        mean_return = statistics.mean(returns)
        std_dev = statistics.stdev(returns)
        
        if std_dev == 0:
            return 0.0
        
        return (mean_return - risk_free_rate) / std_dev
        
    except Exception:
        return 0.0

def calculate_max_drawdown(values: List[float]) -> float:
    """Calculate maximum drawdown from a series of values"""
    if not values or len(values) < 2:
        return 0.0
    
    peak = values[0]
    max_drawdown = 0.0
    
    for value in values[1:]:
        if value > peak:
            peak = value
        else:
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
    
    return max_drawdown * 100  # Return as percentage

def format_time_duration(seconds: float) -> str:
    """Format time duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"

def validate_config_value(value: Any, expected_type: type, default: Any = None) -> Any:
    """Validate and convert configuration value"""
    try:
        if value is None:
            return default
        
        if expected_type == bool:
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        
        return expected_type(value)
        
    except (ValueError, TypeError):
        return default

def get_trading_session_info() -> Dict[str, Any]:
    """Get current trading session information"""
    now = datetime.utcnow()
    
    # Market sessions (approximate)
    sessions = {
        'asian': {'start': 0, 'end': 9},      # UTC hours
        'european': {'start': 7, 'end': 16},
        'american': {'start': 13, 'end': 22}
    }
    
    current_hour = now.hour
    active_sessions = []
    
    for session, times in sessions.items():
        if times['start'] <= current_hour <= times['end']:
            active_sessions.append(session)
    
    return {
        'current_time': now.isoformat(),
        'current_hour_utc': current_hour,
        'active_sessions': active_sessions,
        'is_weekend': now.weekday() >= 5
    }

class CircularBuffer:
    """Simple circular buffer for storing fixed-size data"""
    
    def __init__(self, size: int):
        self.size = size
        self.buffer = []
        self.index = 0
        self.is_full = False
    
    def append(self, item: Any):
        """Add item to buffer"""
        if len(self.buffer) < self.size:
            self.buffer.append(item)
        else:
            self.buffer[self.index] = item
            self.is_full = True
        
        self.index = (self.index + 1) % self.size
    
    def get_all(self) -> List[Any]:
        """Get all items in chronological order"""
        if not self.is_full:
            return self.buffer.copy()
        
        return self.buffer[self.index:] + self.buffer[:self.index]
    
    def get_latest(self, count: int = 1) -> List[Any]:
        """Get latest N items"""
        all_items = self.get_all()
        return all_items[-count:] if count <= len(all_items) else all_items
    
    def clear(self):
        """Clear the buffer"""
        self.buffer.clear()
        self.index = 0
        self.is_full = False
