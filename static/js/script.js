// script.js - YT Downloader Plus
// Frontend JavaScript for handling UI interactions and API calls

// DOM Elements (will be initialized after DOM loads)
let downloadForm, downloadBtn, cancelBtn, previewBtn, videoPreview;
let progressCard, logsDiv, clearLogsBtn, modeRadios, resolutionGroup;
let channelOptionsGroup, downloadTypeRadios;

// Status polling
let statusInterval = null;
let statusPollTimer = null;
let statusFetchInFlight = false;
let statusPollDelay = 1000;
let isDownloading = false;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('YT Downloader Plus JS loaded');
    
    // Initialize DOM elements
    downloadForm = document.getElementById('downloadForm');
    downloadBtn = document.getElementById('downloadBtn');
    cancelBtn = document.getElementById('cancelBtn');
    previewBtn = document.getElementById('previewBtn');
    videoPreview = document.getElementById('videoPreview');
    progressCard = document.getElementById('progressCard');
    logsDiv = document.getElementById('logs');
    clearLogsBtn = document.getElementById('clearLogsBtn');
    modeRadios = document.querySelectorAll('input[name="mode"]');
    resolutionGroup = document.getElementById('resolutionGroup');
    channelOptionsGroup = document.getElementById('channelOptionsGroup');
    downloadTypeRadios = document.querySelectorAll('input[name="download_type"]');
    
    console.log('Form element:', downloadForm);
    console.log('Button element:', downloadBtn);
    
    if (!downloadForm) {
        console.error('ERROR: Download form not found!');
        return;
    }
    if (!downloadBtn) {
        console.error('ERROR: Download button not found!');
        return;
    }
    
    console.log('All DOM elements loaded successfully');
    
    // Download type change handler
    downloadTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'channel') {
                channelOptionsGroup.style.display = 'block';
            } else {
                channelOptionsGroup.style.display = 'none';
            }
        });
    });
    
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

    // Also add click listener as backup
    downloadBtn.addEventListener('click', function(e) {
        if (e.target.form) {
            e.target.form.dispatchEvent(new Event('submit'));
        }
    });

    // Cancel button
    cancelBtn.addEventListener('click', handleCancel);

    // Clear logs button
    clearLogsBtn.addEventListener('click', clearLogs);

    // Preview button
    previewBtn.addEventListener('click', fetchVideoInfo);

    // Fetch info on enter in URL field
    document.getElementById('url').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            fetchVideoInfo();
        }
    });

    // Start status polling (adaptive interval)
    startStatusPolling();

    // Pause polling when tab is hidden
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            if (statusPollTimer) {
                clearTimeout(statusPollTimer);
                statusPollTimer = null;
            }
        } else {
            startStatusPolling();
        }
    });
});

