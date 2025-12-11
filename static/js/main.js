// Job Application Automation - Main JavaScript

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Job Application Automation System Loaded');

    // Add smooth scrolling to all links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // Setup website URL auto-formatting
    const websiteInput = document.querySelector('input[name="website"]');
    if (websiteInput) {
        websiteInput.addEventListener('blur', function() {
            formatWebsiteUrl(this);
        });
    }
});

// Auto-format website URL
function formatWebsiteUrl(input) {
    let url = input.value.trim();

    if (!url) return;

    try {
        // Add https:// if no protocol
        if (!url.match(/^https?:\/\//i)) {
            url = 'https://' + url;
        }

        // Parse URL
        const urlObj = new URL(url);
        const hostname = urlObj.hostname.toLowerCase();

        // Add www. if missing (but only if it's not an IP, localhost, or already has subdomain)
        if (!hostname.startsWith('www.') &&
            !hostname.match(/^\\d+\\.\\d+\\.\\d+\\.\\d+$/) &&
            hostname !== 'localhost' &&
            !hostname.includes('localhost:') &&
            hostname.split('.').length === 2) { // Only domain.tld (no subdomain)
            urlObj.hostname = 'www.' + hostname;
        }

        input.value = urlObj.toString();
    } catch (e) {
        // Invalid URL, leave as is
        console.log('Invalid URL format:', url);
    }
}

// Utility Functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
        type === 'success' ? 'bg-green-500' :
        type === 'error' ? 'bg-red-500' :
        type === 'warning' ? 'bg-yellow-500' :
        'bg-blue-500'
    } text-white`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Form validation helper
function validateEmail(email) {
    const re = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
    return re.test(email);
}

function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('border-red-500');
            isValid = false;
        } else {
            field.classList.remove('border-red-500');
        }
    });

    return isValid;
}

// Confirmation dialog
function confirmAction(message) {
    return new Promise((resolve) => {
        const result = confirm(message);
        resolve(result);
    });
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy', 'error');
    });
}

// Export table to CSV
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const rows = table.querySelectorAll('tr');
    const csv = [];

    rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const rowData = Array.from(cols).map(col => {
            let data = col.textContent.trim();
            // Escape quotes
            data = data.replace(/"/g, '""');
            return `"${data}"`;
        });
        csv.push(rowData.join(','));
    });

    const csvContent = csv.join('\\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'export.csv';
    a.click();
    window.URL.revokeObjectURL(url);
}

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Search/filter functionality
function filterTable(searchInput, tableId) {
    const filter = searchInput.value.toLowerCase();
    const table = document.getElementById(tableId);
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr');

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    });
}

// Close modal on outside click
document.addEventListener('click', function(event) {
    const modals = document.querySelectorAll('.modal:not(.hidden)');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.classList.add('hidden');
        }
    });
});

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Escape key closes modals
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal:not(.hidden)');
        modals.forEach(modal => modal.classList.add('hidden'));
    }

    // Ctrl/Cmd + K for search (if search exists)
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        const searchInput = document.querySelector('input[type="search"]');
        if (searchInput) searchInput.focus();
    }
});

console.log('Main.js loaded successfully');
