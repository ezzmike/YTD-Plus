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
import copy
from typing import Any, cast
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Regex to strip ANSI escape codes
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Global state for managing downloads
download_queue = queue.Queue(maxsize=100)  # Unlimited queue with 100 max pending
download_status = {}
active_downloads_urls = set()  # Track URLs currently being downloaded
status_lock = threading.Lock()
worker_threads = []  # List of active worker threads
MAX_CONCURRENT_DOWNLOADS = Config.MAX_CONCURRENT_DOWNLOADS  # Allow up to N simultaneous downloads

DEFAULT_STATUS = {
    'is_downloading': False,
    'active_downloads': 0,
    'current_url': '',
    'progress': 0,
    'status': 'idle',
    'speed': '',
    'eta': '',
    'title': '',
    'current_action': '',
    'last_progress_at': 0,
    'stalled_for': 0,
    'logs': [],
    'output_folder': '',
    'mode': '',
}

def get_download_status():
    """Get status dict for a download, initialized on first use"""
    with status_lock:
        for key, value in DEFAULT_STATUS.items():
            if key not in download_status:
                download_status[key] = [] if key == 'logs' else value
    return download_status


def strip_ansi(text):
    """Remove ANSI escape sequences from text"""
    if not isinstance(text, str):
        return text
    return ANSI_ESCAPE.sub('', text)


class YtdlpLogger:
    def debug(self, msg):
        if msg:
            add_log(str(msg))

    def warning(self, msg):
        if msg:
            add_log(f"⚠️ {msg}")

    def error(self, msg):
        if msg:
            add_log(f"✗ {msg}")


def add_log(message):
    """Add a message to the download logs"""
    with status_lock:
        timestamp = time.strftime('%H:%M:%S')
        clean_msg = strip_ansi(message)
        if 'logs' not in download_status:
            download_status['logs'] = []
        download_status['logs'].append(f"[{timestamp}] {clean_msg}")
        # Keep only last 100 log entries
        if len(download_status['logs']) > 100:
            download_status['logs'] = download_status['logs'][-100:]


def cleanup_intermediate_files(folder, video_title):
    """Remove intermediate files like thumbnails, keeping only the final media file (fast version)"""
    try:
        # Files to remove after download (intermediate files)
        cleanup_exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
        
        # Only walk the immediate download folder, not subfolders (much faster)
        try:
            files = os.listdir(folder)
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in cleanup_exts:
                    full_path = os.path.join(folder, file)
                    try:
                        os.remove(full_path)
                        add_log(f"Cleaned up: {file}")
                    except Exception:
                        pass  # Silent fail on cleanup
        except Exception:
            pass  # Silent fail if folder doesn't exist
    except Exception:
        pass  # Silent fail on cleanup warning


