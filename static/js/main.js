// JobFlow - Enhanced Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('JobFlow SaaS Loaded');
    initializeToastContainer();
    initializeSkeletons();
});

// Toast Notification System
function showToast(message, type = 'info', options = {}) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icon = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    }[type];

    toast.innerHTML = `
        <div class="flex-shrink-0">
            <i class="fas fa-${icon} text-xl text-${type === 'success' ? 'green' : type === 'error' ? 'red' : type === 'warning' ? 'yellow' : 'blue'}-600"></i>
        </div>
        <div class="flex-1">
            <p class="text-sm font-medium text-gray-900">${message}</p>
        </div>
        ${options.action ? `
            <button onclick="handleToastAction(this)" class="text-sm font-medium text-blue-600 hover:text-blue-700">
                ${options.action}
            </button>
        ` : ''}
        <button onclick="closeToast(this)" class="flex-shrink-0 text-gray-400 hover:text-gray-600">
            <i class="fas fa-times"></i>
        </button>
    `;

    if (options.onAction) {
        toast.dataset.onAction = options.onAction;
    }

    container.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function closeToast(button) {
    const toast = button.closest('.toast');
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
}

function handleToastAction(button) {
    const toast = button.closest('.toast');
    const onAction = toast.dataset.onAction;
    if (onAction) {
        eval(onAction)();
    }
    closeToast(button);
}

function initializeToastContainer() {
    if (!document.getElementById('toast-container')) {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(container);
    }
}

// Loading Skeletons
function showSkeleton(targetId) {
    const target = document.getElementById(targetId);
    if (!target) return;

    const skeleton = document.createElement('div');
    skeleton.className = 'skeleton-card';
    skeleton.innerHTML = `
        <div class="skeleton-line mb-4" style="width: 60%"></div>
        <div class="skeleton-line mb-3" style="width: 100%"></div>
        <div class="skeleton-line mb-3" style="width: 90%"></div>
        <div class="skeleton-line" style="width: 80%"></div>
    `;

    target.innerHTML = '';
    target.appendChild(skeleton);
}

function hideSkeleton(targetId) {
    const target = document.getElementById(targetId);
    if (!target) return;
    target.innerHTML = '';
}

function initializeSkeletons() {
    // Show skeletons for slow-loading sections
    const sections = document.querySelectorAll('[data-skeleton]');
    sections.forEach(section => {
        if (!section.hasChildNodes()) {
            showSkeleton(section.id);
        }
    });
}

// Utility Functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function validateEmail(email) {
    const re = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
    return re.test(email);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}

// Export functions
function exportToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const rows = Array.from(table.querySelectorAll('tr'));
    const csv = rows.map(row => {
        const cells = Array.from(row.querySelectorAll('td, th'));
        return cells.map(cell => {
            let text = cell.textContent.trim();
            text = text.replace(/"/g, '""');
            return `"${text}"`;
        }).join(',');
    }).join('\\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'export.csv';
    a.click();
    URL.revokeObjectURL(url);
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Escape closes modals
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal:not(.hidden)').forEach(modal => {
            modal.classList.add('hidden');
        });
    }

    // Ctrl/Cmd + K for quick actions
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        // TODO: Show command palette
    }
});

// Auto-format website URLs
function formatWebsiteUrl(input) {
    let url = input.value.trim();
    if (!url) return;

    try {
        if (!url.match(/^https?:\\/\\//i)) {
            url = 'https://' + url;
        }

        const urlObj = new URL(url);
        const hostname = urlObj.hostname.toLowerCase();

        if (!hostname.startsWith('www.') &&
            !hostname.match(/^\\d+\\.\\d+\\.\\d+\\.\\d+$/) &&
            hostname !== 'localhost' &&
            hostname.split('.').length === 2) {
            urlObj.hostname = 'www.' + hostname;
        }

        input.value = urlObj.toString();
    } catch (e) {
        console.log('Invalid URL format');
    }
}

console.log('✨ JobFlow SaaS UI Loaded Successfully');