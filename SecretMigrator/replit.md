# Crypto Trading Bot - System Documentation

## Overview

This is a comprehensive cryptocurrency trading bot application built with Python. The system combines artificial intelligence predictions, risk management, real-time market data processing, and user interaction through both a web dashboard and Telegram bot interface. The application is designed to automate cryptocurrency trading while providing comprehensive monitoring and control capabilities.

## System Architecture

### Core Architecture Pattern
- **Modular Microservice-like Architecture**: The system is organized into distinct modules that handle specific responsibilities
- **Async/Await Pattern**: Heavy use of Python's asyncio for handling concurrent operations
- **Event-Driven Design**: Components communicate through async events and callbacks
- **Factory Pattern**: Configuration-driven initialization of exchange connections and trading parameters

### Technology Stack
- **Backend Framework**: Python 3.11+ with asyncio for concurrent operations
- **Web Framework**: Flask for the dashboard API and web interface
- **Database**: SQLite with aiosqlite for async operations (extensible to PostgreSQL)
- **Machine Learning**: scikit-learn for AI predictions with RandomForest and GradientBoosting models
- **Exchange Integration**: CCXT library for multi-exchange support
- **Messaging**: python-telegram-bot for Telegram integration
- **Frontend**: Bootstrap 5 with vanilla JavaScript and Chart.js for visualization

## Key Components

### 1. Trading Bot Core (`bot/trading_bot.py`)
The main orchestrator that coordinates all system components. Manages the trading lifecycle, executes strategies, and handles component initialization and shutdown.

### 2. AI Prediction Engine (`bot/ai_predictor.py`)
- Uses machine learning models (Random Forest, Gradient Boosting) for price prediction
- Implements feature engineering with technical indicators
- Supports model persistence with joblib
- Provides confidence scoring for trading decisions

### 3. Exchange Manager (`bot/exchange_manager.py`)
- Abstracts exchange operations using CCXT library
- Supports multiple exchanges (Binance, etc.)
- Implements rate limiting and error handling
- Manages order execution and position tracking

### 4. Risk Management (`bot/risk_manager.py`)
- Implements daily loss limits and position size controls
- Tracks portfolio exposure and risk metrics
- Enforces maximum open positions and stop-loss rules
- Provides risk-adjusted position sizing

### 5. Data Management (`bot/data_manager.py`)
- Collects and stores market data across multiple timeframes
- Caches price data for performance optimization
- Manages historical data for backtesting and ML training

### 6. Web Dashboard (`dashboard/app.py`)
- Flask-based web interface for monitoring
- Real-time data visualization with Chart.js
- REST API endpoints for data access
- Responsive Bootstrap 5 UI

### 7. Telegram Integration (`bot/telegram_handler.py`)
- Command-based bot interface for remote control
- Real-time notifications for trades and alerts
- Status monitoring and emergency controls

### 8. Database Layer (`utils/database.py`)
- Async SQLite operations with aiosqlite
- Trade logging and performance tracking
- Market data storage and retrieval

## Data Flow

### 1. Market Data Collection
1. Exchange Manager fetches real-time price data
2. Data Manager processes and stores market data
3. Technical indicators are calculated for AI features
4. Data is cached for performance optimization

### 2. AI Prediction Pipeline
1. Historical data is preprocessed with technical indicators
2. ML models generate price direction predictions
3. Confidence scores are calculated for each prediction
4. Results are filtered by confidence threshold

### 3. Trading Decision Process
1. AI predictions are evaluated against confidence thresholds
2. Risk Manager validates position sizing and exposure limits
3. Trading signals are generated with entry/exit parameters
4. Exchange Manager executes trades with proper error handling

### 4. Monitoring and Notifications
1. Trade results are logged to database
2. Performance metrics are calculated and cached
3. Dashboard updates real-time displays
4. Telegram notifications are sent for important events

## External Dependencies

### Core Dependencies
- **ccxt**: Multi-exchange trading library for API integration
- **scikit-learn**: Machine learning framework for AI predictions
- **pandas/numpy**: Data manipulation and numerical computing
- **aiosqlite**: Async SQLite database operations
- **python-telegram-bot**: Telegram bot API integration
- **flask**: Web framework for dashboard

### Infrastructure Dependencies
- **Environment Variables**: Configuration through environment variables
- **File System**: Local storage for database and model persistence
- **Network**: Internet connectivity for exchange APIs and Telegram

## Deployment Strategy

### Development Environment
- **Replit Integration**: Configured with `.replit` file for one-click deployment
- **Python 3.11**: Modern Python version with async improvements
- **Auto-dependency Installation**: Requirements handled automatically

### Configuration Management
- **Environment-based Config**: All sensitive data through environment variables
- **Multi-environment Support**: Testnet/live trading modes
- **Centralized Configuration**: Single `config.py` file for all settings

### Scalability Considerations
- **Database Migration Path**: SQLite → PostgreSQL for production scaling
- **Async Architecture**: Built for high-concurrency operations
- **Modular Design**: Easy to scale individual components

### Security Features
- **API Key Management**: Secure storage through environment variables
- **Telegram Authorization**: Chat ID-based access control
- **Risk Limits**: Multiple layers of financial risk protection

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

- **June 26, 2025**: Enhanced external signals integration
  - Added comprehensive Market Signals dashboard section with dark theme
  - Integrated SignalsAggregator component for external trend prediction
  - Added Fear & Greed Index visualization with interactive gauge
  - Implemented social sentiment tracking and trending signals display
  - Created real-time signal sources overview with confidence scoring
  - Added /api/signals endpoint for external trading signals data

## Changelog

Changelog:
- June 25, 2025. Initial setup
- June 26, 2025. Added external signals integration and Market Signals dashboard