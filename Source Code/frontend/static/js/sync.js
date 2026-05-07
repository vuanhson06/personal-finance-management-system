/**
 * sync.js — Bank Sync Record Ledger
 * Fetches and renders externally-sourced transactions (ExternalTransID IS NOT NULL).
 * Auto-refreshes every 10 seconds to capture live webhook events.
 */

document.addEventListener('DOMContentLoaded', () => {

    const formatCurrency = (amount) =>
        new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

    const formatDate = (iso) => {
        const d = new Date(iso);
        return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
            + ' · '
            + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    };

    // ─── Load & Render Sync Records ───────────────────────────────────────────
    const loadSyncLog = async () => {
        try {
            const res = await fetch('/api/sync/records');
            if (!res.ok) throw new Error('Failed to fetch sync records.');
            const result = await res.json();
            const records = result.data || [];

            renderStats(records);
            renderTable(records);

            // Update refresh label
            const now = new Date();
            document.getElementById('lastRefreshedLabel').textContent =
                `Last refreshed: ${now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
        } catch (err) {
            console.error('Sync log error:', err);
            document.getElementById('syncTableBody').innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-danger py-4">
                        ⚠️ Failed to load sync records. Check server connection.
                    </td>
                </tr>`;
        }
    };

    // ─── Stats Cards ──────────────────────────────────────────────────────────
    const renderStats = (records) => {
        document.getElementById('statTotal').textContent = records.length;

        const incomes  = records.filter(r => r.type === 'income');
        const expenses = records.filter(r => r.type === 'expense');

        const totalIncome  = incomes.reduce((s, r) => s + parseFloat(r.amount), 0);
        const totalExpense = expenses.reduce((s, r) => s + parseFloat(r.amount), 0);

        document.getElementById('statIncome').textContent  = formatCurrency(totalIncome);
        document.getElementById('statExpense').textContent = formatCurrency(totalExpense);
        document.getElementById('statLastDate').textContent =
            records.length > 0
                ? new Date(records[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                : '—';
    };

    let categories = [];

    const fetchCategories = async () => {
        try {
            const res = await fetch('/api/categories');
            if (res.ok) {
                const result = await res.json();
                categories = result.data;
                const select = document.getElementById('categorySelect');
                if (select) {
                    select.innerHTML = '<option value="">Choose Category...</option>' + 
                        categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
                }
            }
        } catch (err) {
            console.error('Error fetching categories:', err);
        }
    };

    window.openCategoryModal = (txnId, txnType, currentCatId) => {
        document.getElementById('editTxnId').value = txnId;
        document.getElementById('editTxnType').value = txnType;
        const select = document.getElementById('categorySelect');
        if (select) select.value = currentCatId || "";
        
        const modal = new bootstrap.Modal(document.getElementById('updateCategoryModal'));
        modal.show();
    };

    // ─── Ledger Table ─────────────────────────────────────────────────────────
    const renderTable = (records) => {
        const tbody = document.getElementById('syncTableBody');

        if (records.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7">
                        <div class="empty-state">
                            <div class="radar-icon">📡</div>
                            <h5 class="mt-4 fw-bold" style="color: var(--neu-text);">
                                Waiting for external bank signals...
                            </h5>
                            <p class="text-muted mt-2" style="max-width: 460px; margin: 0 auto; font-size: 0.88rem;">
                                Send a JSON payload from an external provider (e.g. ReqBin via Ngrok) to see live updates here.
                            </p>
                            <code class="d-block mt-4 text-muted" style="font-size: 0.78rem; opacity: 0.7;">
                                POST https://&lt;ngrok-url&gt;/webhook/transaction
                            </code>
                        </div>
                    </td>
                </tr>`;
            return;
        }

        tbody.innerHTML = records.map(r => {
            const isIncome    = r.type === 'income';
            const amountColor = isIncome ? 'text-success' : 'text-danger';
            const amountSign  = isIncome ? '+' : '−';

            // Type: clean pill badge, no emoji icon card
            const typeBadge = isIncome
                ? `<span class="badge rounded-pill" style="background:var(--neu-success); color:#121212; font-size:.78rem; padding:5px 12px; font-weight:600;">Income</span>`
                : `<span class="badge rounded-pill" style="background:#8E44AD; color:#fff; font-size:.78rem; padding:5px 12px; font-weight:600;">Expense</span>`;

            // Category: clickable pill badge
            const currentCat = categories.find(c => c.name === r.category_name);
            const currentCatId = currentCat ? currentCat.id : "";
            
            const catBadge = `<span class="badge rounded-pill ${r.category_name.toLowerCase() === 'others' ? 'bg-success' : 'bg-secondary'}" 
                                   style="font-size:.78rem; padding:5px 10px; cursor: pointer;" 
                                   onclick="openCategoryModal(${r.id}, '${r.type}', '${currentCatId}')"
                                   title="Click to change category">${r.category_name}</span>`;

            return `
            <tr>
                <td class="text-muted" style="white-space:nowrap;">${formatDate(r.date)}</td>
                <td class="fw-bold">${r.description || '<span class="text-muted fst-italic">—</span>'}</td>
                <td>${catBadge}</td>
                <td>${typeBadge}</td>
                <td class="text-muted small">ACC-${r.account_id}</td>
                <td class="fw-bold ${amountColor}">${amountSign}${formatCurrency(Math.abs(r.amount))}</td>
                <td><span class="ext-id-pill" title="${r.external_trans_id}">${r.external_trans_id}</span></td>
            </tr>`;
        }).join('');
    };

    // ─── Update Category Form Handler ─────────────────────────────────────────
    const updateForm = document.getElementById('updateCategoryForm');
    if (updateForm) {
        updateForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const txnId = document.getElementById('editTxnId').value;
            const txnType = document.getElementById('editTxnType').value;
            const categoryId = document.getElementById('categorySelect').value;
            
            try {
                const res = await fetch(`/api/transactions/${txnType}/${txnId}/category`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({category_id: categoryId})
                });
                
                if (res.ok) {
                    bootstrap.Modal.getInstance(document.getElementById('updateCategoryModal')).hide();
                    loadSyncLog();
                } else {
                    const result = await res.json();
                    alert(result.message || 'Failed to update category.');
                }
            } catch (err) {
                console.error('Error updating category:', err);
            }
        });
    }

    // ─── Manual Refresh Button ────────────────────────────────────────────────
    document.getElementById('manualRefreshBtn').addEventListener('click', () => {
        document.getElementById('manualRefreshBtn').textContent = '↻ ...';
        loadSyncLog().finally(() => {
            document.getElementById('manualRefreshBtn').textContent = '↻ Refresh';
        });
    });

    // ─── Init & Auto-refresh every 10s ────────────────────────────────────────
    fetchCategories();
    loadSyncLog();
    setInterval(loadSyncLog, 10000);
});
