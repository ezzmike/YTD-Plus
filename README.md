# YT Video DL+ (Web Edition)

A powerful, web-based YouTube downloader with support for playlists, resolution selection, and audio extraction. Accessible from any device on your local network.

## Features

- 🎥 **Playlist Support** — Download single videos, entire playlists, or channels automatically
- 📐 **Resolution Selection** — Choose from 2160p (4K), 1440p, 1080p, 720p, 480p, or "Best"
- 🎵 **Audio-Only Mode** — Extract audio as MP3 (up to 320 kbps)
- 🌐 **Web Interface** — Clean, responsive UI accessible from any device on your network
- 📊 **Real-time Progress** — Live download progress with speed and ETA
- 💾 **Custom Output Folder** — Choose where to save your downloads
- 🔄 **Resume Support** — Automatically resume interrupted downloads

## Requirements

- Python 3.8 or higher
- FFmpeg (for audio extraction and video merging)

### Installing FFmpeg

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd yt_downloader_plus
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the web server:
```bash
python app.py
```

2. Open your browser and navigate to:
   - Local: `http://localhost:5000`
   - Network: `http://YOUR_IP:5000` (shown in console on startup)

3. Enter a YouTube URL (video or playlist)

4. Select your preferences:
   - Download Mode: Video or Audio Only
   - Resolution: Best, 2160p (4K), 1440p, 1080p, 720p, or 480p
   - Output Folder: Where to save downloads

5. Click "Start Download" and monitor progress

## Configuration

Edit `config.py` to customize:
- Default download folder
- Server host and port
- Maximum concurrent downloads
- Default quality settings

## Network Access

To access from other devices on your network:
1. Find your computer's IP address:
   ```bash
   # Windows
   ipconfig
   
   # macOS/Linux
   ifconfig
   ```
2. Use `http://YOUR_IP:5000` on any device connected to your network

## Project Structure

```
yt_downloader_plus/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── .gitignore           # Git ignore rules
├── downloads/           # Default download folder
├── static/
│   ├── css/
│   │   └── style.css    # Stylesheet
│   └── js/
│       └── script.js    # Frontend JavaScript
└── templates/
    └── index.html       # Web interface
```

## Troubleshooting

**"FFmpeg not found" error:**
- Make sure FFmpeg is installed and accessible in your PATH
- Restart your terminal/command prompt after installing FFmpeg

**Cannot access from other devices:**
- Check your firewall settings
- Ensure devices are on the same network
- Try running with: `python app.py --host 0.0.0.0`

**Download fails:**
- Verify the URL is valid
- Check internet connection
- Some videos may be restricted or require authentication

## Security Note

This application is intended for use on trusted local networks only. Do not expose it to the public internet without proper security measures.

## License

MIT License - feel free to modify and distribute

## Credits

Built with:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube downloader
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [FFmpeg](https://ffmpeg.org/) - Media processing
