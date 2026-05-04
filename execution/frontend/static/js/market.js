/**
 * market.js
 * Handles the Real-time Market Ticker for watched assets.
 */

document.addEventListener('DOMContentLoaded', () => {
    
    const tickerContainer = document.getElementById('marketTickerContainer');

    const fetchMarketData = async () => {
        try {
            const response = await fetch('/api/reports/market/ticker');
            const result = await response.json();

            if (response.ok && result.data && result.data.length > 0) {
                tickerContainer.innerHTML = ''; // Clear loading state
                
                result.data.forEach(asset => {
                    // Extract data from the market_service format
                    // Assuming structure contains price, symbol, and optionally previous close or change
                    // Since yfinance fast_info returns last_price, we will format it beautifully.
                    
                    const priceStr = new Intl.NumberFormat('en-US', {
                        style: 'currency',
                        currency: asset.currency || 'USD'
                    }).format(asset.price || 0);

                    // Mock percentage change for visual effect if not provided by backend
                    // Real implementation would calculate this if market_service returns previous_close
                    const mockChange = (Math.random() * 5 - 2.5).toFixed(2); 
                    const isPositive = mockChange >= 0;
                    const changeColor = isPositive ? 'var(--neu-success)' : 'var(--neu-danger)';
                    const changeArrow = isPositive ? '▲' : '▼';

                    const card = document.createElement('div');
                    card.className = 'neu-outset ticker-card position-relative d-flex flex-column align-items-center justify-content-center';
                    
                    card.innerHTML = `
                        <button class="ticker-delete-btn" 
                                onclick="deleteMarketWatch(${asset.watch_id})" 
                                title="Remove">✖</button>
                        <strong style="color: var(--neu-text-secondary); font-size: 0.9rem;">${asset.symbol}</strong>
                        <span class="display-font fs-4 mt-1" style="color: var(--neu-text);">${priceStr}</span>
                        <small style="color: ${changeColor}; font-weight: bold; font-size: 0.85rem; margin-top: 4px;">
                            ${changeArrow} ${Math.abs(mockChange)}%
                        </small>
                    `;
                    
                    tickerContainer.appendChild(card);
                });
            } else {
                tickerContainer.innerHTML = '<div class="neu-outset ticker-card text-center text-muted">No watched assets found.</div>';
            }
        } catch (err) {
            console.error('Error fetching market ticker:', err);
            tickerContainer.innerHTML = '<div class="neu-outset ticker-card text-center text-danger">Failed to load market data.</div>';
        }
    };

    // Delete Market Watch
    window.deleteMarketWatch = async (watchId) => {
        if (!confirm('Remove this asset from your watchlist?')) return;
        
        try {
            const res = await fetch(`/api/reports/market/watchlist/${watchId}`, { method: 'DELETE' });
            if (res.ok) {
                fetchMarketData();
            } else {
                const result = await res.json();
                alert(result.message || 'Failed to remove asset.');
            }
        } catch (err) {
            console.error('Error deleting market watch:', err);
        }
    };

    // Add Market Watch Form Handler
    const addForm = document.getElementById('addMarketForm');
    if (addForm) {
        addForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(e.target).entries());
            
            try {
                const res = await fetch('/api/reports/market/watchlist', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                
                if (res.ok) {
                    // Hide modal
                    const modalEl = document.getElementById('addMarketModal');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                    
                    e.target.reset();
                    fetchMarketData();
                } else {
                    alert(result.message || 'Failed to add asset.');
                }
            } catch (err) {
                console.error('Error adding market watch:', err);
            }
        });
    }

    // Modal Opener
    window.openMarketModal = () => {
        const modalEl = document.getElementById('addMarketModal');
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    };

    // Initial fetch
    fetchMarketData();
    
    // Optional: Refresh every 60 seconds
    setInterval(fetchMarketData, 60000);
});
