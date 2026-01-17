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
    DEBUG = True  # Set to False in production
    
    # Download settings
    DEFAULT_DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
    MAX_CONCURRENT_DOWNLOADS = 3
    
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
    
    # Ensure download folder exists
    os.makedirs(DEFAULT_DOWNLOAD_FOLDER, exist_ok=True)
