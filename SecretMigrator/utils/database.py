"""
Database management utilities
"""
import sqlite3
import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime, date
import aiosqlite
from utils.logger import setup_logger

class DatabaseManager:
    """Database manager for storing trading data"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.logger = setup_logger('database_manager')
        
        # Extract database path from URL
        if database_url.startswith('sqlite:///'):
            self.db_path = database_url.replace('sqlite:///', '')
        else:
            self.db_path = 'trading_bot.db'
    
    async def initialize(self):
        """Initialize database and create tables"""
        try:
            await self.create_tables()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def create_tables(self):
        """Create necessary database tables"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Trades table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id TEXT UNIQUE NOT NULL,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        amount REAL NOT NULL,
                        entry_price REAL NOT NULL,
                        stop_loss REAL,
                        take_profit REAL,
                        close_price REAL,
                        pnl REAL,
                        status TEXT DEFAULT 'open',
                        open_time TEXT NOT NULL,
                        close_time TEXT,
                        close_reason TEXT,
                        prediction_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # OHLCV data table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS ohlcv_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        volume REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol, timeframe, timestamp)
                    )
                """)
                
                # Performance metrics table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        total_trades INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        losing_trades INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0,
                        total_volume REAL DEFAULT 0,
                        max_drawdown REAL DEFAULT 0,
                        metrics_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(date)
                    )
                """)
                
                # Bot status table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS bot_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        status TEXT NOT NULL,
                        active_positions INTEGER DEFAULT 0,
                        balance_data TEXT,
                        error_count INTEGER DEFAULT 0,
                        status_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                await db.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe ON ohlcv_data(symbol, timeframe)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_timestamp ON ohlcv_data(timestamp)")
                
                await db.commit()
                
        except Exception as e:
            self.logger.error(f"Error creating database tables: {e}")
            raise
    
    async def save_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Save trade information to database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO trades (
                        order_id, symbol, side, amount, entry_price, stop_loss, take_profit,
                        status, open_time, prediction_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_data['order_id'],
                    trade_data['symbol'],
                    trade_data['side'],
                    trade_data['amount'],
                    trade_data['entry_price'],
                    trade_data.get('stop_loss'),
                    trade_data.get('take_profit'),
                    'open',
                    datetime.fromtimestamp(trade_data['timestamp']).isoformat(),
                    json.dumps(trade_data.get('prediction', {}))
                ))
                
                await db.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving trade: {e}")
            return False
    
    async def update_trade(self, order_id: str, update_data: Dict[str, Any]) -> bool:
        """Update existing trade information"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE trades SET
                        close_price = ?,
                        pnl = ?,
                        status = ?,
                        close_time = ?,
                        close_reason = ?
                    WHERE order_id = ?
                """, (
                    update_data.get('close_price'),
                    update_data.get('pnl'),
                    update_data.get('status', 'closed'),
                    datetime.fromtimestamp(update_data.get('close_time', 0)).isoformat(),
                    update_data.get('close_reason'),
                    order_id
                ))
                
                await db.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating trade {order_id}: {e}")
            return False
    
    async def get_trades(self, symbol: str = None, status: str = None, limit: int = 100) -> List[Dict]:
        """Get trades from database with optional filters"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = "SELECT * FROM trades WHERE 1=1"
                params = []
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                query += " ORDER BY created_at DESC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    trades = []
                    for row in rows:
                        trade = dict(zip(columns, row))
                        # Parse JSON data
                        if trade['prediction_data']:
                            trade['prediction_data'] = json.loads(trade['prediction_data'])
                        trades.append(trade)
                    
                    return trades
                    
        except Exception as e:
            self.logger.error(f"Error getting trades: {e}")
            return []
    
    async def store_ohlcv_batch(self, ohlcv_records: List[Dict]) -> bool:
        """Store OHLCV data in batch"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.executemany("""
                    INSERT OR REPLACE INTO ohlcv_data (
                        symbol, timeframe, timestamp, open, high, low, close, volume
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    (
                        record['symbol'],
                        record['timeframe'],
                        record['timestamp'],
                        record['open'],
                        record['high'],
                        record['low'],
                        record['close'],
                        record['volume']
                    ) for record in ohlcv_records
                ])
                
                await db.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing OHLCV batch: {e}")
            return False
    
    async def get_ohlcv_data(self, symbol: str, timeframe: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Get OHLCV data as pandas DataFrame"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    SELECT timestamp, open, high, low, close, volume
                    FROM ohlcv_data
                    WHERE symbol = ? AND timeframe = ?
                """
                params = [symbol, timeframe]
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date)
                
                query += " ORDER BY timestamp"
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    if rows:
                        df = pd.DataFrame(rows, columns=columns)
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df.set_index('timestamp', inplace=True)
                        return df
                    else:
                        return pd.DataFrame()
                        
        except Exception as e:
            self.logger.error(f"Error getting OHLCV data: {e}")
            return pd.DataFrame()
    
    async def save_performance_metrics(self, date: str, metrics: Dict[str, Any]) -> bool:
        """Save daily performance metrics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO performance_metrics (
                        date, total_trades, winning_trades, losing_trades,
                        total_pnl, total_volume, max_drawdown, metrics_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    date,
                    metrics.get('total_trades', 0),
                    metrics.get('winning_trades', 0),
                    metrics.get('losing_trades', 0),
                    metrics.get('total_pnl', 0),
                    metrics.get('total_volume', 0),
                    metrics.get('max_drawdown', 0),
                    json.dumps(metrics)
                ))
                
                await db.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving performance metrics: {e}")
            return False
    
    async def get_performance_metrics(self, days: int = 30) -> List[Dict]:
        """Get performance metrics for specified number of days"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT * FROM performance_metrics
                    ORDER BY date DESC
                    LIMIT ?
                """, (days,)) as cursor:
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    metrics = []
                    for row in rows:
                        metric = dict(zip(columns, row))
                        if metric['metrics_data']:
                            metric['metrics_data'] = json.loads(metric['metrics_data'])
                        metrics.append(metric)
                    
                    return metrics
                    
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return []
    
    async def cleanup_old_ohlcv_data(self, cutoff_date: str) -> bool:
        """Clean up old OHLCV data"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM ohlcv_data
                    WHERE timestamp < ?
                """, (cutoff_date,))
                
                await db.commit()
                
                # Get count of deleted rows
                async with db.execute("SELECT changes()") as cursor:
                    deleted_count = (await cursor.fetchone())[0]
                
                self.logger.info(f"Cleaned up {deleted_count} old OHLCV records")
                return True
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old OHLCV data: {e}")
            return False
    
    async def get_trading_statistics(self) -> Dict[str, Any]:
        """Get comprehensive trading statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                # Total trades
                async with db.execute("SELECT COUNT(*) FROM trades") as cursor:
                    stats['total_trades'] = (await cursor.fetchone())[0]
                
                # Open trades
                async with db.execute("SELECT COUNT(*) FROM trades WHERE status = 'open'") as cursor:
                    stats['open_trades'] = (await cursor.fetchone())[0]
                
                # Closed trades statistics
                async with db.execute("""
                    SELECT COUNT(*), SUM(pnl), AVG(pnl), MIN(pnl), MAX(pnl)
                    FROM trades WHERE status = 'closed'
                """) as cursor:
                    row = await cursor.fetchone()
                    stats['closed_trades'] = row[0] or 0
                    stats['total_pnl'] = row[1] or 0
                    stats['avg_pnl'] = row[2] or 0
                    stats['min_pnl'] = row[3] or 0
                    stats['max_pnl'] = row[4] or 0
                
                # Winning/losing trades
                async with db.execute("SELECT COUNT(*) FROM trades WHERE status = 'closed' AND pnl > 0") as cursor:
                    stats['winning_trades'] = (await cursor.fetchone())[0]
                
                async with db.execute("SELECT COUNT(*) FROM trades WHERE status = 'closed' AND pnl < 0") as cursor:
                    stats['losing_trades'] = (await cursor.fetchone())[0]
                
                # Win rate
                if stats['closed_trades'] > 0:
                    stats['win_rate'] = stats['winning_trades'] / stats['closed_trades']
                else:
                    stats['win_rate'] = 0
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error getting trading statistics: {e}")
            return {}