def progress_hook(d):
    """Callback for yt-dlp progress updates"""
    with status_lock:
        if d['status'] == 'downloading':
            # Extract progress information and strip ANSI
            percent_str = strip_ansi(d.get('_percent_str', '0%')).strip()
            speed_str = strip_ansi(d.get('_speed_str', 'N/A')).strip()
            eta_str = strip_ansi(d.get('_eta_str', 'N/A')).strip()
            
            # Parse percentage efficiently, fallback to byte-based calc
            percent = None
            if percent_str and percent_str != '0%':
                try:
                    # Remove % and any non-numeric characters except dot
                    clean_percent = re.sub(r'[^\d.]', '', percent_str)
                    percent = float(clean_percent)
                except Exception:
                    percent = None

            if percent is None:
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded_bytes = d.get('downloaded_bytes')
                if total_bytes and downloaded_bytes is not None:
                    try:
                        percent = (float(downloaded_bytes) / float(total_bytes)) * 100
                        percent_str = f"{percent:.1f}%"
                    except Exception:
                        percent = None

            if percent is None:
                percent = download_status.get('progress', 0)
            
            download_status['progress'] = percent
            download_status['status'] = 'downloading'
            if speed_str in ('', 'N/A'):
                downloaded_bytes = d.get('downloaded_bytes')
                elapsed = d.get('elapsed')
                if downloaded_bytes is not None and elapsed:
                    try:
                        speed = float(downloaded_bytes) / float(elapsed)
                        speed_str = f"{speed/1024/1024:.2f} MiB/s"
                    except Exception:
                        pass
            download_status['speed'] = speed_str
            download_status['eta'] = eta_str
            download_status['last_progress_at'] = time.time()
            download_status['stalled_for'] = 0
            
            # Get title if available
            if 'info_dict' in d:
                download_status['title'] = d['info_dict'].get('title', 'Unknown')
            
            # Show progress stage
            if percent < 5:
                download_status['current_action'] = f'Initializing download ({percent_str})'
            elif percent < 25:
                download_status['current_action'] = f'Downloading stream ({percent_str})'
            elif percent < 75:
                download_status['current_action'] = f'Downloading data ({percent_str})'
            elif percent < 95:
                download_status['current_action'] = f'Completing download ({percent_str})'
            else:
                download_status['current_action'] = f'Finalizing download ({percent_str})'
            
        elif d['status'] == 'finished':
            download_status['status'] = 'processing'
            download_status['progress'] = 98
            download_status['speed'] = ''
            download_status['eta'] = 'Processing...'
            download_status['current_action'] = 'Extracting and processing...'
            download_status['last_progress_at'] = time.time()
            download_status['stalled_for'] = 0
            add_log("Download finished, extracting and processing...")
            
        elif d['status'] == 'postprocessing':
            # Detect what's being post-processed
            pp_info = d.get('postprocessor', 'unknown')
            
            if 'audio' in str(pp_info).lower():
                download_status['current_action'] = 'Extracting audio...'
                add_log("Extracting audio from video...")
            elif 'ffmpeg' in str(pp_info).lower():
                download_status['current_action'] = 'Merging video and audio...'
                add_log("Merging video and audio...")
            elif 'metadata' in str(pp_info).lower():
                download_status['current_action'] = 'Embedding metadata...'
                add_log("Embedding metadata and thumbnails...")
            else:
                download_status['current_action'] = f'Post-processing ({pp_info})...'
                add_log(f"Post-processing: {pp_info}")
            
            download_status['status'] = 'processing'
            download_status['progress'] = 99
            download_status['speed'] = ''
            download_status['eta'] = 'Finalizing...'
            download_status['last_progress_at'] = time.time()
            download_status['stalled_for'] = 0
            
        elif d['status'] == 'error':
            download_status['status'] = 'error'
            error_msg = str(d.get('error', 'Unknown error'))
            add_log(f"Error: {error_msg}")


