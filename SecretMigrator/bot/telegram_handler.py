"""
Telegram bot handler for notifications and commands
"""
import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from typing import Dict, Any
from utils.logger import setup_logger
import json

class TelegramHandler:
    """Handles Telegram bot interactions"""
    
    def __init__(self, config, trading_bot):
        self.config = config
        self.trading_bot = trading_bot
        self.logger = setup_logger('telegram_handler')
        
        # Initialize Telegram bot
        self.application = None
        self.bot = None
        
        if self.config.TELEGRAM_BOT_TOKEN:
            self.bot = Bot(token=self.config.TELEGRAM_BOT_TOKEN)
            self.application = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup command and message handlers"""
        if not self.application:
            return
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        self.application.add_handler(CommandHandler("positions", self.positions_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Message handler for general messages
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
    
    async def start(self):
        """Start the Telegram bot"""
        if not self.application:
            self.logger.warning("Telegram bot not configured - missing token")
            return
        
        try:
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            
            # Start polling in background
            asyncio.create_task(self.application.updater.start_polling())
            
            self.logger.info("Telegram bot started successfully")
            
            # Send startup notification
            await self.send_notification("🤖 Trading bot started successfully!")
            
        except Exception as e:
            self.logger.error(f"Failed to start Telegram bot: {e}")
    
    async def stop(self):
        """Stop the Telegram bot"""
        if self.application:
            try:
                await self.send_notification("🛑 Trading bot shutting down...")
                await self.application.stop()
                self.logger.info("Telegram bot stopped")
            except Exception as e:
                self.logger.error(f"Error stopping Telegram bot: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            welcome_message = """
🤖 **Crypto Trading Bot**

Welcome! This bot helps you monitor and control your automated crypto trading.

Available commands:
/status - Get bot status
/balance - Check account balance
/positions - View active positions
/stop - Stop the trading bot
/help - Show this help message

The bot will send you notifications about trades and important events.
            """
            
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error in start command: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            if not self._is_authorized(update.effective_chat.id):
                await update.message.reply_text("❌ Unauthorized access")
                return
            
            status = await self.trading_bot.get_status()
            
            if 'error' in status:
                await update.message.reply_text(f"❌ Error getting status: {status['error']}")
                return
            
            status_message = f"""
📊 **Bot Status**

🟢 Status: {'Running' if status['running'] else 'Stopped'}
📈 Active Positions: {status['active_positions']}
💰 Balance: ${status.get('balance', {}).get('USDT', 0):.2f}
📋 Trading Pairs: {', '.join(status['trading_pairs'])}
🕐 Last Update: {status.get('last_update', 'N/A')}
            """
            
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error in status command: {e}")
            await update.message.reply_text("❌ Error retrieving status")
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        try:
            if not self._is_authorized(update.effective_chat.id):
                await update.message.reply_text("❌ Unauthorized access")
                return
            
            balance = await self.trading_bot.exchange_manager.get_balance()
            
            if not balance:
                await update.message.reply_text("❌ Error retrieving balance")
                return
            
            balance_message = "💰 **Account Balance**\n\n"
            
            for currency, amount in balance.items():
                if amount > 0:
                    balance_message += f"{currency}: {amount:.8f}\n"
            
            await update.message.reply_text(balance_message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error in balance command: {e}")
            await update.message.reply_text("❌ Error retrieving balance")
    
    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        try:
            if not self._is_authorized(update.effective_chat.id):
                await update.message.reply_text("❌ Unauthorized access")
                return
            
            active_positions = self.trading_bot.active_positions
            
            if not active_positions:
                await update.message.reply_text("📭 No active positions")
                return
            
            positions_message = "📊 **Active Positions**\n\n"
            
            for order_id, position in active_positions.items():
                pnl_emoji = "📈" if position.get('pnl', 0) >= 0 else "📉"
                side_emoji = "🟢" if position['side'] == 'long' else "🔴"
                
                positions_message += f"""
{side_emoji} **{position['symbol']}** ({position['side'].upper()})
💵 Amount: {position['amount']:.8f}
📍 Entry: ${position['entry_price']:.4f}
🛑 Stop Loss: ${position['stop_loss']:.4f}
🎯 Take Profit: ${position['take_profit']:.4f}
{pnl_emoji} P&L: ${position.get('pnl', 0):.2f}

