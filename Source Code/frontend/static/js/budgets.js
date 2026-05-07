/**
 * budgets.js
 * Handles setting monthly category limits and rendering progress bars with visual alerts.
 */

document.addEventListener('DOMContentLoaded', () => {

    // Helper to format currency
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
    };

    // Show Alert Helper
    const showAlert = (type, title, text) => {
        Swal.fire({
            icon: type,
            title: title,
            text: text,
            confirmButtonColor: '#006666',
            background: '#E7E5E4',
            color: '#1E2938',
            customClass: { popup: 'neu-outset', confirmButton: 'neu-btn-primary' }
        });
    };

    let categoriesMap = {};

    // Load Categories for the Form Dropdown
    const loadCategories = async () => {
        try {
            const res = await fetch('/api/categories');
            if(!res.ok) return;
            const result = await res.json();
            
            // Filter to only Expense categories
            const expCats = result.data.filter(c => c.type === 'Expense');
            
            // Build map for lookup when rendering
            result.data.forEach(c => categoriesMap[c.id] = c.name);
            
            const html = expCats.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
            document.getElementById('categorySelect').innerHTML = html || '<option value="">No Categories</option>';
        } catch (e) {
            console.error('Error loading categories', e);
        }
    };

    // Load Budgets & Calculate Status
    const loadBudgets = async () => {
        try {
            // Ensure categories are loaded first so we can resolve names
            if (Object.keys(categoriesMap).length === 0) {
                await loadCategories();
            }

            const now = new Date();
            const currentMonth = now.toISOString().slice(0, 7);
            const res = await fetch(`/api/budgets?period=${currentMonth}`);
            if(!res.ok) {
                document.getElementById('budgetsContainer').innerHTML = '<div class="col-12 text-center text-danger">Failed to load budgets.</div>';
                return;
            }
            const result = await res.json(); // Array of {id, category_id, limit, period}
            const budgets = result.data;
            
            if (budgets.length === 0) {
                document.getElementById('budgetsContainer').innerHTML = '<div class="col-12 text-center text-muted">No budgets set. Create one!</div>';
                return;
            }

            let html = '';
            // For each budget, we need to fetch its current status (spending)
            for (const b of budgets) {
                const statusRes = await fetch(`/api/budgets/status/${b.category_id}?period=${b.period}`);
                let currentSpending = 0;
                
                if (statusRes.ok) {
                    const statusData = await statusRes.json();
                    // Remaining = limit - spending, so spending = limit - remaining
                    // Actually, the backend calculates remaining = limit - (expense - income)
                    // Let's just calculate spending as Limit - Remaining
                    currentSpending = parseFloat(b.limit) - parseFloat(statusData.data.remaining);
                }
                
                const target = parseFloat(b.limit);
                let percent = (currentSpending / target) * 100;
                let displayPercent = percent;
                if (displayPercent > 100) displayPercent = 100;
                
                // Visual Alerts Logic
                let barColor = 'var(--neu-success)'; // Green < 80%
                let alertText = '';
                
                if (percent >= 100) {
                    barColor = 'var(--neu-danger)'; // Red >= 100%
                    alertText = '<span class="text-danger fw-bold ms-2">⚠️ Budget Exceeded</span>';
                } else if (percent >= 80) {
                    barColor = '#F39C12'; // Orange Warning >= 80%
                    alertText = '<span class="text-warning fw-bold ms-2">⚠️ Approaching Limit</span>';
                }

                const catName = categoriesMap[b.category_id] || 'Unknown Category';

                html += `
                <div class="col-md-6">
                    <div class="neu-outset budget-card">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <div>
                                <h4 class="mb-0 fw-bold d-inline-block" style="color: var(--neu-primary);">${catName}</h4>
                                <button class="neu-btn btn-sm text-danger ms-2" style="width: 32px; height: 32px; padding: 0; display: inline-flex; align-items: center; justify-content: center;" title="Delete Budget" onclick="deleteBudget(${b.id})"><i data-lucide="trash-2" style="width: 14px; height: 14px;"></i></button>
                            </div>
                            <span class="badge bg-secondary">${b.period}</span>
                        </div>
                        <p class="text-muted mb-2">Limit: <strong>${formatCurrency(target)}</strong> ${alertText}</p>
                        
                        <div class="progress">
                            <div class="progress-bar" role="progressbar" style="width: ${displayPercent}%; background-color: ${barColor};" aria-valuenow="${displayPercent}" aria-valuemin="0" aria-valuemax="100"></div>
                        </div>
                        
                        <div class="d-flex justify-content-between align-items-center mt-3">
                            <span class="text-muted small">Spent:</span>
                            <span class="display-font fs-5 fw-bold" style="color: ${barColor};">${formatCurrency(currentSpending)}</span>
                        </div>
                    </div>
                </div>
                `;
            }
            
            document.getElementById('budgetsContainer').innerHTML = html;
            lucide.createIcons();
        } catch (e) {
            console.error('Error loading budgets', e);
        }
    };

    // Handle Create Budget Form
    document.getElementById('createBudgetForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        
        try {
            const res = await fetch('/api/budgets', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            
            if (res.ok) {
                // Close modal via Bootstrap
                const modalEl = document.getElementById('createBudgetModal');
                bootstrap.Modal.getInstance(modalEl).hide();
                
                showAlert('success', 'Success', 'Budget set successfully.');
                e.target.reset();
                loadBudgets(); // Refresh grid
            } else {
                showAlert('error', 'Error', result.message || 'Failed to set budget.');
            }
        } catch (err) {
            console.error('Error submitting budget', err);
        }
    });

    // Handle Delete Budget
    window.deleteBudget = async (budgetId) => {
        const result = await Swal.fire({
            icon: 'question',
            title: 'Delete Budget?',
            text: 'Are you sure you want to delete this budget?',
            showCancelButton: true,
            confirmButtonText: 'Yes, delete it!',
            confirmButtonColor: '#FF2157',
            background: '#E7E5E4',
            color: '#1E2938',
            customClass: { popup: 'neu-outset', confirmButton: 'neu-btn-primary' }
        });

        if (result.isConfirmed) {
            try {
                const res = await fetch(`/api/budgets/${budgetId}`, { method: 'DELETE' });
                const json = await res.json();
                
                if (res.ok) {
                    showAlert('success', 'Deleted!', 'The budget has been deleted.');
                    loadBudgets();
                } else {
                    showAlert('error', 'Error', json.message || 'Failed to delete budget.');
                }
            } catch (err) {
                console.error('Error deleting budget', err);
            }
        }
    };

    // Default period to current month
    const now = new Date();
    const currentMonth = now.toISOString().slice(0, 7);
    document.querySelector('input[name="period"]').value = currentMonth;

    // Init
    loadBudgets(); // This will also call loadCategories
});
