/**
 * dashboard.js
 * Handles fetching and rendering the Total Balance and Monthly Spending cards.
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // Formatter for currency
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    };

    // Fetch Total Savings (Balance)
    const fetchTotalBalance = async () => {
        try {
            const response = await fetch('/api/accounts/total-savings');
            const result = await response.json();
            
            if (response.ok && result.data && result.data.total) {
                document.getElementById('totalBalanceVal').textContent = formatCurrency(result.data.total);
            } else {
                document.getElementById('totalBalanceVal').textContent = '$0.00';
            }
        } catch (err) {
            console.error('Error fetching total balance:', err);
            document.getElementById('totalBalanceVal').textContent = 'Error';
        }
    };

    // Fetch Monthly Trend
    const fetchMonthlyTrend = async () => {
        try {
            const response = await fetch('/api/reports/monthly-trend');
            const result = await response.json();
            
            if (response.ok && result.data && result.data.length > 0) {
                // Get the most recent month
                const latest = result.data[result.data.length - 1];
                
                document.getElementById('spendingMonthLabel').textContent = `${latest.month} Spending`;
                document.getElementById('monthlySpendingVal').textContent = formatCurrency(latest.expense);
                
                document.getElementById('incomeMonthLabel').textContent = `${latest.month} Income`;
                document.getElementById('monthlyIncomeVal').textContent = formatCurrency(latest.income);
            } else {
                document.getElementById('monthlySpendingVal').textContent = '$0.00';
                document.getElementById('monthlyIncomeVal').textContent = '$0.00';
            }
        } catch (err) {
            console.error('Error fetching monthly trend:', err);
            document.getElementById('monthlySpendingVal').textContent = 'Error';
            document.getElementById('monthlyIncomeVal').textContent = 'Error';
        }
    };

    // Fetch Dashboard Budgets
    const fetchDashboardBudgets = async () => {
        try {
            const response = await fetch('/api/budgets/dashboard');
            const result = await response.json();
            
            const container = document.getElementById('dashboardBudgetsContainer');
            
            if (response.ok && result.data && result.data.length > 0) {
                const html = result.data.map(budget => {
                    const actual = parseFloat(budget.actual_spending);
                    const limit = parseFloat(budget.limit);
                    const percent = parseFloat(budget.progress_percentage);
                    const displayPercent = Math.min(percent, 100);
                    
                    // Alert logic: Warning if >= 80% or Over Budget
                    let barColor = 'var(--neu-primary)';
                    if (percent >= 100) {
                        barColor = 'var(--neu-danger)'; // Use theme variable
                    } else if (percent >= 80) {
                        barColor = '#f39c12'; // Warning orange
                    }
                    
                    return `
                        <div class="mb-4">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="fw-bold" style="color: var(--neu-text);">${budget.category_name}</span>
                                <span class="text-muted small">${formatCurrency(actual)} / ${formatCurrency(limit)}</span>
                            </div>
                            <div class="neu-inset" style="height: 12px; border-radius: 6px; overflow: hidden; background-color: rgba(0,0,0,0.05); padding: 0;">
                                <div style="height: 100%; width: ${displayPercent}%; background-color: ${barColor}; border-radius: 6px; transition: width 0.5s ease; box-shadow: 2px 0 5px rgba(0,0,0,0.1);"></div>
                            </div>
                        </div>
                    `;
                }).join('');
                container.innerHTML = html;
            } else {
                container.innerHTML = `
                    <div class="text-center py-3">
                        <p class="text-muted mb-3">No budgets set for this month.</p>
                        <a href="/budgets" class="neu-btn-primary text-decoration-none d-inline-block px-4 py-2">Set Budget</a>
                    </div>
                `;
            }
        } catch (err) {
            console.error('Error fetching dashboard budgets:', err);
            document.getElementById('dashboardBudgetsContainer').innerHTML = '<div class="text-center text-danger">Error loading budgets.</div>';
        }
    };

    // Initialize Dashboard
    fetchTotalBalance();
    fetchMonthlyTrend();
    fetchDashboardBudgets();
});