"""
            
            await update.message.reply_text(positions_message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error in positions command: {e}")
            await update.message.reply_text("❌ Error retrieving positions")
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        try:
            if not self._is_authorized(update.effective_chat.id):
                await update.message.reply_text("❌ Unauthorized access")
                return
            
            await update.message.reply_text("🛑 Stopping trading bot...")
            
            # Stop the trading bot
            asyncio.create_task(self.trading_bot.stop())
            
        except Exception as e:
            self.logger.error(f"Error in stop command: {e}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            help_message = """
🤖 **Crypto Trading Bot Commands**

/start - Start interaction with the bot
/status - Get current bot status and statistics
/balance - View account balance across all currencies
/positions - Show all active trading positions
/stop - Emergency stop the trading bot
/help - Display this help message

**Features:**
• 🔄 Automated trading based on AI predictions
• 📊 Real-time market analysis
• 🛡️ Risk management with stop-loss
• 📱 Telegram notifications for all trades
• 📈 Performance tracking and reporting

**Safety:**
• Always uses stop-loss orders
• Risk management prevents excessive losses
• Position sizing based on account balance
• Daily loss limits for protection

For support or questions, check the logs or contact the administrator.
            """
            
            await update.message.reply_text(help_message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error in help command: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general messages"""
        try:
            if not self._is_authorized(update.effective_chat.id):
                return
            
            message_text = update.message.text.lower()
            
            # Simple keyword responses
            if 'status' in message_text or 'how' in message_text:
                await self.status_command(update, context)
            elif 'balance' in message_text or 'money' in message_text:
                await self.balance_command(update, context)
            elif 'position' in message_text or 'trade' in message_text:
                await self.positions_command(update, context)
            else:
                await update.message.reply_text(
                    "🤔 I didn't understand that. Type /help to see available commands."
                )
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    def _is_authorized(self, chat_id: int) -> bool:
        """Check if the chat ID is authorized"""
        if not self.config.TELEGRAM_CHAT_IDS:
            return True  # If no restriction is set, allow all
        
        authorized_ids = [int(id.strip()) for id in self.config.TELEGRAM_CHAT_IDS if id.strip()]
        return chat_id in authorized_ids
    
    async def send_notification(self, message: str):
        """Send notification to authorized chats"""
        if not self.bot or not self.config.TELEGRAM_NOTIFICATIONS:
            return
        
        try:
            if self.config.TELEGRAM_CHAT_IDS:
                for chat_id in self.config.TELEGRAM_CHAT_IDS:
                    if chat_id.strip():
                        await self.bot.send_message(
                            chat_id=int(chat_id.strip()),
                            text=message,
                            parse_mode='Markdown'
                        )
            
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
    
    async def send_trade_notification(self, position: Dict[str, Any], action: str):
        """Send trade-specific notifications"""
        try:
            if action == "OPENED":
                emoji = "🟢" if position['side'] == 'long' else "🔴"
                message = f"""
{emoji} **POSITION OPENED**

📊 Symbol: {position['symbol']}
📈 Side: {position['side'].upper()}
💵 Amount: {position['amount']:.8f}
📍 Entry Price: ${position['entry_price']:.4f}
🛑 Stop Loss: ${position['stop_loss']:.4f}
🎯 Take Profit: ${position['take_profit']:.4f}
🤖 AI Confidence: {position.get('prediction', {}).get('confidence', 0):.2%}
                """
            
            elif action == "CLOSED":
                pnl = position.get('pnl', 0)
                pnl_emoji = "💰" if pnl >= 0 else "💸"
                
                message = f"""
{pnl_emoji} **POSITION CLOSED**

📊 Symbol: {position['symbol']}
📈 Side: {position['side'].upper()}
💵 Amount: {position['amount']:.8f}
📍 Entry: ${position['entry_price']:.4f}
📍 Exit: ${position.get('close_price', 0):.4f}
📊 P&L: ${pnl:.2f}
📋 Reason: {position.get('close_reason', 'Unknown')}
                """
            
            else:
                message = f"Trade update: {action} for {position['symbol']}"
            
            await self.send_notification(message)
            
        except Exception as e:
            self.logger.error(f"Error sending trade notification: {e}")
    
    async def send_alert(self, alert_type: str, message: str):
        """Send alert notifications"""
        try:
            alert_emojis = {
                'error': '🚨',
                'warning': '⚠️',
                'info': 'ℹ️',
                'success': '✅'
            }
            
            emoji = alert_emojis.get(alert_type, '📢')
            alert_message = f"{emoji} **ALERT**\n\n{message}"
            
            await self.send_notification(alert_message)
            
        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