def build_youtube_extractor_args(allow_fallback_clients=False):
    """Build YouTube extractor args with sensible client filtering."""
    po_tokens = build_po_tokens()
    clients = list(Config.YOUTUBE_PLAYER_CLIENTS)

    if not Config.YOUTUBE_PO_TOKEN_IOS and 'ios' in clients:
        clients.remove('ios')
        add_log("iOS client disabled (missing PO token)")

    if not getattr(Config, 'ALLOW_DRM_CLIENTS', False) and 'tv' in clients:
        clients.remove('tv')
        add_log("TV client disabled (DRM-prone formats)")

    if allow_fallback_clients:
        for client in ['web', 'mweb', 'android']:
            if client not in clients:
                clients.append(client)
        if getattr(Config, 'ALLOW_DRM_CLIENTS', False) and 'tv' not in clients:
            clients.append('tv')
        if Config.YOUTUBE_PO_TOKEN_IOS and 'ios' not in clients:
            clients.append('ios')

    if not clients:
        clients = ['web']

    extractor_args: dict[str, Any] = {
        'player_client': clients,
    }

    if po_tokens:
        extractor_args['po_token'] = po_tokens
    elif getattr(Config, 'ALLOW_MISSING_PO_FORMATS', False):
        extractor_args['formats'] = cast(Any, 'missing_pot')

    return {'youtube': extractor_args}


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

    extractor_args = build_youtube_extractor_args()

    opts = {
        'outtmpl': {
            'default': os.path.join(folder, '%(title)s [%(id)s].%(ext)s'),
            'playlist': os.path.join(folder, '%(playlist)s', '%(playlist_index)s - %(title)s [%(id)s].%(ext)s'),
        },
        'progress_hooks': [progress_hook],
        'logger': YtdlpLogger(),
        'quiet': True,
        'no_warnings': True,
        'continuedl': True,
        'retries': Config.RETRIES,
        'fragment_retries': Config.FRAGMENT_RETRIES,
        'retry_sleep': {
            'http': 2,
            'fragment': 2,
            'extractor': 2,
        },
        'ignoreerrors': False,
        'concurrent_fragment_downloads': Config.CONCURRENT_FRAGMENT_DOWNLOADS,
        'nocheckcertificate': True,
        'socket_timeout': Config.SOCKET_TIMEOUT,
        'geo_bypass': True,
        'updatetime': False,
        'buffer_size': 16384,  # Larger buffer for faster I/O
        'http_chunk_size': Config.HTTP_CHUNK_SIZE,
        # Browser-like headers to avoid 403 Forbidden
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        'extractor_args': extractor_args
    }

    if Config.COOKIES_FILE and os.path.exists(Config.COOKIES_FILE):
        opts['cookiefile'] = Config.COOKIES_FILE
        add_log(f"Using cookies file: {Config.COOKIES_FILE}")

    if ffmpeg_path:
        opts['ffmpeg_location'] = ffmpeg_path

    # Prefer Node.js for YouTube JS runtime when available
    import shutil
    if Config.USE_NODE_RUNTIME:
        node_path = shutil.which('node')
        if not node_path:
            local_node = os.path.join(bin_path, 'node.exe')
            if os.path.exists(local_node):
                node_path = local_node
        if node_path:
            opts['js_runtimes'] = {
                'node': {
                    'path': node_path
                }
            }
        else:
            add_log("⚠️ Warning: Node.js runtime not found. Some YouTube formats may be missing.")

    # Enable remote components for EJS challenge solver (recommended by yt-dlp)
    opts['remote_components'] = ['ejs:github']
    
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
            # Allow any container/stream type to avoid "format not available" when mp4 isn't offered
            fmt = 'bestvideo*+bestaudio/best'
        else:
            try:
                height = int(resolution.split('p')[0])
                fmt = f'bestvideo*[height<={height}]+bestaudio/best[height<={height}]/best'
            except Exception:
                fmt = 'bestvideo*+bestaudio/best'
        
        opts.update({
            'format': fmt,
            'merge_output_format': 'mkv',
            'prefer_ffmpeg': True,
            # Prefer highest quality variants when multiple formats match
            'format_sort': ['res', 'fps', 'hdr', 'vcodec', 'acodec', 'size'],
        })

    # Subtitles - disabled for speed (significantly slows down download)
    # Uncomment to enable:
    # if subtitles:
    #     opts.update({
    #         'writesubtitles': True,
    #         'allsubtitles': False,
    #         'subtitleslangs': ['en', '.*'],
    #         'writeautomaticsub': True,
    #     })
    #     pps.append({
    #         'key': 'FFmpegEmbedSubtitle',
    #     })
    #     add_log("Feature enabled: Download/Embed Subtitles")

    # Thumbnail - fast embedding as cover art (shows in file properties)
    if embed_thumbnail:
        opts.update({
            'writethumbnail': True,  # Download thumbnail JPG
        })
        # Embed as cover art metadata in audio files
        if mode == "Audio":
            pps.append({
                'key': 'FFmpegMetadata',  # Embeds thumbnail as cover art
            })
            add_log("Feature enabled: Thumbnail as album art")
        else:
            # For video, FFmpegMetadata attaches thumbnail as cover art (Windows shows this)
            pps.append({
                'key': 'FFmpegMetadata',  # Fast metadata-only embedding
            })
            add_log("Feature enabled: Thumbnail embedded (shows in file explorer)")

    if pps:
        opts['postprocessors'] = pps
    
    return opts


def build_po_tokens():
    """Build a list of YouTube PO tokens from config."""
    tokens = []
    if Config.YOUTUBE_PO_TOKEN_WEB:
        tokens.append(f"web.gvs+{Config.YOUTUBE_PO_TOKEN_WEB}")
    if Config.YOUTUBE_PO_TOKEN_MWEB:
        tokens.append(f"mweb.gvs+{Config.YOUTUBE_PO_TOKEN_MWEB}")
    if Config.YOUTUBE_PO_TOKEN_IOS:
        tokens.append(f"ios.gvs+{Config.YOUTUBE_PO_TOKEN_IOS}")
    return tokens


