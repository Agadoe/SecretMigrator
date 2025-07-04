/**
 * Trading Bot Dashboard JavaScript
 */

class TradingBotDashboard {
    constructor() {
        this.charts = {};
        this.refreshInterval = 10000; // 10 seconds
        this.intervalId = null;
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupTabs();
        this.setupCharts();
        this.loadInitialData();
        this.startAutoRefresh();
    }
    
    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('[data-tab]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchTab(link.getAttribute('data-tab'));
            });
        });
        
        // Refresh button
        const refreshBtn = document.getElementById('refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshAllData());
        }
        
        // Trade filter
        const tradeFilter = document.getElementById('trade-filter');
        if (tradeFilter) {
            tradeFilter.addEventListener('change', () => this.loadTrades());
        }
        
        // Bot control buttons (disabled for read-only dashboard)
        ['start-bot', 'pause-bot', 'stop-bot'].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', () => {
                    this.showAlert('Bot controls are not available in this dashboard. Use Telegram commands.', 'warning');
                });
            }
        });
    }
    
    setupTabs() {
        // Set up tab switching functionality
        this.currentTab = 'overview';
    }
    
    switchTab(tabName) {
        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Remove active class from all nav links
        document.querySelectorAll('[data-tab]').forEach(link => {
            link.classList.remove('active');
        });
        
        // Show selected tab content
        const targetTab = document.getElementById(tabName);
        const targetLink = document.querySelector(`[data-tab="${tabName}"]`);
        
        if (targetTab && targetLink) {
            targetTab.classList.add('active');
            targetLink.classList.add('active');
            this.currentTab = tabName;
            
            // Load tab-specific data
            this.loadTabData(tabName);
        }
    }
    
    loadTabData(tabName) {
        switch (tabName) {
            case 'overview':
                this.loadOverviewData();
                break;
            case 'positions':
                this.loadPositions();
                break;
            case 'trades':
                this.loadTrades();
                break;
            case 'performance':
                this.loadPerformanceData();
                break;
            case 'signals':
                this.loadSignalsData();
                break;
            case 'settings':
                this.loadSettings();
                break;
        }
    }
    
    setupCharts() {
        // Performance Chart
        const performanceCtx = document.getElementById('performanceChart');
        if (performanceCtx) {
            this.charts.performance = new Chart(performanceCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Portfolio Value',
                        data: [],
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toLocaleString();
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Allocation Chart
        const allocationCtx = document.getElementById('allocationChart');
        if (allocationCtx) {
            this.charts.allocation = new Chart(allocationCtx, {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: [
                            '#3498db',
                            '#2ecc71',
                            '#f39c12',
                            '#e74c3c',
                            '#9b59b6'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
        
        // Daily Performance Chart
        const dailyPerfCtx = document.getElementById('dailyPerformanceChart');
        if (dailyPerfCtx) {
            this.charts.dailyPerformance = new Chart(dailyPerfCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Daily P&L',
                        data: [],
                        backgroundColor: function(context) {
                            const value = context.parsed.y;
                            return value >= 0 ? '#27ae60' : '#e74c3c';
                        }
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(2);
                                }
                            }
                        }
                    }
                }
            });
        }
    }
    
    async loadInitialData() {
        await this.loadOverviewData();
    }
    
    async loadOverviewData() {
        try {
            this.showLoading(true);
            
            // Load status, statistics, and market data in parallel
            const [status, statistics, marketData] = await Promise.all([
                this.fetchAPI('/api/status'),
                this.fetchAPI('/api/statistics'),
                this.fetchAPI('/api/market-data')
            ]);
            
            this.updateStatusCards(status, statistics);
            this.updateMarketData(marketData);
            this.updatePerformanceChart(statistics);
            
        } catch (error) {
            this.showAlert('Failed to load overview data: ' + error.message, 'danger');
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadPositions() {
        try {
            this.showLoading(true);
            const positions = await this.fetchAPI('/api/positions');
            this.updatePositionsTable(positions);
        } catch (error) {
            this.showAlert('Failed to load positions: ' + error.message, 'danger');
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadTrades() {
        try {
            this.showLoading(true);
            const filter = document.getElementById('trade-filter')?.value || 'all';
            const params = filter !== 'all' ? `?status=${filter}` : '';
            const trades = await this.fetchAPI('/api/trades' + params);
            this.updateTradesTable(trades);
        } catch (error) {
            this.showAlert('Failed to load trades: ' + error.message, 'danger');
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadPerformanceData() {
        try {
            this.showLoading(true);
            const performance = await this.fetchAPI('/api/performance');
            this.updatePerformanceMetrics(performance);
            this.updateDailyPerformanceChart(performance);
        } catch (error) {
            this.showAlert('Failed to load performance data: ' + error.message, 'danger');
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadSignalsData() {
        try {
            const signals = await this.fetchAPI('/api/signals');
            this.updateSignalsDisplay(signals);
        } catch (error) {
            console.error('Error loading signals data:', error);
            this.showAlert('Failed to load signals data', 'error');
        }
    }

    updateSignalsDisplay(signals) {
        // Update overall sentiment
        const sentiment = signals.market_sentiment;
        this.updateElement('overall-sentiment', sentiment.overall);
        document.getElementById('overall-sentiment').className = 
            sentiment.overall === 'BULLISH' ? 'text-success' : 
            sentiment.overall === 'BEARISH' ? 'text-danger' : 'text-warning';
        
        document.getElementById('sentiment-strength').style.width = `${sentiment.strength * 100}%`;
        document.getElementById('sentiment-strength').className = 
            `progress-bar ${sentiment.overall === 'BULLISH' ? 'bg-success' : 
            sentiment.overall === 'BEARISH' ? 'bg-danger' : 'bg-warning'}`;
        
        this.updateElement('sentiment-confidence', `${Math.round(sentiment.confidence * 100)}%`);

        // Update signal sources
        const sourcesContainer = document.getElementById('signal-sources');
        sourcesContainer.innerHTML = '';
        
        Object.entries(signals.signals_by_source).forEach(([source, data]) => {
            const col = document.createElement('div');
            col.className = 'col-md-4 mb-3';
            
            const signalColor = data.signal === 'BUY' || data.signal === 'STRONG_BUY' ? 'success' : 
                               data.signal === 'SELL' || data.signal === 'STRONG_SELL' ? 'danger' : 'warning';
            
            col.innerHTML = `
                <div class="text-center">
                    <h6 class="text-muted">${source}</h6>
                    <span class="badge bg-${signalColor}">${data.signal}</span>
                </div>
            `;
            sourcesContainer.appendChild(col);
        });

        // Update trending signals
        const trendingContainer = document.getElementById('trending-signals');
        trendingContainer.innerHTML = '';
        
        signals.trending_signals.forEach(signal => {
            const signalColor = signal.signal === 'BUY' || signal.signal === 'STRONG_BUY' ? 'success' : 
                               signal.signal === 'SELL' || signal.signal === 'STRONG_SELL' ? 'danger' : 'warning';
            
            const item = document.createElement('div');
            item.className = 'list-group-item d-flex justify-content-between align-items-center';
            item.innerHTML = `
                <div>
                    <h6 class="mb-1">${signal.source}</h6>
                    <p class="mb-1 text-muted">${signal.symbol || ''} ${signal.sentiment || signal.pattern || signal.activity || ''}</p>
                    <small class="text-muted">Confidence: ${Math.round(signal.confidence * 100)}%</small>
                </div>
                <span class="badge bg-${signalColor} rounded-pill">${signal.signal}</span>
            `;
            trendingContainer.appendChild(item);
        });

        // Update Fear & Greed gauge
        this.updateFearGreedGauge(signals.trending_signals.find(s => s.source === 'Fear & Greed Index'));
    }

    updateFearGreedGauge(fearGreedData) {
        if (!fearGreedData) return;
        
        const canvas = document.getElementById('fearGreedGauge');
        const ctx = canvas.getContext('2d');
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = 80;
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw gauge background
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, Math.PI, 2 * Math.PI);
        ctx.strokeStyle = '#e9ecef';
        ctx.lineWidth = 20;
        ctx.stroke();
        
        // Calculate angle for current value (0-100 scale)
        const angle = Math.PI + (fearGreedData.value / 100) * Math.PI;
        
        // Draw gauge fill
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, Math.PI, angle);
        ctx.strokeStyle = fearGreedData.value > 75 ? '#dc3545' : 
                         fearGreedData.value > 50 ? '#ffc107' : '#28a745';
        ctx.lineWidth = 20;
        ctx.stroke();
        
        // Update text values
        this.updateElement('fear-greed-value', fearGreedData.value);
        this.updateElement('fear-greed-sentiment', fearGreedData.sentiment);
        
        const sentimentEl = document.getElementById('fear-greed-sentiment');
        sentimentEl.className = fearGreedData.value > 75 ? 'text-danger' : 
                               fearGreedData.value > 50 ? 'text-warning' : 'text-success';
    }

    loadSettings() {
        // Load bot configuration settings
        // These would typically come from the API
        const settings = {
            tradingPairs: 'BTC/USDT, ETH/USDT, ADA/USDT',
            maxPositionSize: '100.00',
            stopLossPct: '2.0',
            takeProfitPct: '5.0'
        };
        
        document.getElementById('trading-pairs').value = settings.tradingPairs;
        document.getElementById('max-position-size').value = settings.maxPositionSize;
        document.getElementById('stop-loss-pct').value = settings.stopLossPct;
        document.getElementById('take-profit-pct').value = settings.takeProfitPct;
    }
    
    updateStatusCards(status, statistics) {
        // Update account balance
        const balance = status.balance?.USDT || 0;
        this.updateElement('account-balance', this.formatCurrency(balance));
        
        // Update daily P&L (calculated from recent trades)
        const dailyPnl = statistics.total_pnl || 0;
        const dailyPnlElement = document.getElementById('daily-pnl');
        if (dailyPnlElement) {
            dailyPnlElement.textContent = this.formatCurrency(dailyPnl);
            dailyPnlElement.className = dailyPnl >= 0 ? 'text-success' : 'text-danger';
        }
        
        // Update active positions
        this.updateElement('active-positions', status.active_positions || 0);
        
        // Update total trades
        this.updateElement('total-trades', statistics.total_trades || 0);
        
        // Update bot status
        const statusElement = document.getElementById('bot-status');
        if (statusElement) {
            const isRunning = status.running;
            statusElement.textContent = isRunning ? 'Running' : 'Stopped';
            statusElement.className = `badge ${isRunning ? 'bg-success' : 'bg-danger'}`;
        }
    }
    
    updateMarketData(marketData) {
        const tbody = document.getElementById('market-data');
        if (!tbody) return;
        
        if (!marketData || Object.keys(marketData).length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No market data available</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        
        Object.entries(marketData).forEach(([symbol, data]) => {
            const row = document.createElement('tr');
            const changeClass = data.change_24h >= 0 ? 'text-success' : 'text-danger';
            const changeIcon = data.change_24h >= 0 ? '▲' : '▼';
            
            row.innerHTML = `
                <td><strong>${symbol}</strong></td>
                <td>$${data.price?.toFixed(4) || '0.0000'}</td>
                <td class="${changeClass}">${changeIcon} ${Math.abs(data.change_24h || 0).toFixed(2)}%</td>
                <td>$${(data.volume_24h || 0).toLocaleString()}</td>
                <td>$${(data.high_24h || 0).toFixed(4)}</td>
                <td>$${(data.low_24h || 0).toFixed(4)}</td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    updatePositionsTable(positions) {
        const tbody = document.getElementById('positions-data');
        if (!tbody) return;
        
        if (!positions || positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center">No active positions</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        
        positions.forEach(position => {
            const row = document.createElement('tr');
            const pnl = position.pnl || 0;
            const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
            const sideClass = position.side === 'long' ? 'text-success' : 'text-danger';
            
            row.innerHTML = `
                <td><strong>${position.symbol}</strong></td>
                <td><span class="badge ${sideClass === 'text-success' ? 'bg-success' : 'bg-danger'}">${position.side.toUpperCase()}</span></td>
                <td>${position.amount?.toFixed(8) || '0.00000000'}</td>
                <td>$${position.entry_price?.toFixed(4) || '0.0000'}</td>
                <td>$${position.current_price?.toFixed(4) || '0.0000'}</td>
                <td class="${pnlClass}">$${pnl.toFixed(2)}</td>
                <td>$${position.stop_loss?.toFixed(4) || '0.0000'}</td>
                <td>$${position.take_profit?.toFixed(4) || '0.0000'}</td>
                <td><span class="badge bg-primary">${position.status || 'OPEN'}</span></td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    updateTradesTable(trades) {
        const tbody = document.getElementById('trades-data');
        if (!tbody) return;
        
        if (!trades || trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center">No trades found</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        
        trades.forEach(trade => {
            const row = document.createElement('tr');
            const pnl = trade.pnl || 0;
            const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
            const sideClass = trade.side === 'long' ? 'text-success' : 'text-danger';
            const statusClass = trade.status === 'closed' ? 'bg-secondary' : 'bg-primary';
            
            const openTime = new Date(trade.open_time).toLocaleString();
            const confidence = trade.prediction_data?.confidence || 0;
            
            row.innerHTML = `
                <td>${openTime}</td>
                <td><strong>${trade.symbol}</strong></td>
                <td><span class="badge ${sideClass === 'text-success' ? 'bg-success' : 'bg-danger'}">${trade.side.toUpperCase()}</span></td>
                <td>${trade.amount?.toFixed(8) || '0.00000000'}</td>
                <td>$${trade.entry_price?.toFixed(4) || '0.0000'}</td>
                <td class="${pnlClass}">$${pnl.toFixed(2)}</td>
                <td><span class="badge ${statusClass}">${trade.status?.toUpperCase() || 'OPEN'}</span></td>
                <td>${(confidence * 100).toFixed(1)}%</td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    updatePerformanceChart(statistics) {
        if (!this.charts.performance) return;
        
        // This would typically come from historical performance data
        // For now, we'll create sample data based on statistics
        const chart = this.charts.performance;
        const days = 30;
        const labels = [];
        const data = [];
        
        for (let i = days; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString());
            
            // Generate sample portfolio value based on total P&L
            const baseValue = 1000;
            const randomVariation = (Math.random() - 0.5) * 100;
            data.push(baseValue + (statistics.total_pnl || 0) + randomVariation);
        }
        
        chart.data.labels = labels;
        chart.data.datasets[0].data = data;
        chart.update();
    }
    
    updatePerformanceMetrics(performance) {
        // Update performance metrics
        const metrics = performance[0] || {};
        
        this.updateElement('total-return', '0%'); // Would calculate from data
        this.updateElement('win-rate', `${(metrics.winning_trades / Math.max(metrics.total_trades, 1) * 100).toFixed(1)}%`);
        this.updateElement('max-drawdown', '0%'); // Would calculate from data
        this.updateElement('sharpe-ratio', '0.00'); // Would calculate from returns
        
        // Update risk metrics
        this.updateElement('risk-level', 'LOW');
        this.updateElement('daily-loss-limit', '$50.00');
        this.updateElement('max-positions', '3');
        
        // Update risk progress bar
        const riskProgress = document.getElementById('risk-progress');
        if (riskProgress) {
            riskProgress.style.width = '25%'; // Sample value
            riskProgress.className = 'progress-bar bg-success';
        }
    }
    
    updateDailyPerformanceChart(performance) {
        if (!this.charts.dailyPerformance || !performance) return;
        
        const chart = this.charts.dailyPerformance;
        const labels = performance.map(p => new Date(p.date).toLocaleDateString());
        const data = performance.map(p => p.total_pnl || 0);
        
        chart.data.labels = labels;
        chart.data.datasets[0].data = data;
        
        // Update colors based on values
        chart.data.datasets[0].backgroundColor = data.map(value => 
            value >= 0 ? '#27ae60' : '#e74c3c'
        );
        
        chart.update();
    }
    
    async fetchAPI(endpoint) {
        const response = await fetch(endpoint);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    }
    
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
    
    formatCurrency(amount, decimals = 2) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(amount);
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.toggle('show', show);
        }
        this.isLoading = show;
    }
    
    showAlert(message, type = 'info') {
        // Create and show bootstrap alert
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Add to top of main content
        const mainContent = document.querySelector('.col-md-9.col-lg-10');
        if (mainContent) {
            mainContent.insertBefore(alertDiv, mainContent.firstChild);
            
            // Auto dismiss after 5 seconds
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }
    
    startAutoRefresh() {
        this.intervalId = setInterval(() => {
            if (!this.isLoading) {
                this.loadTabData(this.currentTab);
            }
        }, this.refreshInterval);
    }
    
    stopAutoRefresh() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
    
    async refreshAllData() {
        await this.loadTabData(this.currentTab);
        this.showAlert('Data refreshed successfully', 'success');
    }
    
    destroy() {
        this.stopAutoRefresh();
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new TradingBotDashboard();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        window.dashboard.destroy();
    }
});
