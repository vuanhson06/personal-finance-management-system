/**
 * goals.js
 * Handles Saving Goals CRUD and integration with Strict Balance Guard.
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // Globals
    let accountsCache = [];

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
            customClass: { popup: 'neu-outset', confirmButton: 'neu-btn-primary' }
        });
    };

    // Strict Balance Guard handler
    const handleApiResponse = async (response) => {
        const result = await response.json();
        if (response.ok) {
            return result;
        } else if (response.status === 422) {
            Swal.fire({
                icon: 'error',
                title: 'Insufficient Funds!',
                text: result.message || 'This contribution would overdraw your account.',
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

    // Load Accounts for dropdown
    const loadAccounts = async () => {
        try {
            const res = await fetch('/api/accounts');
            if(!res.ok) return;
            const result = await res.json();
            accountsCache = result.data;
            
            const html = accountsCache.map(acc => `<option value="${acc.id}">${acc.name} (${formatCurrency(acc.balance)})</option>`).join('');
            document.getElementById('accountSelect').innerHTML = html || '<option value="">No Accounts</option>';
        } catch (e) {
            console.error('Error loading accounts', e);
        }
    };

    // Load Goals
    const loadGoals = async () => {
        try {
            const res = await fetch('/api/goals');
            if(!res.ok) return;
            const result = await res.json();
            
            const html = result.data.map(goal => {
                const target = parseFloat(goal.target);
                const current = parseFloat(goal.current);
                let percent = (current / target) * 100;
                if (percent > 100) percent = 100;
                
                const isCompleted = goal.status === 'Completed' || percent === 100;
                const barColor = isCompleted ? 'var(--neu-success)' : 'var(--neu-primary)';

                return `
                <div class="col-md-6">
                    <div class="neu-outset goal-card">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <div>
                                <h4 class="mb-0 fw-bold d-inline-block" style="color: var(--neu-primary);">${goal.name}</h4>
                                <button class="neu-btn btn-sm text-danger ms-2" style="width: 32px; height: 32px; padding: 0; display: inline-flex; align-items: center; justify-content: center;" title="Delete Goal" onclick="deleteGoal(${goal.id}, ${current})"><i data-lucide="trash-2" style="width: 14px; height: 14px;"></i></button>
                            </div>
                            <span class="badge rounded-pill bg-${isCompleted ? 'success' : 'primary'}">${goal.status}</span>
                        </div>
                        <p class="text-muted mb-1">Target: <strong>${formatCurrency(target)}</strong></p>
                        
                        <div class="progress">
                            <div class="progress-bar" role="progressbar" style="width: ${percent}%; background-color: ${barColor};" aria-valuenow="${percent}" aria-valuemin="0" aria-valuemax="100"></div>
                        </div>
                        
                        <div class="d-flex justify-content-between align-items-center mt-3">
                            <div class="display-font fs-5 fw-bold">${formatCurrency(current)}</div>
                            <div>
                                <button class="neu-btn btn-sm me-2" onclick="openActionModal(${goal.id}, 'Withdraw', '${goal.name}')" ${current === 0 ? 'disabled' : ''}>Withdraw</button>
                                <button class="neu-btn-primary btn-sm" onclick="openActionModal(${goal.id}, 'Contribute', '${goal.name}')" ${isCompleted ? 'disabled' : ''}>Contribute</button>
                            </div>
                        </div>
                    </div>
                </div>
                `;
            }).join('');
            
            document.getElementById('goalsContainer').innerHTML = html || '<div class="col-12 text-center text-muted">No saving goals found. Create one!</div>';
            lucide.createIcons();
        } catch (e) {
            console.error('Error loading goals', e);
        }
    };

    // Open Action Modal (Contribute/Withdraw)
    window.openActionModal = (goalId, actionType, goalName) => {
        document.getElementById('actionGoalId').value = goalId;
        document.getElementById('actionType').value = actionType;
        document.getElementById('actionModalTitle').textContent = `${actionType} - ${goalName}`;
        document.getElementById('actionAmount').value = '';
        
        const btn = document.getElementById('actionSubmitBtn');
        btn.textContent = `Confirm ${actionType}`;
        btn.style.backgroundColor = actionType === 'Withdraw' ? 'var(--neu-danger)' : 'var(--neu-primary)';
        
        const modal = new bootstrap.Modal(document.getElementById('actionGoalModal'));
        modal.show();
    };

    // Handle Create Goal
    document.getElementById('createGoalForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        
        try {
            const res = await fetch('/api/goals', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            await handleApiResponse(res);
            
            // Close modal via Bootstrap
            const modalEl = document.getElementById('createGoalModal');
            bootstrap.Modal.getInstance(modalEl).hide();
            
            showAlert('success', 'Success', 'Goal created successfully.');
            e.target.reset();
            loadGoals();
        } catch (err) {}
    });

    // Handle Action (Contribute/Withdraw)
    document.getElementById('actionGoalForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        const actionType = data.action_type;
        const endpoint = `/api/goals/${data.goal_id}/${actionType.toLowerCase()}`;
        
        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    account_id: data.account_id,
                    amount: data.amount
                })
            });
            await handleApiResponse(res);
            
            // Close modal
            const modalEl = document.getElementById('actionGoalModal');
            bootstrap.Modal.getInstance(modalEl).hide();
            
            showAlert('success', 'Success', `${actionType} processed successfully.`);
            
            // Refresh
            loadGoals();
            loadAccounts(); // Balances changed!
        } catch (err) {}
    });

    // Handle Delete Goal
    window.deleteGoal = async (goalId, currentBalance) => {
        if (currentBalance > 0) {
            Swal.fire({
                icon: 'warning',
                title: 'Action Required',
                text: `You must withdraw the remaining ${formatCurrency(currentBalance)} back to your bank account before deleting this goal.`,
                confirmButtonColor: '#006666',
                background: '#E7E5E4',
                color: '#1E2938',
                customClass: { popup: 'neu-outset', confirmButton: 'neu-btn-primary' }
            });
            return;
        }

        const result = await Swal.fire({
            icon: 'question',
            title: 'Delete Goal?',
            text: 'Are you sure you want to delete this goal?',
            showCancelButton: true,
            confirmButtonText: 'Yes, delete it!',
            confirmButtonColor: '#FF2157',
            background: '#E7E5E4',
            color: '#1E2938',
            customClass: { popup: 'neu-outset', confirmButton: 'neu-btn-primary' }
        });

        if (result.isConfirmed) {
            try {
                const res = await fetch(`/api/goals/${goalId}`, { method: 'DELETE' });
                await handleApiResponse(res);
                showAlert('success', 'Deleted!', 'The goal has been deleted.');
                loadGoals();
            } catch (err) {}
        }
    };

    // Init
    loadAccounts();
    loadGoals();
});
