"""
Database initialization script
"""
import asyncio
import sqlite3
import logging
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import DatabaseManager
from utils.logger import setup_logger
from config import Config

class DatabaseInitializer:
    """Database initialization and management utility"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger('db_initializer')
        self.db_manager = DatabaseManager(config.DATABASE_URL)
    
    async def initialize_database(self):
        """Initialize the database with all required tables"""
        try:
            self.logger.info("Starting database initialization...")
            
            # Create database tables
            await self.db_manager.initialize()
            
            # Verify tables were created
            await self._verify_tables()
            
            # Create initial data if needed
            await self._create_initial_data()
            
            self.logger.info("Database initialization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    async def _verify_tables(self):
        """Verify that all required tables exist"""
        required_tables = [
            'trades',
            'ohlcv_data',
            'performance_metrics',
            'bot_status'
        ]
        
        try:
            # Extract database path
            if self.config.DATABASE_URL.startswith('sqlite:///'):
                db_path = self.config.DATABASE_URL.replace('sqlite:///', '')
            else:
                db_path = 'trading_bot.db'
            
            # Connect and check tables
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [table[0] for table in cursor.fetchall()]
            
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                self.logger.error(f"Missing tables: {missing_tables}")
                raise Exception(f"Database tables missing: {missing_tables}")
            
            self.logger.info(f"All required tables exist: {existing_tables}")
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error verifying tables: {e}")
            raise
    
    async def _create_initial_data(self):
        """Create initial data if database is empty"""
        try:
            # Check if we need to create initial performance metrics
            metrics = await self.db_manager.get_performance_metrics(days=1)
            
            if not metrics:
                # Create initial performance metrics entry
                today = datetime.now().strftime('%Y-%m-%d')
                initial_metrics = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_pnl': 0.0,
                    'total_volume': 0.0,
                    'max_drawdown': 0.0
                }
                
                await self.db_manager.save_performance_metrics(today, initial_metrics)
                self.logger.info("Created initial performance metrics")
            
            # Create initial bot status entry
            await self._create_initial_status()
            
        except Exception as e:
            self.logger.error(f"Error creating initial data: {e}")
    
    async def _create_initial_status(self):
        """Create initial bot status entry"""
        try:
            import aiosqlite
            
            db_path = self.config.DATABASE_URL.replace('sqlite:///', '') if self.config.DATABASE_URL.startswith('sqlite:///') else 'trading_bot.db'
            
            async with aiosqlite.connect(db_path) as db:
                # Check if status entries exist
                async with db.execute("SELECT COUNT(*) FROM bot_status") as cursor:
                    count = (await cursor.fetchone())[0]
                
                if count == 0:
                    # Create initial status entry
                    await db.execute("""
                        INSERT INTO bot_status (
                            timestamp, status, active_positions, balance_data, error_count, status_data
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        datetime.now().isoformat(),
                        'initialized',
                        0,
                        '{}',
                        0,
                        '{"initialized": true}'
                    ))
                    
                    await db.commit()
                    self.logger.info("Created initial bot status entry")
                
        except Exception as e:
            self.logger.error(f"Error creating initial status: {e}")
    
    async def reset_database(self):
        """Reset database by dropping and recreating all tables"""
        try:
            self.logger.warning("Resetting database - all data will be lost!")
            
            db_path = self.config.DATABASE_URL.replace('sqlite:///', '') if self.config.DATABASE_URL.startswith('sqlite:///') else 'trading_bot.db'
            
            # Remove existing database file
            if os.path.exists(db_path):
                os.remove(db_path)
                self.logger.info(f"Removed existing database: {db_path}")
            
            # Reinitialize database
            await self.initialize_database()
            
            self.logger.info("Database reset completed")
            
        except Exception as e:
            self.logger.error(f"Error resetting database: {e}")
            raise
    
    async def create_sample_data(self):
        """Create sample data for testing purposes"""
        try:
            self.logger.info("Creating sample data...")
            
            # Create sample trades
            sample_trades = [
                {
                    'order_id': 'sample_001',
                    'symbol': 'BTC/USDT',
                    'side': 'long',
                    'amount': 0.01,
                    'entry_price': 45000.0,
                    'stop_loss': 44100.0,
                    'take_profit': 47250.0,
                    'timestamp': (datetime.now() - timedelta(hours=2)).timestamp(),
                    'prediction': {'confidence': 0.75, 'signal': 'BUY'}
                },
                {
                    'order_id': 'sample_002',
                    'symbol': 'ETH/USDT',
                    'side': 'long',
                    'amount': 0.5,
                    'entry_price': 3000.0,
                    'stop_loss': 2940.0,
                    'take_profit': 3150.0,
                    'timestamp': (datetime.now() - timedelta(hours=1)).timestamp(),
                    'prediction': {'confidence': 0.68, 'signal': 'BUY'}
                }
            ]
            
            for trade_data in sample_trades:
                await self.db_manager.save_trade(trade_data)
            
            # Create sample OHLCV data
            await self._create_sample_ohlcv_data()
            
            # Create sample performance metrics
            await self._create_sample_performance_data()
            
            self.logger.info("Sample data created successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating sample data: {e}")
            raise
    
    async def _create_sample_ohlcv_data(self):
        """Create sample OHLCV data"""
        try:
            import random
            
            symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
            timeframes = ['1h', '4h']
            
            for symbol in symbols:
                for timeframe in timeframes:
                    # Generate 48 hours of sample data
                    base_price = 45000 if 'BTC' in symbol else (3000 if 'ETH' in symbol else 1.5)
                    
                    ohlcv_records = []
                    current_time = datetime.now() - timedelta(hours=48)
                    
                    for i in range(48):
                        # Generate realistic OHLCV data
                        variation = random.uniform(-0.02, 0.02)  # 2% max variation
                        open_price = base_price * (1 + variation)
                        close_price = open_price * (1 + random.uniform(-0.01, 0.01))
                        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.005))
                        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.005))
                        volume = random.uniform(100, 1000)
                        
                        ohlcv_records.append({
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'timestamp': current_time.isoformat(),
                            'open': open_price,
                            'high': high_price,
                            'low': low_price,
                            'close': close_price,
                            'volume': volume
                        })
                        
                        current_time += timedelta(hours=1)
                    
                    # Store in batches
                    await self.db_manager.store_ohlcv_batch(ohlcv_records)
            
            self.logger.info("Sample OHLCV data created")
            
        except Exception as e:
            self.logger.error(f"Error creating sample OHLCV data: {e}")
    
    async def _create_sample_performance_data(self):
        """Create sample performance metrics"""
        try:
            # Create performance data for the last 7 days
            for i in range(7):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                
                metrics = {
                    'total_trades': random.randint(5, 15),
                    'winning_trades': random.randint(3, 10),
                    'losing_trades': random.randint(2, 8),
                    'total_pnl': random.uniform(-50, 150),
                    'total_volume': random.uniform(1000, 5000),
                    'max_drawdown': random.uniform(0, 10)
                }
                
                # Ensure consistency
                metrics['losing_trades'] = metrics['total_trades'] - metrics['winning_trades']
                if metrics['losing_trades'] < 0:
                    metrics['losing_trades'] = 0
                    metrics['winning_trades'] = metrics['total_trades']
                
                await self.db_manager.save_performance_metrics(date, metrics)
            
            self.logger.info("Sample performance data created")
            
        except Exception as e:
            self.logger.error(f"Error creating sample performance data: {e}")
    
    async def backup_database(self, backup_path: str = None):
        """Create a backup of the database"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"trading_bot_backup_{timestamp}.db"
            
            db_path = self.config.DATABASE_URL.replace('sqlite:///', '') if self.config.DATABASE_URL.startswith('sqlite:///') else 'trading_bot.db'
            
            if os.path.exists(db_path):
                import shutil
                shutil.copy2(db_path, backup_path)
                self.logger.info(f"Database backed up to: {backup_path}")
            else:
                self.logger.warning(f"Database file not found: {db_path}")
                
        except Exception as e:
            self.logger.error(f"Error backing up database: {e}")
            raise

async def main():
    """Main function for database initialization"""
    config = Config()
    initializer = DatabaseInitializer(config)
    
    import argparse
    parser = argparse.ArgumentParser(description='Database initialization utility')
    parser.add_argument('--reset', action='store_true', help='Reset database (WARNING: deletes all data)')
    parser.add_argument('--sample-data', action='store_true', help='Create sample data for testing')
    parser.add_argument('--backup', type=str, help='Create database backup to specified path')
    
    args = parser.parse_args()
    
    try:
        if args.reset:
            confirm = input("This will delete all existing data. Are you sure? (yes/no): ")
            if confirm.lower() == 'yes':
                await initializer.reset_database()
            else:
                print("Database reset cancelled")
                return
        
        # Initialize database
        await initializer.initialize_database()
        
        if args.sample_data:
            await initializer.create_sample_data()
        
        if args.backup:
            await initializer.backup_database(args.backup)
        
        print("Database initialization completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
