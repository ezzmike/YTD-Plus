# app.py
# YT Downloader Plus - Web-based YouTube downloader
# Flask application with yt-dlp integration

from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import os
import threading
import queue
import time
import socket
import re
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Regex to strip ANSI escape codes
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Global state for managing downloads
download_queue = queue.Queue()
download_status = {
    'is_downloading': False,
    'current_url': '',
    'progress': 0,
    'status': 'idle',
    'speed': '',
    'eta': '',
    'title': '',
    'logs': []
}
status_lock = threading.Lock()


def strip_ansi(text):
    """Remove ANSI escape sequences from text"""
    if not isinstance(text, str):
        return text
    return ANSI_ESCAPE.sub('', text)


def add_log(message):
    """Add a message to the download logs"""
    with status_lock:
        timestamp = time.strftime('%H:%M:%S')
        clean_msg = strip_ansi(message)
        download_status['logs'].append(f"[{timestamp}] {clean_msg}")
        # Keep only last 100 log entries
        if len(download_status['logs']) > 100:
            download_status['logs'] = download_status['logs'][-100:]


def progress_hook(d):
    """Callback for yt-dlp progress updates"""
    with status_lock:
        if d['status'] == 'downloading':
            # Extract progress information and strip ANSI
            percent_str = strip_ansi(d.get('_percent_str', '0%')).strip()
            speed_str = strip_ansi(d.get('_speed_str', 'N/A')).strip()
            eta_str = strip_ansi(d.get('_eta_str', 'N/A')).strip()
            
            # Parse percentage efficiently
            try:
                # Remove % and any non-numeric characters except dot
                clean_percent = re.sub(r'[^\d.]', '', percent_str)
                percent = float(clean_percent)
            except:
                percent = download_status['progress']
            
            download_status['progress'] = percent
            download_status['status'] = 'downloading'
            download_status['speed'] = speed_str
            download_status['eta'] = eta_str
            
            # Get title if available
            if 'info_dict' in d:
                download_status['title'] = d['info_dict'].get('title', 'Unknown')
            
        elif d['status'] == 'finished':
            download_status['status'] = 'processing'
            download_status['progress'] = 100
            add_log("Download finished, processing...")
            
        elif d['status'] == 'error':
            download_status['status'] = 'error'
            error_msg = str(d.get('error', 'Unknown error'))
            add_log(f"Error: {error_msg}")


def get_ydl_opts(folder, mode, resolution, subtitles=False, embed_thumbnail=False):
    """Build yt-dlp options based on user settings"""
    
    # Path to local FFmpeg binaries if they exist
    bin_path = os.path.join(os.getcwd(), 'bin')
    ffmpeg_exe = os.path.join(bin_path, 'ffmpeg.exe')
    ffmpeg_path = bin_path if os.path.exists(ffmpeg_exe) or os.path.exists(os.path.join(bin_path, 'ffmpeg')) else None

    if ffmpeg_path:
        add_log(f"Using local FFmpeg from: {bin_path}")
    else:
        # Check if ffmpeg is in system path
        import shutil
        if shutil.which('ffmpeg'):
            pass # add_log("Using system FFmpeg")
        else:
            add_log("⚠️ Warning: FFmpeg not found! Audio extraction and video merging will fail.")

    opts = {
        'outtmpl': {
            'default': os.path.join(folder, '%(title)s [%(id)s].%(ext)s'),
            'playlist': os.path.join(folder, '%(playlist)s', '%(playlist_index)s - %(title)s [%(id)s].%(ext)s'),
        },
        'paths': {'home': folder},
        'progress_hooks': [progress_hook],
        'quiet': False,
        'no_warnings': False,
        'continuedl': True,
        'retries': 10,
        'fragment_retries': 10,
        'ignoreerrors': True, # Skip errors to continue playlist if one fails
        'concurrent_fragment_downloads': 5,
        'nocheckcertificate': True,
        'socket_timeout': 30,
        'geo_bypass': True,
        'updatetime': False,
        # Browser-like headers to avoid 403 Forbidden
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        # YouTube specific tweaks
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'], # Try multiple clients
                'skip': ['dash', 'hls'], # Some DASH/HLS streams fail with 403
            }
        }
    }

    if ffmpeg_path:
        opts['ffmpeg_location'] = ffmpeg_path
    
    # Post-processors list
    pps = []

    if mode == "Audio":
        # Audio-only mode: extract best audio as MP3
        opts.update({
            'format': 'bestaudio/best',
        })
        pps.append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        })
        add_log(f"Mode: Audio extraction (MP3 320kbps)")
    else:
        # Video mode with resolution selection
        if resolution == "Best":
            fmt = 'bestvideo+bestaudio/best'
        else:
            try:
                height = int(resolution.split('p')[0])
                fmt = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/bestvideo+bestaudio/best'
            except:
                fmt = 'bestvideo+bestaudio/best'
        
        opts.update({
            'format': fmt,
            'merge_output_format': 'mp4',
        })

    # Subtitles
    if subtitles:
        opts.update({
            'writesubtitles': True,
            'allsubtitles': False,
            'subtitleslangs': ['en', '.*'],
            'writeautomaticsub': True,
        })
        pps.append({
            'key': 'FFmpegEmbedSubtitle',
        })
        add_log("Feature enabled: Download/Embed Subtitles")

    # Thumbnail
    if embed_thumbnail:
        opts.update({
            'writethumbnail': True,
        })
        pps.append({
            'key': 'EmbedThumbnail',
        })
        pps.append({
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        })
        add_log("Feature enabled: Embed Thumbnail")

    if pps:
        opts['postprocessors'] = pps
    
    return opts


