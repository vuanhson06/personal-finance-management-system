/**
 * profile.js
 * Handles the global Avatar button and Profile/Security modal logic.
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // --- Profile & Security Logic ---
    window.openProfileModal = async () => {
        try {
            const res = await fetch('/api/auth/me');
            const result = await res.json();
            if (res.ok) {
                const nameEl = document.getElementById('profileName');
                const emailEl = document.getElementById('profileEmail');
                const joinedEl = document.getElementById('profileJoined');
                
                if (nameEl) nameEl.textContent = result.data.username;
                if (emailEl) emailEl.textContent = result.data.email;
                
                if (joinedEl && result.data.joined_at) {
                    const joined = new Date(result.data.joined_at);
                    joinedEl.textContent = joined.toLocaleDateString('en-US', {
                        year: 'numeric', month: 'long', day: 'numeric'
                    });
                }
                
                const modalEl = document.getElementById('profileModal');
                if (modalEl) {
                    const modal = new bootstrap.Modal(modalEl);
                    modal.show();
                }
            }
        } catch (err) {
            console.error('Profile fetch failed:', err);
        }
    };

    const passForm = document.getElementById('changePasswordForm');
    if (passForm) {
        passForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const current = document.getElementById('currPass').value;
            const newP = document.getElementById('newPass').value;
            const confirm = document.getElementById('confirmPass').value;

            if (newP !== confirm) {
                alert('New passwords do not match.');
                return;
            }

            try {
                const res = await fetch('/api/auth/change-password', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({current_password: current, new_password: newP})
                });
                const result = await res.json();
                if (res.ok) {
                    alert('Password updated successfully!');
                    const modalEl = document.getElementById('profileModal');
                    if (modalEl) {
                        const modal = bootstrap.Modal.getInstance(modalEl);
                        if (modal) modal.hide();
                    }
                    passForm.reset();
                } else {
                    alert(result.message || 'Update failed.');
                }
            } catch (err) {
                console.error('Password update error:', err);
            }
        });
    }
});
