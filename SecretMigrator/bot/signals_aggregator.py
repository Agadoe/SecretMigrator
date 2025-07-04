"""
External signals aggregator for trend analysis and signal collection
"""
import asyncio
import aiohttp
import logging
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from utils.logger import setup_logger
import json

class SignalsAggregator:
    """Aggregates external trading signals and market sentiment"""
    
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger('signals_aggregator')
        
        # Signal sources and their weights
        self.signal_sources = {
            'fear_greed_index': 0.25,
            'social_sentiment': 0.20,
            'whale_movements': 0.15,
            'options_flow': 0.15,
            'technical_patterns': 0.25
        }
        
        # Cache for signals
        self.signals_cache = {}
        self.last_update = None
        self.update_interval = 300  # 5 minutes
        
    async def get_aggregated_signals(self, symbol: str = None) -> Dict[str, Any]:
        """Get aggregated signals from all sources"""
        try:
            # Check if we need to update signals
            now = datetime.now()
            if (not self.last_update or 
                (now - self.last_update).total_seconds() > self.update_interval):
                await self._update_all_signals()
                self.last_update = now
            
            # Return signals for specific symbol or general market
            if symbol:
                return self.signals_cache.get(symbol, {})
            else:
                return self._get_market_signals()
                
        except Exception as e:
            self.logger.error(f"Error getting aggregated signals: {e}")
            return {}
    
    async def _update_all_signals(self):
        """Update signals from all sources"""
        try:
            # Simulate fetching from multiple signal sources
            tasks = [
                self._get_fear_greed_signals(),
                self._get_social_sentiment(),
                self._get_whale_movements(),
                self._get_options_flow(),
                self._get_technical_patterns()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if not isinstance(result, Exception):
                    source_name = list(self.signal_sources.keys())[i]
                    self.logger.info(f"Updated signals from {source_name}")
                    
        except Exception as e:
            self.logger.error(f"Error updating signals: {e}")
    
    async def _get_fear_greed_signals(self) -> Dict[str, Any]:
        """Simulate fear and greed index signals"""
        try:
            # Simulate fear/greed index (0-100)
            fear_greed_value = random.randint(10, 90)
            
            if fear_greed_value < 25:
                sentiment = "Extreme Fear"
                signal_strength = "STRONG_BUY"
            elif fear_greed_value < 45:
                sentiment = "Fear"
                signal_strength = "BUY"
            elif fear_greed_value < 55:
                sentiment = "Neutral"
                signal_strength = "HOLD"
            elif fear_greed_value < 75:
                sentiment = "Greed"
                signal_strength = "SELL"
            else:
                sentiment = "Extreme Greed"
                signal_strength = "STRONG_SELL"
            
            signal = {
                'source': 'Fear & Greed Index',
                'value': fear_greed_value,
                'sentiment': sentiment,
                'signal': signal_strength,
                'confidence': 0.85,
                'timestamp': datetime.now().isoformat()
            }
            
            self.signals_cache['fear_greed'] = signal
            return signal
            
        except Exception as e:
            self.logger.error(f"Error getting fear/greed signals: {e}")
            return {}
    
    async def _get_social_sentiment(self) -> Dict[str, Any]:
        """Simulate social media sentiment signals"""
        try:
            symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
            
            for symbol in symbols:
                # Simulate social sentiment analysis
                positive_mentions = random.randint(100, 1000)
                negative_mentions = random.randint(50, 500)
                total_mentions = positive_mentions + negative_mentions
                
                sentiment_score = (positive_mentions - negative_mentions) / total_mentions
                
                if sentiment_score > 0.3:
                    sentiment = "Very Positive"
                    signal_strength = "BUY"
                elif sentiment_score > 0.1:
                    sentiment = "Positive"
                    signal_strength = "WEAK_BUY"
                elif sentiment_score > -0.1:
                    sentiment = "Neutral"
                    signal_strength = "HOLD"
                elif sentiment_score > -0.3:
                    sentiment = "Negative"
                    signal_strength = "WEAK_SELL"
                else:
                    sentiment = "Very Negative"
                    signal_strength = "SELL"
                
                signal = {
                    'source': 'Social Sentiment',
                    'symbol': symbol,
                    'sentiment_score': round(sentiment_score, 3),
                    'sentiment': sentiment,
                    'signal': signal_strength,
                    'mentions': total_mentions,
                    'confidence': min(0.9, total_mentions / 1000),
                    'timestamp': datetime.now().isoformat()
                }
                
                self.signals_cache[f'social_{symbol}'] = signal
            
            return {'updated': True}
            
        except Exception as e:
            self.logger.error(f"Error getting social sentiment: {e}")
            return {}
    
    async def _get_whale_movements(self) -> Dict[str, Any]:
        """Simulate whale wallet movement signals"""
        try:
            symbols = ['BTC/USDT', 'ETH/USDT']
            
            for symbol in symbols:
                # Simulate whale movements
                large_transactions = random.randint(0, 5)
                
                if large_transactions > 3:
                    activity_level = "High"
                    signal_strength = "STRONG_SELL" if random.choice([True, False]) else "STRONG_BUY"
                elif large_transactions > 1:
                    activity_level = "Medium" 
                    signal_strength = "WEAK_SELL" if random.choice([True, False]) else "WEAK_BUY"
                else:
                    activity_level = "Low"
                    signal_strength = "HOLD"
                
                signal = {
                    'source': 'Whale Movements',
                    'symbol': symbol,
                    'large_transactions': large_transactions,
                    'activity_level': activity_level,
                    'signal': signal_strength,
                    'confidence': 0.75,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.signals_cache[f'whale_{symbol}'] = signal
            
            return {'updated': True}
            
        except Exception as e:
            self.logger.error(f"Error getting whale movements: {e}")
            return {}
    
    async def _get_options_flow(self) -> Dict[str, Any]:
        """Simulate options flow signals"""
        try:
            # Simulate options data
            call_volume = random.randint(1000, 10000)
            put_volume = random.randint(1000, 10000)
            
            put_call_ratio = put_volume / call_volume
            
            if put_call_ratio > 1.2:
                sentiment = "Bearish"
                signal_strength = "SELL"
            elif put_call_ratio > 0.8:
                sentiment = "Neutral"
                signal_strength = "HOLD"
            else:
                sentiment = "Bullish"
                signal_strength = "BUY"
            
            signal = {
                'source': 'Options Flow',
                'put_call_ratio': round(put_call_ratio, 3),
                'call_volume': call_volume,
                'put_volume': put_volume,
                'sentiment': sentiment,
                'signal': signal_strength,
                'confidence': 0.70,
                'timestamp': datetime.now().isoformat()
            }
            
            self.signals_cache['options_flow'] = signal
            return signal
            
        except Exception as e:
            self.logger.error(f"Error getting options flow: {e}")
            return {}
    
    async def _get_technical_patterns(self) -> Dict[str, Any]:
        """Simulate technical pattern recognition signals"""
        try:
            symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
            patterns = [
                'Head and Shoulders', 'Bull Flag', 'Bear Flag', 
                'Ascending Triangle', 'Descending Triangle',
                'Cup and Handle', 'Double Top', 'Double Bottom'
            ]
            
            for symbol in symbols:
                # Simulate pattern detection
                detected_pattern = random.choice(patterns)
                pattern_strength = random.uniform(0.6, 0.95)
                
                # Determine signal based on pattern
                bullish_patterns = ['Bull Flag', 'Ascending Triangle', 'Cup and Handle', 'Double Bottom']
                bearish_patterns = ['Bear Flag', 'Descending Triangle', 'Head and Shoulders', 'Double Top']
                
                if detected_pattern in bullish_patterns:
                    signal_strength = "BUY" if pattern_strength > 0.8 else "WEAK_BUY"
                elif detected_pattern in bearish_patterns:
                    signal_strength = "SELL" if pattern_strength > 0.8 else "WEAK_SELL"
                else:
                    signal_strength = "HOLD"
                
                signal = {
                    'source': 'Technical Patterns',
                    'symbol': symbol,
                    'pattern': detected_pattern,
                    'pattern_strength': round(pattern_strength, 3),
                    'signal': signal_strength,
                    'confidence': pattern_strength,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.signals_cache[f'pattern_{symbol}'] = signal
            
            return {'updated': True}
            
        except Exception as e:
            self.logger.error(f"Error getting technical patterns: {e}")
            return {}
    
    def _get_market_signals(self) -> Dict[str, Any]:
        """Aggregate all signals into market overview"""
        try:
            market_signals = {
                'overall_sentiment': 'NEUTRAL',
                'signal_strength': 0.0,
                'confidence': 0.0,
                'signal_count': 0,
                'signals_by_source': {},
                'trending_signals': []
            }
            
            total_weight = 0
            weighted_signal = 0
            signal_count = 0
            
            # Process all cached signals
            for key, signal in self.signals_cache.items():
                if 'signal' in signal and 'confidence' in signal:
                    signal_count += 1
                    
                    # Convert signal to numeric value
                    signal_value = self._signal_to_numeric(signal['signal'])
                    confidence = signal['confidence']
                    
                    # Weight by source type
                    weight = self._get_signal_weight(signal['source'])
                    
                    weighted_signal += signal_value * confidence * weight
                    total_weight += confidence * weight
                    
                    # Add to signals by source
                    source = signal['source']
                    if source not in market_signals['signals_by_source']:
                        market_signals['signals_by_source'][source] = []
                    market_signals['signals_by_source'][source].append(signal)
            
            # Calculate overall sentiment
            if total_weight > 0:
                market_signals['signal_strength'] = weighted_signal / total_weight
                market_signals['confidence'] = min(1.0, total_weight / len(self.signal_sources))
                market_signals['overall_sentiment'] = self._numeric_to_signal(market_signals['signal_strength'])
            
            market_signals['signal_count'] = signal_count
            market_signals['last_updated'] = datetime.now().isoformat()
            
            # Add trending signals (strongest signals)
            trending = []
            for key, signal in self.signals_cache.items():
                if 'confidence' in signal and signal['confidence'] > 0.8:
                    trending.append(signal)
            
            market_signals['trending_signals'] = sorted(
                trending, 
                key=lambda x: x['confidence'], 
                reverse=True
            )[:5]
            
            return market_signals
            
        except Exception as e:
            self.logger.error(f"Error aggregating market signals: {e}")
            return {}
    
    def _signal_to_numeric(self, signal: str) -> float:
        """Convert signal string to numeric value"""
        signal_map = {
            'STRONG_BUY': 1.0,
            'BUY': 0.6,
            'WEAK_BUY': 0.3,
            'HOLD': 0.0,
            'WEAK_SELL': -0.3,
            'SELL': -0.6,
            'STRONG_SELL': -1.0
        }
        return signal_map.get(signal, 0.0)
    
    def _numeric_to_signal(self, value: float) -> str:
        """Convert numeric value to signal string"""
        if value > 0.7:
            return 'STRONG_BUY'
        elif value > 0.3:
            return 'BUY'
        elif value > 0.1:
            return 'WEAK_BUY'
        elif value > -0.1:
            return 'HOLD'
        elif value > -0.3:
            return 'WEAK_SELL'
        elif value > -0.7:
            return 'SELL'
        else:
            return 'STRONG_SELL'
    
    def _get_signal_weight(self, source: str) -> float:
        """Get weight for signal source"""
        for key, weight in self.signal_sources.items():
            if key.replace('_', ' ').lower() in source.lower():
                return weight
        return 0.1  # Default weight for unknown sources
    
    async def get_trending_topics(self) -> List[Dict[str, Any]]:
        """Get trending topics and signals"""
        try:
            await self.get_aggregated_signals()  # Ensure signals are updated
            
            trending = []
            
            # Add fear/greed if significant
            if 'fear_greed' in self.signals_cache:
                fg_signal = self.signals_cache['fear_greed']
                if fg_signal['value'] < 30 or fg_signal['value'] > 70:
                    trending.append({
                        'topic': f"Market {fg_signal['sentiment']}",
                        'description': f"Fear & Greed Index at {fg_signal['value']}",
                        'signal': fg_signal['signal'],
                        'strength': 'high' if abs(fg_signal['value'] - 50) > 25 else 'medium'
                    })
            
            # Add social sentiment trends
            for key, signal in self.signals_cache.items():
                if key.startswith('social_') and signal.get('mentions', 0) > 500:
                    symbol = signal['symbol']
                    trending.append({
                        'topic': f"{symbol} Social Buzz",
                        'description': f"{signal['mentions']} mentions - {signal['sentiment']}",
                        'signal': signal['signal'],
                        'strength': 'high' if signal['mentions'] > 800 else 'medium'
                    })
            
            # Add pattern signals
            for key, signal in self.signals_cache.items():
                if key.startswith('pattern_') and signal.get('confidence', 0) > 0.85:
                    trending.append({
                        'topic': f"{signal['symbol']} {signal['pattern']}",
                        'description': f"Strong pattern detected ({signal['confidence']:.0%} confidence)",
                        'signal': signal['signal'],
                        'strength': 'high'
                    })
            
            return trending[:10]  # Return top 10 trending
            
        except Exception as e:
            self.logger.error(f"Error getting trending topics: {e}")
            return []