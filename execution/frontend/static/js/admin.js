/**
 * admin.js
 * Handles the logic for the Nexus Finance Admin Panel.
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // Formatter for currency
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    };

    // Chart.js Dark Mode Defaults
    if (window.Chart) {
        Chart.defaults.color = '#D1D5DB';
        Chart.defaults.font.family = "'Inter', sans-serif";
    }

    // --- 1. Fetch System Health & Metrics ---
    const fetchSystemHealth = async () => {
        try {
            const res = await fetch('/api/admin/system-health');
            const result = await res.json();
            if (res.ok) {
                const { metrics } = result.data;
                document.getElementById('stat-total-users').textContent = metrics.total_users;
            }
        } catch (err) {
            console.error('Error fetching system health:', err);
        }
    };

    // --- 2. Fetch Global Analytics & Initialize Charts ---
    const fetchAnalytics = async () => {
        try {
            const res = await fetch('/api/admin/analytics/global');
            const result = await res.json();
            if (res.ok) {
                renderHeatmap(result.data.heatmap);
                renderDistribution(result.data.distribution);
            }
        } catch (err) {
            console.error('Error fetching analytics:', err);
        }
    };

    const renderHeatmap = (data) => {
        const grid = document.getElementById('activity-heatmap-grid');
        if (!grid) return;
        grid.innerHTML = '';
        
        // MySQL DAYOFWEEK (1=Sun, 2=Mon... 7=Sat) -> Matrix Mon-Sun (0=Mon, 6=Sun)
        const dayMap = { 2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 1: 6 };
        const matrix = Array.from({ length: 7 }, () => Array(24).fill(0));
        
        let maxCount = 0;
        data.forEach(p => {
            const row = dayMap[p.day];
            if (row !== undefined) {
                matrix[row][p.hour] = p.count;
                if (p.count > maxCount) maxCount = p.count;
            }
        });

        // Render 7 rows x 24 hours
        for (let d = 0; d < 7; d++) {
            for (let h = 0; h < 24; h++) {
                const count = matrix[d][h];
                const cell = document.createElement('div');
                cell.className = 'heatmap-cell';
                
                if (count > 0) {
                    const intensity = maxCount > 0 ? (count / maxCount) : 0;
                    cell.style.backgroundColor = 'var(--neu-primary)';
                    cell.style.opacity = 0.15 + (intensity * 0.85);
                    
                    const dayName = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d];
                    cell.title = `${dayName} at ${h}:00 - ${count} transactions`;
                } else {
                    cell.title = 'Quiet period';
                }
                grid.appendChild(cell);
            }
        }
    };

    let distChartInstance = null;
    const renderDistribution = (data) => {
        const ctx = document.getElementById('distributionChart').getContext('2d');
        if (distChartInstance) distChartInstance.destroy();
        
        const labels = data.map(d => d.category);
        const values = data.map(d => parseFloat(d.amount));

        distChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        '#006666', '#00A63D', '#FF2157', '#f39c12', '#3498db', '#9b59b6'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } }
                },
                cutout: '70%'
            }
        });
    };

    // --- 3. User Management Ledger ---
    const fetchUsers = async () => {
        try {
            const res = await fetch('/api/admin/users');
            const result = await res.json();
            if (res.ok) {
                const users = result.data;
                document.getElementById('stat-total-users').textContent = users.length;
                renderUserTable(users);
            }
        } catch (err) {
            console.error('Error fetching users:', err);
        }
    };

    const renderUserTable = (users) => {
        const container = document.getElementById('userTableBody');
        container.innerHTML = users.map(u => `
            <tr class="user-row border-bottom" style="border-color: rgba(255,255,255,0.05) !important;">
                <td class="text-muted small">#${u.id}</td>
                <td>
                    <div class="fw-bold">${u.username}</div>
                    <div class="text-muted small">${u.email}</div>
                </td>
                <td><span class="badge ${u.role === 'Admin' ? 'bg-danger' : 'bg-secondary'}">${u.role}</span></td>
                <td>
                    <span class="status-badge ${u.is_active ? 'status-active' : 'status-locked'} d-inline-flex align-items-center">
                        <i data-lucide="${u.is_active ? 'check-circle' : 'lock'}" class="me-1" style="width: 12px; height: 12px;"></i>
                        ${u.is_active ? 'Active' : 'Locked'}
                    </span>
                </td>
                <td class="text-muted small">${new Date(u.created_at).toLocaleDateString()}</td>
                <td class="text-end">
                    <button class="neu-btn btn-sm py-1 px-3 d-inline-flex align-items-center gap-2" onclick="toggleUserStatus(${u.id}, ${u.is_active})">
                        <i data-lucide="${u.is_active ? 'lock' : 'unlock'}" style="width: 14px; height: 14px;"></i>
                        <span>${u.is_active ? 'Lock' : 'Unlock'}</span>
                    </button>
                </td>
            </tr>
        `).join('');
        if (window.lucide) lucide.createIcons();
    };

    window.toggleUserStatus = async (userId, currentStatus) => {
        const action = currentStatus ? 'lock' : 'unlock';
        const result = await Swal.fire({
            title: 'Are you sure?',
            text: `Do you want to ${action} this user account?`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#006666',
            confirmButtonText: `Yes, ${action} it!`
        });

        if (result.isConfirmed) {
            try {
                const res = await fetch(`/api/admin/users/${userId}/toggle-status`, { method: 'PUT' });
                if (res.ok) {
                    Swal.fire('Success', `User has been ${action}ed.`, 'success');
                    fetchUsers(); // Refresh list
                    fetchAuditLogs(); // Refresh logs
                }
            } catch (err) {
                console.error('Error toggling user status:', err);
            }
        }
    };

    // --- 4. Audit Trail ---
    const fetchAuditLogs = async () => {
        try {
            const res = await fetch('/api/admin/logs');
            const result = await res.json();
            if (res.ok) {
                const container = document.getElementById('auditTableBody');
                container.innerHTML = result.data.map(l => `
                    <tr>
                        <td class="text-muted">${new Date(l.timestamp).toLocaleString()}</td>
                        <td class="fw-bold">Admin #${l.admin_id}</td>
                        <td>${l.action}</td>
                        <td class="text-muted">${l.target_id ? 'User #' + l.target_id : '--'}</td>
                    </tr>
                `).join('');
            }
        } catch (err) {
            console.error('Error fetching audit logs:', err);
        }
    };

    // Search functionality
    document.getElementById('userSearch').addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const rows = document.querySelectorAll('.user-row');
        rows.forEach(row => {
            const text = row.innerText.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    });

    // --- Refresh Logic ---
    window.refreshAdminData = () => {
        fetchSystemHealth();
        fetchAnalytics();
        fetchUsers();
        fetchAuditLogs();
        document.getElementById('lastSyncTime').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
    };

    // --- Initial Load ---
    refreshAdminData();
});
