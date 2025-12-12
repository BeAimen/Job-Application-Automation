// Drag and Drop File Upload

document.addEventListener('DOMContentLoaded', function() {
    initializeDropZones();
});

function initializeDropZones() {
    const dropZones = document.querySelectorAll('.drop-zone');

    dropZones.forEach(zone => {
        const input = zone.querySelector('input[type="file"]');

        if (!input) return;

        // Click to upload
        zone.addEventListener('click', () => {
            input.click();
        });

        // Drag over
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });

        // Drag leave
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('dragover');
        });

        // Drop
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFiles(files, zone);
            }
        });

        // File input change
        input.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFiles(e.target.files, zone);
            }
        });
    });
}

function handleFiles(files, zone) {
    const file = files[0];

    // Validate file type
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (!allowedTypes.includes(file.type)) {
        showToast('Please upload a PDF or DOCX file', 'error');
        return;
    }

    // Show file info
    const fileInfo = zone.querySelector('.file-info') || createFileInfo(zone);
    fileInfo.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <i class="fas fa-file-pdf text-red-500 text-2xl"></i>
                <div>
                    <p class="text-sm font-medium text-gray-900">${file.name}</p>
                    <p class="text-xs text-gray-500">${formatFileSize(file.size)}</p>
                </div>
            </div>
            <button onclick="removeFile(this)" class="text-gray-400 hover:text-red-600">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="mt-2">
            <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-blue-500 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
            </div>
        </div>
    `;

    // Simulate upload progress
    const progressBar = fileInfo.querySelector('.bg-blue-500');
    let progress = 0;
    const interval = setInterval(() => {
        progress += 10;
        progressBar.style.width = progress + '%';
        if (progress >= 100) {
            clearInterval(interval);
            showToast('File uploaded successfully', 'success');
        }
    }, 200);
}

function createFileInfo(zone) {
    const div = document.createElement('div');
    div.className = 'file-info mt-4 p-4 bg-gray-50 rounded-lg';
    zone.appendChild(div);
    return div;
}

function removeFile(button) {
    const fileInfo = button.closest('.file-info');
    fileInfo.remove();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}