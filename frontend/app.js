// API Endpoint
const API_URL = 'http://127.0.0.1:5000/api';

// Format currency
const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
};

// Initialize WebSocket connection
const socket = io('http://127.0.0.1:5000');

socket.on('connect', () => {
    console.log('Connected to WebSocket server');
    document.querySelector('.status-indicator').innerHTML = '<span class="pulse"></span> System Online';
});

socket.on('disconnect', () => {
    console.log('Disconnected from WebSocket server');
    document.querySelector('.status-indicator').innerHTML = '<span class="pulse" style="background-color: var(--danger); box-shadow: none;"></span> System Offline';
});

socket.on('dashboard_update', (data) => {
    console.log('Received real-time update', data);
    updateDashboard(data.stats);
    updateTradesTable(data.trades);
});

// Update the DOM
function updateDashboard(data) {
    // Basic Metrics
    document.getElementById('equity-val').textContent = formatCurrency(data.equity);
    document.getElementById('win-rate-val').textContent = data.win_rate.toFixed(1) + '%';
    document.getElementById('active-pos-val').textContent = data.active_positions;
    
    // Daily PnL
    const dailyEl = document.getElementById('daily-pnl');
    dailyEl.textContent = `${data.daily_pnl >= 0 ? '+' : ''} ${formatCurrency(data.daily_pnl)} Today`;
    dailyEl.className = `delta ${data.daily_pnl >= 0 ? 'positive' : 'negative'}`;

    // === OPERATION $100 LOGIC ===
    const weeklyPnl = data.weekly_pnl || 0;
    const target = data.target || 100;
    
    // Calculate percentage (clamp between 0 and 100)
    let percentage = (weeklyPnl / target) * 100;
    if (percentage < 0) percentage = 0;
    if (percentage > 100) percentage = 100;

    // Update UI text
    document.getElementById('current-profit').textContent = formatCurrency(weeklyPnl);
    document.getElementById('percent-complete').textContent = `${percentage.toFixed(1)}% Complete`;
    
    const remainingEl = document.getElementById('remaining-amount');
    if (weeklyPnl >= target) {
        remainingEl.textContent = 'Target Achieved!';
        remainingEl.style.color = 'var(--success)';
        document.getElementById('progress-fill').style.background = 'linear-gradient(90deg, #00E676, #69F0AE)';
    } else {
        const remaining = target - weeklyPnl;
        remainingEl.textContent = `${formatCurrency(remaining)} needed to hit target`;
    }

    // Animate the progress bar width
    document.getElementById('progress-fill').style.width = `${percentage}%`;
}

function updateTradesTable(trades) {
    const tbody = document.getElementById('trades-body');
    tbody.innerHTML = '';
    
    trades.forEach(trade => {
        const tr = document.createElement('tr');
        
        // Format time
        const time = new Date(trade.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        // Format PnL
        const isWin = trade.pnl > 0;
        const isLoss = trade.pnl < 0;
        const isTie = trade.pnl === 0;

        let resultHtml = `<span class="text-neutral">Pending</span>`;
        if (trade.pnl !== null && trade.pnl !== undefined) {
             if (isWin) {
                 resultHtml = `<span class="win">+${formatCurrency(trade.pnl)}</span>`;
             } else if (isLoss) {
                 resultHtml = `<span class="loss">${formatCurrency(trade.pnl)}</span>`;
             } else {
                 resultHtml = `<span class="text-neutral">$0.00</span>`;
             }
        }
            
        tr.innerHTML = `
            <td>${time}</td>
            <td style="font-weight: 600;">${trade.symbol}</td>
            <td>${trade.side}</td>
            <td>${resultHtml}</td>
        `;
        tbody.appendChild(tr);
    });
}