def download_worker(worker_id):
    """Background worker thread for processing downloads"""
    print(f"[Worker {worker_id}] Download worker thread is running...")
    while True:
        try:
            # Wait for a download task
            task = download_queue.get(timeout=1)  # Use timeout to keep thread responsive
            if task is None:  # Poison pill to stop the worker
                print(f"[Worker {worker_id}] Stopping worker thread")
                break
            
            print(f"[Worker {worker_id}] Received task: {task[0]}")
            # Unpack task with new parameters, with defaults for backward compatibility
            url = task[0]
            folder = task[1]
            mode = task[2]
            resolution = task[3]
            subtitles = task[4]
            embed_thumbnail = task[5]
            download_type = task[6] if len(task) > 6 else 'single'
            channel_mode = task[7] if len(task) > 7 else 'all'
            video_count = task[8] if len(task) > 8 else 10
            
            with status_lock:
                # Increment active download count and track URL
                active_downloads_urls.add(url)
                download_status['active_downloads'] = download_status.get('active_downloads', 0) + 1
                download_status['is_downloading'] = download_status['active_downloads'] > 0
                download_status['current_url'] = url
                download_status['output_folder'] = folder
                download_status['mode'] = mode
                download_status['progress'] = 0
                download_status['status'] = 'starting'
                download_status['current_action'] = 'Preparing download'
                download_status['speed'] = ''
                download_status['eta'] = ''
                download_status['title'] = ''
                download_status['last_progress_at'] = time.time()
                download_status['stalled_for'] = 0
            
            print(f"[Worker {worker_id}] Starting download: {url}")
            add_log(f"Starting download: {url}")
            add_log(f"Download type: {download_type}")
            if download_type == 'channel':
                add_log(f"Channel mode: {channel_mode}")
                if channel_mode == 'recent':
                    add_log(f"Downloading {video_count} recent videos")
            add_log(f"Output folder: {folder}")
            download_started_at = time.time()
            
            try:
                print(f"[Worker {worker_id}] Getting yt-dlp options...")
                ydl_opts = get_ydl_opts(folder, mode, resolution, subtitles, embed_thumbnail)
                
                # Modify ydl_opts based on download type
                if download_type == 'playlist':
                    add_log("Playlist mode: downloading all videos from playlist")
                elif download_type == 'channel':
                    if channel_mode == 'all':
                        # Download all videos from channel
                        add_log("Channel mode: downloading all videos from channel")
                    elif channel_mode == 'recent':
                        # Download only recent N videos
                        ydl_opts['playlistend'] = video_count
                        add_log(f"Channel mode: downloading {video_count} most recent videos")

                def attempt_download(opts):
                    print(f"[Worker {worker_id}] Starting yt-dlp extraction...")
                    with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
                        return ydl.extract_info(url, download=True)

                try:
                    info = attempt_download(ydl_opts)
                except Exception as e:
                    error_msg = str(e)
                    if 'Requested format is not available' in error_msg or 'Only images are available' in error_msg:
                        add_log("Retrying with alternate YouTube client settings...")
                        alt_opts = copy.deepcopy(ydl_opts)
                        alt_opts['extractor_args'] = build_youtube_extractor_args(
                            allow_fallback_clients=True
                        )

                        # Relax format constraints on retry
                        alt_opts['format'] = 'best'

                        if not Config.USE_NODE_RUNTIME:
                            import shutil
                            node_path = shutil.which('node')
                            if node_path:
                                alt_opts['js_runtimes'] = {
                                    'node': {
                                        'path': node_path
                                    }
                                }

                        info = attempt_download(alt_opts)
                    else:
                        raise

                print(f"[Worker {worker_id}] yt-dlp extraction complete")

                # Update status to show finalization
                with status_lock:
                    download_status['progress'] = 97
                    download_status['current_action'] = 'Verifying downloaded files...'
                    download_status['status'] = 'finalizing'
                
                # Fast verification - just check if files exist in download folder
                video_exts = {'.mp4', '.mkv', '.webm', '.mov', '.flv', '.avi'}
                audio_exts = {'.mp3', '.m4a', '.opus', '.aac', '.wav', '.flac'}
                allowed_exts = audio_exts if mode == "Audio" else video_exts

                print(f"[Worker {worker_id}] Verifying files in {folder}...")
                # Quick check: just verify at least one media file exists
                media_found = False
                try:
                    if not os.path.exists(folder):
                        raise Exception(f"Download folder not found: {folder}")
                    
                    files = os.listdir(folder)
                    print(f"[Worker {worker_id}] Found {len(files)} files in folder")
                    
                    for file in files:
                        ext = os.path.splitext(file)[1].lower()
                        if ext in allowed_exts:
                            media_found = True
                            print(f"[Worker {worker_id}] ✓ Media file found: {file}")
                            add_log(f"✓ Media file found: {file}")
                            break
                except Exception as e:
                    print(f"[Worker {worker_id}] File verification error: {e}")
                    add_log(f"File verification error: {str(e)}")

                if not media_found:
                    raise Exception("Download finished but no media output file was found")

                # Update progress before cleanup
                with status_lock:
                    download_status['progress'] = 98
                    download_status['current_action'] = 'Cleaning up temporary files...'
                
                # Clean up intermediate files (thumbnails, etc)
                print(f"[Worker {worker_id}] Starting cleanup...")
                add_log("Cleaning up intermediate files...")
                cleanup_intermediate_files(folder, download_status.get('title', 'Unknown'))
                print(f"[Worker {worker_id}] Cleanup complete")
                
                # Mark as completed
                with status_lock:
                    download_status['status'] = 'completed'
                    download_status['progress'] = 100
                    download_status['current_action'] = 'Complete!'
                
                print(f"[Worker {worker_id}] ✓ Download completed successfully!")
                add_log("✓ Download completed successfully!")
                
            except Exception as e:
                with status_lock:
                    download_status['status'] = 'error'
                    # Don't reset progress to 0 - keep it at current value
                    download_status['current_action'] = 'Error occurred'
                
                error_msg = str(e)
                print(f"[Worker {worker_id}] ✗ Error: {error_msg}")
                add_log(f"✗ Error: {error_msg}")
                if 'Requested format is not available' in error_msg or 'Only images are available' in error_msg:
                    add_log("Hint: This video may require a YouTube PO token or JS runtime. Try setting PO tokens in config.py or enabling Node.js runtime.")
                
                # Print full traceback to terminal for debugging
                import traceback
                print(f"[Worker {worker_id}] Full traceback:")
                traceback.print_exc()
            
            finally:
                # Decrement active download count and remove URL from active set
                with status_lock:
                    active_downloads_urls.discard(url)  # Remove URL from active set
                    download_status['active_downloads'] = max(0, download_status.get('active_downloads', 1) - 1)
                    download_status['is_downloading'] = download_status['active_downloads'] > 0
                
                print(f"[Worker {worker_id}] Task completed. Active downloads: {download_status.get('active_downloads', 0)}")
                download_queue.task_done()
                
        except queue.Empty:
            # Timeout waiting for task, just continue loop
            continue
        except Exception as e:
            print(f"[Worker {worker_id}] Worker loop error: {str(e)}")
            import traceback
            traceback.print_exc()
            add_log(f"Worker error: {str(e)}")