// Fetch video info metadata
async function fetchVideoInfo() {
    const url = document.getElementById('url').value.trim();
    if (!url) return;

    previewBtn.disabled = true;
    previewBtn.textContent = '⏳';
    
    try {
        const response = await fetch('/api/info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        const data = await response.json();

        if (data.success) {
            const thumb = data.thumbnail || '';
            if (thumb) {
                document.getElementById('previewThumb').src = thumb;
                videoPreview.style.display = 'flex';
            } else {
                videoPreview.style.display = 'none';
            }
            document.getElementById('previewTitle').textContent = data.title;
            document.getElementById('previewMeta').textContent =
                (data.is_playlist ? 'Playlist' : 'Video') +
                (data.duration ? ` • ${data.duration}` : '');
        } else {
            addLog(`Preview Error: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Info error:', error);
    } finally {
        previewBtn.disabled = false;
        previewBtn.textContent = '🔍';
    }
}

// Handle download form submission
async function handleDownload(e) {
    e.preventDefault();

    // Disable button immediately to prevent double-clicks
    if (downloadBtn.disabled) {
        console.log('Download button already disabled, ignoring click');
        return;
    }
    downloadBtn.disabled = true;

    const downloadType = document.querySelector('input[name="download_type"]:checked').value;
    const formData = {
        url: document.getElementById('url').value.trim(),
        mode: document.querySelector('input[name="mode"]:checked').value,
        resolution: document.getElementById('resolution').value,
        folder: document.getElementById('folder').value.trim(),
        subtitles: document.getElementById('subtitles').checked,
        embed_thumbnail: document.getElementById('embed_thumbnail').checked,
        download_type: downloadType
    };

    // Add channel-specific options if downloading channel
    if (downloadType === 'channel') {
        formData.channel_mode = document.querySelector('input[name="channel_mode"]:checked').value;
        if (formData.channel_mode === 'recent') {
            formData.video_count = parseInt(document.getElementById('video_count').value) || 10;
        }
    }

    // Validate URL
    if (!formData.url) {
        addLog('Please enter a YouTube URL!', 'error');
        downloadBtn.disabled = false; // Re-enable on validation error
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
            downloadBtn.disabled = false; // Re-enable immediately on error
        }
    } catch (error) {
        console.error('Download error:', error);
        addLog(`Network error: ${error.message}`, 'error');
        downloadBtn.disabled = false; // Re-enable on exception
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
function scheduleStatusPoll(delay) {
    if (statusPollTimer) {
        clearTimeout(statusPollTimer);
    }
    statusPollTimer = setTimeout(async () => {
        if (statusFetchInFlight) {
            scheduleStatusPoll(statusPollDelay);
            return;
        }

        statusFetchInFlight = true;
        try {
            const response = await fetch('/api/status', { cache: 'no-store' });
            const status = await response.json();
            updateStatus(status);
            statusPollDelay = 1000;
        } catch (error) {
            console.error('Status polling error:', error);
            statusPollDelay = Math.min(5000, statusPollDelay + 500);
        } finally {
            statusFetchInFlight = false;
            scheduleStatusPoll(statusPollDelay);
        }
    }, delay);
}

function startStatusPolling() {
    statusPollDelay = 1000;
    scheduleStatusPoll(statusPollDelay);
}

// Update UI with status from server
function updateStatus(status) {
    if (status.is_downloading && !isDownloading) {
        isDownloading = true;
        updateUIState(true);
    }

    // Show progress card if downloading
    if (status.is_downloading) {
        progressCard.style.display = 'block';
    }
    
    // Update status text
    const statusElement = document.getElementById('status');
    statusElement.textContent = capitalizeFirst(status.status);
    statusElement.className = 'value ' + status.status;

    // Update current action if available
    if (status.current_action) {
        let actionText = status.current_action;
        if (status.stalled_for && status.stalled_for >= 20) {
            actionText = `No progress for ${status.stalled_for}s. ${status.current_action}`;
        }
        document.getElementById('currentAction').textContent = actionText;
        document.getElementById('currentActionRow').style.display = 'flex';
    } else {
        document.getElementById('currentActionRow').style.display = 'none';
    }

    // Update progress - ensure it's a number and handled correctly
    const progress = Math.min(100, Math.max(0, Math.round(parseFloat(status.progress) || 0)));
    const statusLabel = status.status ? capitalizeFirst(status.status) : 'Status';
    document.getElementById('progressText').textContent = `${progress}% • ${statusLabel}`;
    document.getElementById('progressFill').style.width = progress + '%';

    // Update speed and ETA
    document.getElementById('speed').textContent = status.speed || '-';
    document.getElementById('eta').textContent = status.eta || '-';

    // Update title if available
    if (status.title) {
        document.getElementById('currentTitle').style.display = 'block';
        document.getElementById('titleText').textContent = status.title;
    } else {
        document.getElementById('currentTitle').style.display = 'none';
    }

    // Update logs - add new ones from server
    if (status.logs && status.logs.length > 0) {
        // Get current log entries in UI
        const logElements = logsDiv.querySelectorAll('.log-entry');
        let currentCount = logElements.length;
        const serverCount = status.logs.length;
        
        // If server logs were reset, reset UI logs too
        if (serverCount < currentCount) {
            logsDiv.innerHTML = '';
            currentCount = 0;
        }

        // Add any new logs from the server
        if (serverCount > currentCount) {
            for (let i = currentCount; i < serverCount; i++) {
                addLog(status.logs[i]);
            }
        }
    }

    // Check if download finished
    if (status.status === 'completed' || status.status === 'error' || status.status === 'cancelled') {
        isDownloading = false;
        updateUIState(false);
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
    
    const span = document.createElement('span');
    span.style.color = color;
    span.textContent = message;
    logEntry.appendChild(span);
    logsDiv.appendChild(logEntry);

    // Keep logs at a reasonable length
    const maxLogs = 200;
    while (logsDiv.children.length > maxLogs) {
        logsDiv.removeChild(logsDiv.firstChild);
    }
    
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
