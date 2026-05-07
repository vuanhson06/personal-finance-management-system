/**
 * auth.js
 * Handles asynchronous form submissions for Login and Sign-up using Fetch API.
 * Uses SweetAlert2 for notifications.
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // Helper function to show alerts
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

    // Helper to toggle button loading state
    const toggleButtonState = (btn, isLoading) => {
        if (!btn) return;
        if (isLoading) {
            btn.disabled = true;
            btn.dataset.originalText = btn.innerHTML;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
        } else {
            btn.disabled = false;
            if (btn.dataset.originalText) {
                btn.innerHTML = btn.dataset.originalText;
            }
        }
    };

    // Login Form Handler
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('loginBtn');
            toggleButtonState(btn, true);

            const formData = new FormData(loginForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    window.location.href = '/dashboard';
                } else {
                    showAlert('error', 'Login Failed', result.message || 'Invalid credentials');
                }
            } catch (error) {
                showAlert('error', 'Network Error', 'Unable to connect to the server. Please try again.');
            } finally {
                toggleButtonState(btn, false);
            }
        });
    }

    // Sign Up Form Handler
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('signupBtn');
            toggleButtonState(btn, true);

            const formData = new FormData(signupForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch('/api/auth/signup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Account Created!',
                        text: 'Redirecting to your dashboard...',
                        showConfirmButton: false,
                        timer: 1500,
                        background: '#E7E5E4',
                        color: '#1E2938',
                        customClass: { popup: 'neu-outset' }
                    }).then(() => {
                        window.location.href = '/dashboard';
                    });
                } else {
                    showAlert('error', 'Registration Failed', result.message || 'Please check your information and try again.');
                }
            } catch (error) {
                showAlert('error', 'Network Error', 'Unable to connect to the server. Please try again.');
            } finally {
                toggleButtonState(btn, false);
            }
        });
    }
});
