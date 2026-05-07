/**
 * analytics.js
 * Handles fetching reports data, drawing Chart.js visuals, and rendering a searchable history table.
 */

document.addEventListener('DOMContentLoaded', () => {

    // Helper to format currency
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
    };

    // Shared styling variables for Chart.js
    Chart.defaults.color = '#D1D5DB';
    Chart.defaults.font.family = "'Inter', sans-serif";
    const primaryColor = '#A7FFC4';
    const dangerColor = '#F87171';
    const successColor = '#34D399';
    const surfaceColor = '#121212';

    // 1. Render Monthly Trend Chart
    const renderMonthlyTrend = async () => {
        try {
            const res = await fetch('/api/reports/monthly-trend');
            if(!res.ok) return;
            const result = await res.json();
            const data = result.data; // [{month: '2024-05', income: '1000.00', expense: '500.00'}, ...]

            const labels = data.map(d => d.month);
            const incomes = data.map(d => parseFloat(d.income));
            const expenses = data.map(d => parseFloat(d.expense));

            const ctx = document.getElementById('monthlyTrendChart').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Income',
                            data: incomes,
                            backgroundColor: successColor,
                            borderRadius: 6
                        },
                        {
                            label: 'Expense',
                            data: expenses,
                            backgroundColor: dangerColor,
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top' },
                        tooltip: {
                            callbacks: {
                                label: (context) => formatCurrency(context.raw)
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Error rendering monthly trend', e);
        }
    };

    // 2. Render Category Breakdown Doughnut Chart
    const renderCategoryChart = async () => {
        try {
            const res = await fetch('/api/reports/category-spending');
            if(!res.ok) return;
            const result = await res.json();
            // Data is [{category: 'Food', amount: '250.00'}]
            const data = result.data.filter(d => parseFloat(d.amount) > 0); // Only positive spending

            const labels = data.map(d => d.category);
            const amounts = data.map(d => parseFloat(d.amount));
            
            // Generate distinct colors
            const colors = [
                '#006666', '#FF2157', '#00A63D', '#F39C12', '#8E44AD', '#3498DB', '#34495E', '#16A085'
            ];

            const ctx = document.getElementById('categoryChart').getContext('2d');
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: amounts,
                        backgroundColor: colors.slice(0, labels.length),
                        borderWidth: 4,
                        borderColor: surfaceColor // to mimic the neumorphic inset look slightly
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                boxWidth: 12,
                                usePointStyle: true
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: (context) => ` ${context.label}: ${formatCurrency(context.raw)}`
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Error rendering category chart', e);
        }
    };

    // 3. Render Historical Table
    let allTransactions = []; // Store globally for client-side search
    
    const loadHistoricalData = async () => {
        try {
            // Need categories for mapping
            const catRes = await fetch('/api/categories');
            let categoriesMap = {};
            if (catRes.ok) {
                const catData = await catRes.json();
                catData.data.forEach(c => categoriesMap[c.id] = c.name);
            }

            // Fetch larger limit for history
            const incRes = await fetch('/api/transactions/income?limit=500');
            const expRes = await fetch('/api/transactions/expense?limit=500');
            
            if(!incRes.ok || !expRes.ok) return;
            
            const incData = await incRes.json();
            const expData = await expRes.json();
            
            allTransactions = [
                ...incData.data.map(t => ({...t, type: 'income'})),
                ...expData.data.map(t => ({...t, type: 'expense'}))
            ].map(txn => {
                txn.category_name = categoriesMap[txn.category_id] || 'Unknown';
                return txn;
            }).sort((a, b) => new Date(b.date) - new Date(a.date));

            renderTable(allTransactions);
        } catch (e) {
            console.error('Error loading history', e);
        }
    };

    const renderTable = (transactions) => {
        const tbody = document.getElementById('historyTableBody');
        if (transactions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No records found.</td></tr>';
            return;
        }

        const html = transactions.map(txn => {
            const isIncome = txn.type === 'income';
            return `
            <tr>
                <td class="text-muted">${txn.date}</td>
                <td class="fw-bold">${txn.description || (isIncome ? 'Income' : 'Expense')}</td>
                <td><span class="badge bg-secondary">${txn.category_name}</span></td>
                <td class="text-muted small">ACC-${txn.account_id}</td>
                <td class="fw-bold text-${isIncome ? 'success' : 'danger'}">${isIncome ? '+' : '-'}${formatCurrency(Math.abs(txn.amount))}</td>
            </tr>
            `;
        }).join('');
        
        tbody.innerHTML = html;
    };

    // 4. Bind Search Filtering
    document.getElementById('transactionSearch').addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = allTransactions.filter(txn => {
            const desc = (txn.description || '').toLowerCase();
            const date = (txn.date || '').toLowerCase();
            const cat = (txn.category_name || '').toLowerCase();
            return desc.includes(term) || date.includes(term) || cat.includes(term);
        });
        renderTable(filtered);
    });

    // Initialize all
    renderMonthlyTrend();
    renderCategoryChart();
    loadHistoricalData();
});
