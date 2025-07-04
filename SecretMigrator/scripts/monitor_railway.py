"""
Monitoring script for Railway deployment
"""
import requests
import time
import os
from datetime import datetime
import telegram
import json

class RailwayMonitor:
    def __init__(self):
        self.app_url = os.getenv('RAILWAY_APP_URL')
        self.telegram_bot = telegram.Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.check_interval = 300  # 5 minutes
        self.last_notification = {}
    
    async def check_health(self):
        """Check application health"""
        try:
            response = requests.get(f"{self.app_url}/health")
            health_data = response.json()
            
            if response.status_code != 200:
                await self.send_alert(f"❌ Health check failed: {health_data.get('error', 'Unknown error')}")
                return False
            
            # Check uptime
            uptime_hours = health_data['uptime_seconds'] / 3600
            if uptime_hours > 23:  # Daily status report
                await self.send_status_report(health_data)
            
            # Check exchange connection
            if health_data['exchange'] != 'connected':
                await self.send_alert("⚠️ Exchange connection error")
            
            return True
            
        except Exception as e:
            await self.send_alert(f"❌ Monitoring error: {str(e)}")
            return False
    
    async def send_alert(self, message: str):
        """Send alert to Telegram"""
        # Avoid spam by checking last notification time
        if time.time() - self.last_notification.get(message, 0) < 3600:  # 1 hour cooldown
            return
        
        try:
            await self.telegram_bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            self.last_notification[message] = time.time()
        except Exception as e:
            print(f"Failed to send Telegram alert: {e}")
    
    async def send_status_report(self, health_data: dict):
        """Send daily status report"""
        try:
            # Get trading statistics
            stats_response = requests.get(f"{self.app_url}/api/statistics")
            stats = stats_response.json()
            
            report = f"""📊 Daily Status Report
            
Uptime: {health_data['uptime_seconds'] // 3600} hours
Status: {'✅ Healthy' if health_data['status'] == 'healthy' else '❌ Unhealthy'}
Database: {'✅ Connected' if health_data['database'] == 'connected' else '❌ Error'}
Exchange: {'✅ Connected' if health_data['exchange'] == 'connected' else '❌ Error'}

Trading Statistics:
- Total Equity: ${stats.get('total_equity', 0):.2f}
- Daily P&L: ${stats.get('daily_pnl', 0):.2f}
- Active Positions: {stats.get('active_positions', 0)}
- Total Trades: {stats.get('total_trades', 0)}

Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
            await self.telegram_bot.send_message(
                chat_id=self.chat_id,
                text=report,
                parse_mode='HTML'
            )
            
        except Exception as e:
            await self.send_alert(f"❌ Failed to generate status report: {str(e)}")
    
    async def run(self):
        """Run the monitoring loop"""
        print("Starting Railway deployment monitor...")
        
        while True:
            await self.check_health()
            time.sleep(self.check_interval)

if __name__ == '__main__':
    import asyncio
    monitor = RailwayMonitor()
    asyncio.run(monitor.run()) 