"""
Main entry point for the crypto trading bot
"""
import asyncio
import logging
import signal
import sys
from bot.trading_bot import TradingBot
from dashboard.app import start_dashboard
from utils.logger import setup_logger
from config import Config
import threading

class TradingBotApplication:
    def __init__(self):
        self.logger = setup_logger('main')
        self.config = Config()
        self.bot = None
        self.dashboard_thread = None
        self.running = True
        
    async def start(self):
        """Start the trading bot and dashboard"""
        try:
            self.logger.info("Starting Crypto Trading Bot...")
            
            # Initialize the trading bot
            self.bot = TradingBot(self.config)
            
            # Start dashboard in separate thread
            self.dashboard_thread = threading.Thread(
                target=start_dashboard, 
                args=(self.config,),
                daemon=True
            )
            self.dashboard_thread.start()
            
            # Start the trading bot
            await self.bot.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start application: {e}")
            raise
    
    async def stop(self):
        """Stop the trading bot gracefully"""
        self.logger.info("Stopping Crypto Trading Bot...")
        self.running = False
        
        if self.bot:
            await self.bot.stop()
        
        self.logger.info("Bot stopped successfully")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.stop())

async def main():
    """Main function"""
    app = TradingBotApplication()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)
    
    try:
        await app.start()
        
        # Keep the application running
        while app.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        await app.stop()
    except Exception as e:
        logging.error(f"Application error: {e}")
        await app.stop()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