# Start multiple download worker threads for concurrent downloads
def start_download_workers():
    """Start multiple worker threads"""
    for i in range(MAX_CONCURRENT_DOWNLOADS):
        worker_thread = threading.Thread(target=download_worker, args=(i+1,), daemon=True)
        worker_thread.start()
        worker_threads.append(worker_thread)
        print(f"Started download worker {i+1}/{MAX_CONCURRENT_DOWNLOADS}")

start_download_workers()
print(f"All {len(worker_threads)} download workers started successfully")


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
    data = request.get_json(silent=True) or {}
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
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(url, download=False)
            
            # Use 'thumbnail' or first entry in 'thumbnails'
            thumb = info.get('thumbnail')
            thumbs = info.get('thumbnails') or []
            if not thumb and isinstance(thumbs, list) and len(thumbs) > 0:
                last_thumb = cast(Any, thumbs[-1])
                thumb = last_thumb.get('url')
                
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
    data = request.get_json(silent=True) or {}
    
    if not data:
        return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400
    
    url = data.get('url', '').strip()
    mode = data.get('mode', Config.DEFAULT_MODE)
    if mode not in ('Video', 'Audio'):
        mode = Config.DEFAULT_MODE
    resolution = data.get('resolution', Config.DEFAULT_QUALITY)
    if resolution not in Config.QUALITY_OPTIONS:
        resolution = Config.DEFAULT_QUALITY
    folder = data.get('folder', Config.DEFAULT_DOWNLOAD_FOLDER).strip()
    subtitles = data.get('subtitles', False)
    embed_thumbnail = data.get('embed_thumbnail', False)
    download_type = data.get('download_type', 'single')
    if download_type not in ('single', 'playlist', 'channel'):
        download_type = 'single'
    channel_mode = data.get('channel_mode', 'all')
    if channel_mode not in ('all', 'recent'):
        channel_mode = 'all'
    try:
        video_count = int(data.get('video_count', 10))
    except Exception:
        video_count = 10
    video_count = max(1, min(100, video_count))
    
    # Validate inputs
    if not url:
        return jsonify({'success': False, 'error': 'URL is required'}), 400
    
    if not folder:
        folder = Config.DEFAULT_DOWNLOAD_FOLDER

    # Normalize folder to absolute path to avoid nested downloads
    if not os.path.isabs(folder):
        folder = os.path.abspath(folder)
    
    # Create folder if it doesn't exist
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Cannot create folder: {str(e)}'}), 400
    
    # Ensure status defaults exist
    get_download_status()

    # Check if this URL is already being downloaded
    with status_lock:
        if url in active_downloads_urls:
            return jsonify({'success': False, 'error': 'This URL is already being downloaded'}), 409
        
        # Reset logs for new download (allow unlimited concurrent downloads)
        download_status['logs'] = []
        download_status['status'] = 'queued'
        download_status['current_action'] = 'Queued for download'
        download_status['progress'] = 0
        # Don't set is_downloading here - worker will handle it
    
    # Add to download queue
    try:
        download_queue.put((url, folder, mode, resolution, subtitles, embed_thumbnail, download_type, channel_mode, video_count), timeout=5)
    except queue.Full:
        return jsonify({'success': False, 'error': 'Download queue is full - try again later'}), 503
    
    return jsonify({'success': True, 'message': 'Download queued and processing...'})


