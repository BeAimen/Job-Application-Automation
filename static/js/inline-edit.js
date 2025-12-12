 INLINE_EDIT_JS = """
// Inline Editing Functionality

document.addEventListener('DOMContentLoaded', function() {
    // Make all elements with class 'editable' inline editable
    document.querySelectorAll('.editable').forEach(element => {
        element.addEventListener('click', function() {
            makeEditable(this);
        });
    });
});

function makeEditable(element) {
    if (element.classList.contains('editing')) return;

    const originalValue = element.textContent;
    const field = element.getAttribute('data-field');
    const id = element.getAttribute('data-id');
    const language = element.getAttribute('data-lang') || 'en';

    // Create input
    const input = document.createElement('input');
    input.type = 'text';
    input.value = originalValue;
    input.className = 'form-input py-1 px-2';
    input.style.width = '100%';

    element.textContent = '';
    element.appendChild(input);
    element.classList.add('editing');
    input.focus();
    input.select();

    // Save on blur or enter
    const save = async () => {
        const newValue = input.value;

        if (newValue !== originalValue) {
            try {
                const response = await fetch(`/api/applications/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        field: field,
                        value: newValue,
                        language: language
                    })
                });

                if (response.ok) {
                    element.textContent = newValue;
                    showToast('Updated successfully', 'success', {
                        action: 'Undo',
                        onAction: () => {
                            element.textContent = originalValue;
                            // TODO: Revert on server
                        }
                    });
                } else {
                    element.textContent = originalValue;
                    showToast('Failed to update', 'error');
                }
            } catch (error) {
                element.textContent = originalValue;
                showToast('Network error', 'error');
            }
        } else {
            element.textContent = originalValue;
        }

        element.classList.remove('editing');
    };

    input.addEventListener('blur', save);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            save();
        } else if (e.key === 'Escape') {
            element.textContent = originalValue;
            element.classList.remove('editing');
        }
    });
}

// Show action menu
function showActions(button) {
    const menu = document.createElement('div');
    menu.className = 'absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-10';
    menu.innerHTML = `
        <a href="#" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
            <i class="fas fa-edit mr-2"></i> Edit
        </a>
        <a href="#" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
            <i class="fas fa-clone mr-2"></i> Duplicate
        </a>
        <a href="#" class="block px-4 py-2 text-sm text-red-600 hover:bg-red-50">
            <i class="fas fa-trash mr-2"></i> Delete
        </a>
    `;

    // Position menu
    const rect = button.getBoundingClientRect();
    menu.style.position = 'fixed';
    menu.style.top = (rect.bottom + 5) + 'px';
    menu.style.right = (window.innerWidth - rect.right) + 'px';

    document.body.appendChild(menu);

    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 0);
}