def download_worker():
    """Background worker thread for processing downloads"""
    while True:
        try:
            # Wait for a download task
            task = download_queue.get()
            if task is None:  # Poison pill to stop the worker
                break
            
            url, folder, mode, resolution, subtitles, embed_thumbnail = task
            
            with status_lock:
                download_status['is_downloading'] = True
                download_status['current_url'] = url
                download_status['progress'] = 0
                download_status['status'] = 'starting'
                download_status['speed'] = ''
                download_status['eta'] = ''
                download_status['title'] = ''
            
            add_log(f"Starting download: {url}")
            
            try:
                ydl_opts = get_ydl_opts(folder, mode, resolution, subtitles, embed_thumbnail)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Direct download
                    ydl.download([url])
                
                with status_lock:
                    download_status['status'] = 'completed'
                    download_status['progress'] = 100
                add_log("✓ Download completed successfully!")
                
            except Exception as e:
                with status_lock:
                    download_status['status'] = 'error'
                error_msg = str(e)
                add_log(f"✗ Error: {error_msg}")
            
            finally:
                with status_lock:
                    download_status['is_downloading'] = False
                download_queue.task_done()
                
        except Exception as e:
            add_log(f"Worker error: {str(e)}")


# Start the download worker thread
worker_thread = threading.Thread(target=download_worker, daemon=True)
worker_thread.start()


@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html', 
                          quality_options=Config.QUALITY_OPTIONS,
                          default_quality=Config.DEFAULT_QUALITY,
                          default_mode=Config.DEFAULT_MODE,
                          default_folder=Config.DEFAULT_DOWNLOAD_FOLDER)


@app.route('/api/info', methods=['POST'])
def get_video_info():
    """Fetch video metadata without downloading"""
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'success': False, 'error': 'URL is required'}), 400
        
    try:
        # Minimal options for fast extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': 'in_playlist',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Use 'thumbnail' or first entry in 'thumbnails'
            thumb = info.get('thumbnail')
            if not thumb and info.get('thumbnails'):
                thumb = info['thumbnails'][-1]['url']
                
            return jsonify({
                'success': True,
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': thumb,
                'duration': info.get('duration_string'),
                'is_playlist': 'entries' in info
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/download', methods=['POST'])
def start_download():
    """API endpoint to start a download"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400
    
    url = data.get('url', '').strip()
    mode = data.get('mode', 'Video')
    resolution = data.get('resolution', 'Best')
    folder = data.get('folder', Config.DEFAULT_DOWNLOAD_FOLDER).strip()
    subtitles = data.get('subtitles', False)
    embed_thumbnail = data.get('embed_thumbnail', False)
    
    # Validate inputs
    if not url:
        return jsonify({'success': False, 'error': 'URL is required'}), 400
    
    if not folder:
        folder = Config.DEFAULT_DOWNLOAD_FOLDER
    
    # Create folder if it doesn't exist
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Cannot create folder: {str(e)}'}), 400
    
    # Check if already downloading
    with status_lock:
        if download_status['is_downloading']:
            return jsonify({'success': False, 'error': 'Download already in progress'}), 400
        
        # Reset logs for new download
        download_status['logs'] = []
    
    # Add to download queue
    download_queue.put((url, folder, mode, resolution, subtitles, embed_thumbnail))
    
    return jsonify({'success': True, 'message': 'Download started'})


@app.route('/api/status', methods=['GET'])
def get_status():
    """API endpoint to get current download status"""
    with status_lock:
        return jsonify(download_status.copy())


@app.route('/api/cancel', methods=['POST'])
def cancel_download():
    """API endpoint to cancel current download (limited functionality)"""
    # Note: yt-dlp doesn't support graceful cancellation
    # This will just clear the queue and mark as cancelled
    with status_lock:
        if download_status['is_downloading']:
            download_status['status'] = 'cancelled'
            add_log("Cancel requested (may leave partial files)")
            return jsonify({'success': True, 'message': 'Cancellation requested'})
        else:
            return jsonify({'success': False, 'error': 'No download in progress'}), 400


@app.route('/downloads/<path:filename>')
def serve_download(filename):
    """Serve downloaded files"""
    return send_from_directory(Config.DEFAULT_DOWNLOAD_FOLDER, filename)


def get_local_ip():
    """Get the local IP address for network access"""
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  YT Downloader Plus - Web Edition")
    print("="*60)
    print(f"\n  Local access:   http://localhost:{Config.PORT}")
    print(f"  Network access: http://{get_local_ip()}:{Config.PORT}")
    print(f"\n  Download folder: {Config.DEFAULT_DOWNLOAD_FOLDER}")
    print("\n  Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, threaded=True)