@app.route('/api/status', methods=['GET'])
def get_status():
    """API endpoint to get current download status"""
    get_download_status()
    with status_lock:
        if download_status.get('is_downloading'):
            last_progress_at = download_status.get('last_progress_at') or 0
            if last_progress_at:
                download_status['stalled_for'] = max(0, int(time.time() - last_progress_at))
            else:
                download_status['stalled_for'] = 0
        else:
            download_status['stalled_for'] = 0
        if download_status.get('status') == 'downloading' and download_status.get('stalled_for', 0) >= 20:
            current_action = download_status.get('current_action') or 'Downloading...'
            download_status['current_action'] = f"No progress for {download_status['stalled_for']}s. {current_action}"

        # Recovery: if download appears stuck near completion, finalize when media exists
        if (
            download_status.get('status') in ('downloading', 'processing', 'finalizing')
            and download_status.get('active_downloads', 0) == 0
            and (download_status.get('progress') or 0) >= 95
        ):
            folder = download_status.get('output_folder') or ''
            media_found = False
            if folder and os.path.isdir(folder):
                video_exts = {'.mp4', '.mkv', '.webm', '.mov', '.flv', '.avi'}
                audio_exts = {'.mp3', '.m4a', '.opus', '.aac', '.wav', '.flac'}
                allowed_exts = audio_exts if download_status.get('mode') == 'Audio' else video_exts
                try:
                    for file in os.listdir(folder):
                        ext = os.path.splitext(file)[1].lower()
                        if ext in allowed_exts:
                            media_found = True
                            break
                except Exception:
                    media_found = False
            if media_found:
                download_status['status'] = 'completed'
                download_status['progress'] = 100
                download_status['current_action'] = 'Complete!'
        return jsonify(download_status.copy())


@app.route('/api/cancel', methods=['POST'])
def cancel_download():
    """API endpoint to cancel current download (limited functionality)"""
    # Note: yt-dlp doesn't support graceful cancellation
    # This will just clear the queue and mark as cancelled
    get_download_status()
    cleared = 0
    try:
        while True:
            item = download_queue.get_nowait()
            if item is not None:
                cleared += 1
            download_queue.task_done()
    except queue.Empty:
        pass

    with status_lock:
        if download_status.get('is_downloading') or cleared > 0:
            download_status['status'] = 'cancelled'
            add_log("Cancel requested (may leave partial files)")
            if cleared > 0:
                add_log(f"Cleared {cleared} queued download(s)")
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
