/**
 * transactions.js
 * Handles account and transaction management, including Strict Balance Guard modals.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Globals
    let allCategories = [];

    // Helper to format currency
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
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
            customClass: {
                popup: 'neu-outset',
                confirmButton: 'neu-btn-primary'
            }
        });
    };

    // Handle API responses specifically for Balance Guard (422)
    const handleApiResponse = async (response) => {
        const result = await response.json();
        if (response.ok) {
            return result;
        } else if (response.status === 422) {
            // STRICT BALANCE GUARD HIT
            Swal.fire({
                icon: 'error',
                title: 'Insufficient Funds!',
                text: result.message || 'This transaction would result in a negative balance.',
                confirmButtonText: 'Review Amount',
                confirmButtonColor: '#FF2157',
                background: '#E7E5E4',
                color: '#1E2938',
                customClass: { popup: 'neu-outset' }
            });
            throw new Error('Balance Guard');
        } else {
            showAlert('error', 'Error', result.message || 'Something went wrong');
            throw new Error(result.message);
        }
    };

    // Load Accounts
    const loadAccounts = async () => {
        try {
            const res = await fetch('/api/accounts');
            if(!res.ok) return;
            const result = await res.json();
            
            const listHtml = result.data.map(acc => `
                <div class="neu-inset account-item">
                    <div>
                        <strong style="color: var(--neu-primary);">${acc.name}</strong><br>
                        <small class="text-muted">#${acc.number}</small>
                    </div>
                    <div class="display-font fs-5 fw-bold">
                        ${formatCurrency(acc.balance)}
                    </div>
                </div>
            `).join('');
            
            document.getElementById('accountsListContainer').innerHTML = listHtml || '<p class="text-muted">No accounts found.</p>';

            // Populate select dropdown
            const selectHtml = result.data.map(acc => `<option value="${acc.id}">${acc.name} (${formatCurrency(acc.balance)})</option>`).join('');
            document.getElementById('accountSelect').innerHTML = selectHtml || '<option value="">No Accounts</option>';
            
        } catch (e) {
            console.error('Error loading accounts', e);
        }
    };

    // Load Categories
    const loadCategories = async () => {
        try {
            const res = await fetch('/api/categories');
            if(!res.ok) return;
            const result = await res.json();
            allCategories = result.data;
            updateCategoryDropdown();
        } catch (e) {
            console.error('Error loading categories', e);
        }
    };

    // Update Category dropdown based on selected type and refresh modal list
    const updateCategoryDropdown = () => {
        const type = document.getElementById('txnTypeSelect').value;
        const filtered = allCategories.filter(c => c.type === type);
        const html = filtered.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        document.getElementById('categorySelect').innerHTML = html || '<option value="">No Categories</option>';
        
        // Also render modal list
        const modalHtml = allCategories.map(c => `
            <div class="d-flex justify-content-between align-items-center mb-2 p-2 rounded" style="background: rgba(255,255,255,0.4);">
                <div>
                    <strong>${c.name}</strong> 
                    <span class="badge ${c.type === 'Income' ? 'bg-success' : 'bg-danger'} ms-2">${c.type}</span>
                    ${c.is_system ? '<span class="badge bg-secondary ms-1">System</span>' : ''}
                </div>
                ${c.is_system ? '<span class="text-muted small px-2">Read-only</span>' : `<button class="btn btn-sm text-danger border-0 delete-cat-btn" data-id="${c.id}" title="Delete Category">✖</button>`}
            </div>
        `).join('');
        
        const catListContainer = document.getElementById('categoryListContainer');
        if (catListContainer) {
            catListContainer.innerHTML = modalHtml || '<p class="text-muted small">No categories found.</p>';
            
            // Attach delete listeners
            catListContainer.querySelectorAll('.delete-cat-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    if (confirm('Are you sure you want to delete this category?')) {
                        try {
                            const res = await fetch(`/api/categories/${id}`, { method: 'DELETE' });
                            const result = await res.json();
                            if (res.ok) {
                                loadCategories(); // Refresh all
                            } else {
                                showAlert('error', 'Error', result.message);
                            }
                        } catch (err) {
                            console.error(err);
                        }
                    }
                });
            });
        }
    };

    // Add Category Form Handler
    const addCatForm = document.getElementById('addCategoryForm');
    if (addCatForm) {
        addCatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(e.target).entries());
            try {
                const res = await fetch('/api/categories', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (res.ok) {
                    e.target.reset();
                    loadCategories();
                } else {
                    showAlert('error', 'Validation Failed', result.message);
                }
            } catch (err) {
                console.error(err);
            }
        });
    }

    document.getElementById('txnTypeSelect').addEventListener('change', updateCategoryDropdown);

    // Load Recent Transactions
    const loadTransactions = async () => {
        try {
            const incRes = await fetch('/api/transactions/income?limit=30');
            const expRes = await fetch('/api/transactions/expense?limit=30');

            if (!incRes.ok || !expRes.ok) return;

            const incData = await incRes.json();
            const expData = await expRes.json();

            const incomes  = (incData.data || []).map(t => ({...t, type: 'Income'}));
            const expenses = (expData.data || []).map(t => ({...t, type: 'Expense'}));

            const merged = [...incomes, ...expenses]
                .sort((a, b) => new Date(b.date) - new Date(a.date))
                .slice(0, 30);

            const listHtml = merged.map(txn => {
                const isInc    = txn.type === 'Income';
                const color    = isInc ? 'var(--neu-success)' : 'var(--neu-danger)';
                const sign     = isInc ? '+' : '-';
                const syncBadge = txn.external_trans_id
                    ? '<span class="badge rounded-pill bg-info ms-1" style="font-size:0.6rem;vertical-align:middle;opacity:0.8;">Synced</span>'
                    : '';
                // Safely encode txn for inline onclick
                const txnJson = encodeURIComponent(JSON.stringify(txn));

                return `
                <div class="neu-inset transaction-item d-flex justify-content-between align-items-center">
                    <div>
                        <div class="d-flex align-items-center">
                            <strong style="color: var(--neu-text);">${txn.description || txn.type}</strong>
                            ${syncBadge}
                        </div>
                        <small class="text-muted">${txn.date}</small>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <div class="display-font fs-6" style="color: ${color}; font-weight: bold;">
                            ${sign} ${formatCurrency(txn.amount)}
                        </div>
                        <button class="txn-action-btn edit-btn" title="Edit"
                            onclick="openEditModal(decodeURIComponent('${txnJson}'))">✎</button>
                        <button class="txn-action-btn delete-btn" title="Delete"
                            onclick="deleteTransaction(${txn.id}, '${txn.type}')">✖</button>
                    </div>
                </div>`;
            }).join('');

            document.getElementById('transactionsListContainer').innerHTML =
                listHtml || '<p class="text-muted">No transactions found.</p>';

        } catch (e) {
            console.error('Error loading txns', e);
        }
    };

    // ── Open Edit Modal ──────────────────────────────────────────────────────
    window.openEditModal = (txnRaw) => {
        const txn = typeof txnRaw === 'string' ? JSON.parse(txnRaw) : txnRaw;

        document.getElementById('editTxnId').value       = txn.id;
        document.getElementById('editTxnType').value     = txn.type;
        document.getElementById('editAmount').value      = txn.amount;
        document.getElementById('editDate').value        = txn.date;
        document.getElementById('editDescription').value = txn.description || '';

        // Populate Account dropdown
        fetch('/api/accounts').then(r => r.json()).then(result => {
            const html = (result.data || []).map(a =>
                `<option value="${a.id}" ${a.id == txn.account_id ? 'selected' : ''}>${a.name}</option>`
            ).join('');
            document.getElementById('editAccountSelect').innerHTML =
                html || '<option value="">No Accounts</option>';
        });

        // Populate Category dropdown filtered by txn type
        fetch('/api/categories').then(r => r.json()).then(result => {
            const filtered = (result.data || []).filter(c => c.type === txn.type);
            const html = filtered.map(c =>
                `<option value="${c.id}" ${c.id == txn.category_id ? 'selected' : ''}>${c.name}</option>`
            ).join('');
            document.getElementById('editCategorySelect').innerHTML =
                html || '<option value="">No Categories</option>';
        });

        new bootstrap.Modal(document.getElementById('editTransactionModal')).show();
    };

    // ── Edit Transaction Form Submit ─────────────────────────────────────────
    document.getElementById('editTransactionForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id   = document.getElementById('editTxnId').value;
        const type = document.getElementById('editTxnType').value;

        const payload = {
            amount:      document.getElementById('editAmount').value,
            date:        document.getElementById('editDate').value,
            description: document.getElementById('editDescription').value,
            account_id:  parseInt(document.getElementById('editAccountSelect').value),
            category_id: parseInt(document.getElementById('editCategorySelect').value),
        };

        const endpoint = type === 'Income'
            ? `/api/transactions/income/${id}`
            : `/api/transactions/expense/${id}`;

        try {
            const res = await fetch(endpoint, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            await handleApiResponse(res);
            bootstrap.Modal.getInstance(document.getElementById('editTransactionModal'))?.hide();
            showAlert('success', 'Updated', 'Transaction updated successfully.');
            loadAccounts();
            loadTransactions();
        } catch (err) { /* handled by handleApiResponse */ }
    });

    // ── Delete Transaction ───────────────────────────────────────────────────
    window.deleteTransaction = async (id, type) => {
        const confirm = await Swal.fire({
            icon: 'warning',
            title: 'Delete Transaction?',
            text: 'This action cannot be undone.',
            showCancelButton: true,
            confirmButtonText: 'Yes, Delete',
            confirmButtonColor: '#FF2157',
            cancelButtonText: 'Cancel',
            background: '#E7E5E4',
            color: '#1E2938',
            customClass: { popup: 'neu-outset' }
        });
        if (!confirm.isConfirmed) return;

        const endpoint = type === 'Income'
            ? `/api/transactions/income/${id}`
            : `/api/transactions/expense/${id}`;

        try {
            const res  = await fetch(endpoint, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok) {
                showAlert('success', 'Deleted', 'Transaction removed successfully.');
                loadAccounts();
                loadTransactions();
            } else {
                showAlert('error', 'Error', data.message || 'Failed to delete.');
            }
        } catch (err) {
            console.error('Delete error', err);
        }
    };

    // ── Add Account Form ─────────────────────────────────────────────────────
    document.getElementById('addAccountForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        try {
            const res = await fetch('/api/accounts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            await handleApiResponse(res);
            showAlert('success', 'Success', 'Account added successfully.');
            e.target.reset();
            loadAccounts();
        } catch (e) { /* handled */ }
    });

    // ── Add Transaction Form ─────────────────────────────────────────────────
    document.getElementById('addTransactionForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        const type = data.type;
        const endpoint = type === 'Income' ? '/api/transactions/income' : '/api/transactions/expense';
        delete data.type;

        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            await handleApiResponse(res);
            showAlert('success', 'Success', 'Transaction recorded successfully.');
            e.target.reset();
            loadAccounts();
            loadTransactions();
            updateCategoryDropdown();
        } catch (e) { /* handled by handleApiResponse */ }
    });

    // ── Init ─────────────────────────────────────────────────────────────────
    loadAccounts();
    loadCategories();
    loadTransactions();
    document.querySelector('input[name="date"]').valueAsDate = new Date();
});
