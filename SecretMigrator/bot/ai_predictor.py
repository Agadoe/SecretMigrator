"""
AI prediction module using machine learning for price forecasting
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import logging
from typing import Dict, List, Optional, Tuple
import joblib
import os
from utils.logger import setup_logger

class AIPredictor:
    """AI-based price prediction system"""
    
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger('ai_predictor')
        
        # Models for each trading pair
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        
        # Model parameters
        self.model_type = 'random_forest'  # or 'gradient_boosting'
        self.n_estimators = 100
        self.max_depth = 10
        self.random_state = 42
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML models for each trading pair"""
        for symbol in self.config.TRADING_PAIRS:
            if self.model_type == 'random_forest':
                self.models[symbol] = RandomForestClassifier(
                    n_estimators=self.n_estimators,
                    max_depth=self.max_depth,
                    random_state=self.random_state,
                    n_jobs=-1
                )
            else:
                self.models[symbol] = GradientBoostingClassifier(
                    n_estimators=self.n_estimators,
                    max_depth=self.max_depth,
                    random_state=self.random_state
                )
            
            self.scalers[symbol] = StandardScaler()
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for feature engineering"""
        try:
            # Price-based indicators
            df['sma_10'] = df['close'].rolling(window=10).mean()
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            df['bb_width'] = df['bb_upper'] - df['bb_lower']
            df['bb_position'] = (df['close'] - df['bb_lower']) / df['bb_width']
            
            # Volume indicators
            if 'volume' in df.columns:
                df['volume_sma'] = df['volume'].rolling(window=20).mean()
                df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Price change indicators
            df['price_change_1h'] = df['close'].pct_change(1)
            df['price_change_4h'] = df['close'].pct_change(4)
            df['price_change_24h'] = df['close'].pct_change(24)
            
            # Volatility
            df['volatility'] = df['close'].rolling(window=20).std()
            
            # Support and resistance levels
            df['high_20'] = df['high'].rolling(window=20).max()
            df['low_20'] = df['low'].rolling(window=20).min()
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculating technical indicators: {e}")
            return df
    
    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for machine learning"""
        try:
            # Calculate technical indicators
            df = self._calculate_technical_indicators(df)
            
            # Define feature columns
            self.feature_columns = [
                'sma_10', 'sma_20', 'sma_50',
                'ema_12', 'ema_26',
                'macd', 'macd_signal', 'macd_histogram',
                'rsi',
                'bb_width', 'bb_position',
                'price_change_1h', 'price_change_4h', 'price_change_24h',
                'volatility',
                'high_20', 'low_20'
            ]
            
            # Add volume features if available
            if 'volume' in df.columns:
                self.feature_columns.extend(['volume_ratio'])
            
            # Remove rows with NaN values
            df = df.dropna()
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error preparing features: {e}")
            return df
    
    def _create_labels(self, df: pd.DataFrame, prediction_horizon: int = 1) -> pd.Series:
        """Create labels for supervised learning"""
        try:
            # Calculate future price change
            future_price = df['close'].shift(-prediction_horizon)
            current_price = df['close']
            
            price_change = (future_price - current_price) / current_price
            
            # Create binary labels based on threshold
            threshold = 0.01  # 1% price change threshold
            
            labels = np.where(price_change > threshold, 1,  # Buy signal
                            np.where(price_change < -threshold, -1, 0))  # Sell signal, Hold
            
            return pd.Series(labels, index=df.index)
            
        except Exception as e:
            self.logger.error(f"Error creating labels: {e}")
            return pd.Series()
    
    async def train_model(self, symbol: str, historical_data: pd.DataFrame) -> bool:
        """Train the ML model for a specific symbol"""
        try:
            if len(historical_data) < 100:
                self.logger.warning(f"Insufficient data for training {symbol} model")
                return False
            
            # Prepare features
            df = self._prepare_features(historical_data.copy())
            
            if df.empty:
                self.logger.error(f"No valid features prepared for {symbol}")
                return False
            
            # Create labels
            labels = self._create_labels(df)
            
            # Prepare training data
            X = df[self.feature_columns].values
            y = labels.values
            
            # Remove samples with invalid labels
            valid_indices = ~np.isnan(y)
            X = X[valid_indices]
            y = y[valid_indices]
            
            if len(X) < 50:
                self.logger.warning(f"Insufficient valid samples for training {symbol} model")
                return False
            
            # Scale features
            X_scaled = self.scalers[symbol].fit_transform(X)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=self.random_state, stratify=y
            )
            
            # Train model
            self.models[symbol].fit(X_train, y_train)
            
            # Evaluate model
            y_pred = self.models[symbol].predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            self.logger.info(f"Model trained for {symbol} with accuracy: {accuracy:.3f}")
            
            # Save model
            await self._save_model(symbol)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error training model for {symbol}: {e}")
            return False
    
    async def predict(self, symbol: str, market_data: pd.DataFrame) -> Optional[Dict]:
        """Generate prediction for a symbol"""
        try:
            if symbol not in self.models:
                self.logger.warning(f"No model available for {symbol}")
                return None
            
            if len(market_data) < self.config.LOOKBACK_PERIODS:
                self.logger.warning(f"Insufficient market data for prediction: {len(market_data)} < {self.config.LOOKBACK_PERIODS}")
                return None
            
            # Prepare features
            df = self._prepare_features(market_data.copy())
            
            if df.empty or len(df) == 0:
                self.logger.warning(f"No valid features for prediction {symbol}")
                return None
            
            # Get latest features
            latest_features = df[self.feature_columns].iloc[-1:].values
            
            # Check for NaN values
            if np.isnan(latest_features).any():
                self.logger.warning(f"NaN values in features for {symbol}")
                return None
            
            # Scale features
            latest_features_scaled = self.scalers[symbol].transform(latest_features)
            
            # Make prediction
            prediction = self.models[symbol].predict(latest_features_scaled)[0]
            prediction_proba = self.models[symbol].predict_proba(latest_features_scaled)[0]
            
            # Get confidence (max probability)
            confidence = np.max(prediction_proba)
            
            # Convert prediction to signal
            signal_map = {-1: 'SELL', 0: 'HOLD', 1: 'BUY'}
            signal = signal_map.get(prediction, 'HOLD')
            
            # Get current market indicators for additional context
            current_price = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            macd = df['macd'].iloc[-1]
            bb_position = df['bb_position'].iloc[-1]
            
            prediction_result = {
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                'prediction_value': int(prediction),
                'current_price': current_price,
                'technical_indicators': {
                    'rsi': rsi,
                    'macd': macd,
                    'bb_position': bb_position
                },
                'timestamp': pd.Timestamp.now().isoformat()
            }
            
            self.logger.info(f"Prediction for {symbol}: {signal} (confidence: {confidence:.3f})")
            
            return prediction_result
            
        except Exception as e:
            self.logger.error(f"Error making prediction for {symbol}: {e}")
            return None
    
    async def update_models(self):
        """Update models with new data periodically"""
        try:
            # This would typically fetch new data and retrain models
            # For now, we'll just log that an update was attempted
            self.logger.info("Model update cycle started")
            
            # In a real implementation, you would:
            # 1. Fetch new historical data
            # 2. Retrain models with updated data
            # 3. Evaluate model performance
            # 4. Save updated models
            
        except Exception as e:
            self.logger.error(f"Error updating models: {e}")
    
    async def _save_model(self, symbol: str):
        """Save trained model and scaler"""
        try:
            os.makedirs('models', exist_ok=True)
            
            # Save model
            model_path = f'models/{symbol}_model.joblib'
            joblib.dump(self.models[symbol], model_path)
            
            # Save scaler
            scaler_path = f'models/{symbol}_scaler.joblib'
            joblib.dump(self.scalers[symbol], scaler_path)
            
            self.logger.info(f"Model saved for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error saving model for {symbol}: {e}")
    
    async def load_model(self, symbol: str) -> bool:
        """Load trained model and scaler"""
        try:
            model_path = f'models/{symbol}_model.joblib'
            scaler_path = f'models/{symbol}_scaler.joblib'
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.models[symbol] = joblib.load(model_path)
                self.scalers[symbol] = joblib.load(scaler_path)
                
                self.logger.info(f"Model loaded for {symbol}")
                return True
            else:
                self.logger.warning(f"No saved model found for {symbol}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading model for {symbol}: {e}")
            return False
