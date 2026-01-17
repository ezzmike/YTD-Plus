// script.js - YT Downloader Plus
// Frontend JavaScript for handling UI interactions and API calls

// DOM Elements
const downloadForm = document.getElementById('downloadForm');
const downloadBtn = document.getElementById('downloadBtn');
const cancelBtn = document.getElementById('cancelBtn');
const progressCard = document.getElementById('progressCard');
const logsDiv = document.getElementById('logs');
const clearLogsBtn = document.getElementById('clearLogsBtn');
const modeRadios = document.querySelectorAll('input[name="mode"]');
const resolutionGroup = document.getElementById('resolutionGroup');

// Status polling
let statusInterval = null;
let isDownloading = false;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Mode change handler (show/hide resolution for audio mode)
    modeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'Audio') {
                resolutionGroup.style.opacity = '0.5';
                resolutionGroup.querySelector('select').disabled = true;
            } else {
                resolutionGroup.style.opacity = '1';
                resolutionGroup.querySelector('select').disabled = false;
            }
        });
    });

    // Form submission
    downloadForm.addEventListener('submit', handleDownload);

    // Cancel button
    cancelBtn.addEventListener('click', handleCancel);

    // Clear logs button
    clearLogsBtn.addEventListener('click', clearLogs);

    // Start status polling (check every 500ms when downloading)
    startStatusPolling();
});

// Handle download form submission
async function handleDownload(e) {
    e.preventDefault();

    if (isDownloading) {
        addLog('Download already in progress!', 'error');
        return;
    }

    const formData = {
        url: document.getElementById('url').value.trim(),
        mode: document.querySelector('input[name="mode"]:checked').value,
        resolution: document.getElementById('resolution').value,
        folder: document.getElementById('folder').value.trim()
    };

    // Validate URL
    if (!formData.url) {
        addLog('Please enter a YouTube URL!', 'error');
        return;
    }

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (response.ok) {
            addLog(`Download started: ${formData.url}`, 'success');
            isDownloading = true;
            updateUIState(true);
            progressCard.style.display = 'block';
        } else {
            addLog(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        addLog(`Network error: ${error.message}`, 'error');
    }
}

// Handle cancel button
async function handleCancel() {
    if (!isDownloading) {
        return;
    }

    try {
        const response = await fetch('/api/cancel', {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            addLog('Cancellation requested...', 'warning');
        } else {
            addLog(`Cancel error: ${data.error}`, 'error');
        }
    } catch (error) {
        addLog(`Network error: ${error.message}`, 'error');
    }
}

// Update UI state (disable/enable buttons)
function updateUIState(downloading) {
    if (downloading) {
        downloadBtn.disabled = true;
        downloadBtn.textContent = 'Downloading...';
        downloadBtn.style.backgroundColor = '#FFC107';
        cancelBtn.disabled = false;
    } else {
        downloadBtn.disabled = false;
        downloadBtn.textContent = 'Start Download';
        downloadBtn.style.backgroundColor = '';
        cancelBtn.disabled = true;
    }
}

// Poll server for status updates
function startStatusPolling() {
    statusInterval = setInterval(async () => {
        if (!isDownloading) {
            return;
        }

        try {
            const response = await fetch('/api/status');
            const status = await response.json();

            updateStatus(status);
        } catch (error) {
            console.error('Status polling error:', error);
        }
    }, 500);
}

// Update UI with status from server
function updateStatus(status) {
    // Update status text
    const statusElement = document.getElementById('status');
    statusElement.textContent = capitalizeFirst(status.status);
    statusElement.className = 'value ' + status.status;

    // Update progress
    const progress = Math.round(status.progress);
    document.getElementById('progressText').textContent = progress + '%';
    document.getElementById('progressFill').style.width = progress + '%';

    // Update speed and ETA
    document.getElementById('speed').textContent = status.speed || '-';
    document.getElementById('eta').textContent = status.eta || '-';

    // Update title if available
    if (status.title) {
        document.getElementById('currentTitle').style.display = 'block';
        document.getElementById('titleText').textContent = status.title;
    }

    // Update logs
    if (status.logs && status.logs.length > 0) {
        const lastLog = status.logs[status.logs.length - 1];
        const existingLogs = Array.from(logsDiv.children).map(el => el.textContent);
        
        if (!existingLogs.includes(lastLog)) {
            addLog(lastLog);
        }
    }

    // Check if download finished
    if (status.status === 'completed' || status.status === 'error' || status.status === 'cancelled') {
        isDownloading = false;
        updateUIState(false);
        
        if (status.status === 'completed') {
            showNotification('Download completed successfully!', 'success');
        } else if (status.status === 'error') {
            showNotification('Download failed - check logs', 'error');
        }
    }
}

// Add log entry to UI
function addLog(message, type = 'info') {
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    
    // Add timestamp
    const timestamp = new Date().toLocaleTimeString();
    
    // Color code based on type
    let color = '#d4d4d4';
    if (type === 'error') color = '#ff6b6b';
    if (type === 'success') color = '#51cf66';
    if (type === 'warning') color = '#ffd43b';
    
    logEntry.innerHTML = `<span style="color: ${color}">${message}</span>`;
    logsDiv.appendChild(logEntry);
    
    // Auto-scroll to bottom
    logsDiv.scrollTop = logsDiv.scrollHeight;
}

// Clear logs
function clearLogs() {
    logsDiv.innerHTML = '<div class="log-entry">Logs cleared.</div>';
}

// Show notification (simple alert for now)
function showNotification(message, type) {
    // You could replace this with a toast notification library
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// Utility: Capitalize first letter
function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}
