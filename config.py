# config.py
# Configuration settings for YT Downloader Plus

import os

class Config:
    """Application configuration"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Server settings
    HOST = '0.0.0.0'  # Accessible from network; use '127.0.0.1' for localhost only
    PORT = 5000
    DEBUG = False  # Set to False in production
    
    # Download settings
    DEFAULT_DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
    MAX_CONCURRENT_DOWNLOADS = 3
    USE_NODE_RUNTIME = True  # Prefer JS runtime to fix nsig extraction issues

    # Download tuning (stability)
    SOCKET_TIMEOUT = 60
    RETRIES = 20
    FRAGMENT_RETRIES = 20
    CONCURRENT_FRAGMENT_DOWNLOADS = 2
    HTTP_CHUNK_SIZE = 1048576  # 1MB chunks to avoid long stalls
    
    # yt-dlp default options
    DEFAULT_QUALITY = 'Best'
    DEFAULT_MODE = 'Video'
    
    # Available quality options
    QUALITY_OPTIONS = [
        'Best',
        '2160p (4K)',
        '1440p',
        '1080p',
        '720p',
        '480p'
    ]

    # YouTube extractor settings
    YOUTUBE_PLAYER_CLIENTS = ['web', 'mweb', 'android']  # Avoid DRM-prone clients by default
    YOUTUBE_PO_TOKEN_WEB = ''
    YOUTUBE_PO_TOKEN_MWEB = ''
    YOUTUBE_PO_TOKEN_IOS = ''
    COOKIES_FILE = ''  # Optional: path to cookies.txt for YouTube access
    ALLOW_MISSING_PO_FORMATS = True  # Enable formats that may require PO token (can still 403)
    ALLOW_DRM_CLIENTS = False  # Set True to allow 'tv' client (may be DRM restricted)
    
    # Ensure download folder exists
    os.makedirs(DEFAULT_DOWNLOAD_FOLDER, exist_ok=True)
