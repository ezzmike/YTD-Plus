# 🎬 YT Downloader Plus (Web Edition)

✨ **A sleek, powerful, and fun YouTube downloader for your local network!** ✨

YT Downloader Plus turns your machine into a powerful media server, allowing you to download videos, playlists, and high-quality audio from any device on your home network through a beautiful web interface.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![yt-dlp](https://img.shields.io/badge/yt--dlp-Latest-blue?style=for-the-badge&logo=youtube&logoColor=white)

---

## 🚀 Key Features

*   **📺 Playlist Power** — Handles single videos, massive playlists, and entire channels like a pro.
*   **📐 Quality Control** — Pick your perfect resolution: 4K, 1440p, 1080p, 720p, or just "Best".
*   **🎵 Audio extraction** — Convert videos to high-quality 320kbps MP3s with one click.
*   **🌐 Network-Wide Access** — Run it on your PC, access it from your Phone, Tablet, or TV.
*   **⚡ Zero-Config (FFmpeg Included)** — No need to mess with system PATHs. One command sets up everything!
*   **📊 Live Progress** — Watch your downloads happen with real-time speed, ETA, and logs.
*   **🔀 Resumable** — Interrupted? No problem. yt-dlp picks up right where it left off.

---

## 🛠️ Quick Start

### ⚡ Portable Setup (The Easy Way)
We've made it super simple to include all dependencies (including FFmpeg) directly in the folder:

```bash
# 1. Clone the magic
git clone https://github.com/ezzmike/YTD-Plus.git
cd YTD-Plus

# 2. Install Python deps
pip install -r requirements.txt

# 3. Auto-include FFmpeg + Node.js (One-time setup)
python setup_dependencies.py

# 4. Launch the server
python app.py
```

### 3. Open the UI
Grab your browser and head to:

* **Local:** `http://localhost:5000`
* **Network:** `http://YOUR-IP:5000` (The IP will be shown in your terminal on startup!)

---

## 🧪 CLI Usage (Best Quality)

You can use yt-dlp directly with the same settings as the web app:

```bash
# Best quality video+audio merged to MKV
python -m yt_dlp -f "bestvideo*+bestaudio/best" \
  --merge-output-format mkv \
  --progress --newline \
  "https://www.youtube.com/watch?v=..."
```

If you have a local Node.js runtime (installed by `setup_dependencies.py`), you can add:

```bash
--js-runtimes node:bin/node.exe
```

---

## 🐳 Dockerize

A Dockerfile is included at the project root. Build and run:

```bash
docker build -t yt-downloader-plus .
docker run --rm -p 5000:5000 -v "${PWD}/downloads:/app/downloads" yt-downloader-plus
```

---

## ✅ Requirements

* **Python 3.8+**
* **FFmpeg** (automatic portable setup via `setup_dependencies.py`)
* **Node.js** (automatic portable setup via `setup_dependencies.py`, improves YouTube format support)

---

## ⚙️ Configuration

Edit [config.py](config.py) to change defaults:

* `HOST` / `PORT`
* `DEFAULT_DOWNLOAD_FOLDER`
* `DEFAULT_QUALITY`
* `DEFAULT_MODE`
* `MAX_CONCURRENT_DOWNLOADS`
* `USE_NODE_RUNTIME`
* `YOUTUBE_PLAYER_CLIENTS`
* `YOUTUBE_PO_TOKEN_WEB`
* `YOUTUBE_PO_TOKEN_MWEB`
* `YOUTUBE_PO_TOKEN_IOS`
* `COOKIES_FILE`
* `ALLOW_DRM_CLIENTS`
* `SOCKET_TIMEOUT`
* `RETRIES`
* `FRAGMENT_RETRIES`
* `CONCURRENT_FRAGMENT_DOWNLOADS`
* `HTTP_CHUNK_SIZE`

---

## 🧭 Usage Guide

1. Paste a YouTube **video**, **playlist**, or **channel** URL.
2. Pick **Video** or **Audio** mode.
3. Choose max resolution (Video mode) or **MP3** output (Audio mode).
4. Click **Start Download**.

Notes:

* **Playlists** download all items by default.
* **Channels** support *all videos* or *recent N*.
* **Subtitles** are optional (can slow downloads).
* **Thumbnail embedding** adds cover art to files.

---

## 🧪 API (for automation)

All endpoints accept/return JSON.

### POST /api/info

Request:

```json
{ "url": "https://www.youtube.com/watch?v=..." }
```

Response:

```json
{ "success": true, "title": "...", "thumbnail": "...", "duration": "...", "is_playlist": false }
```

### POST /api/download

Request:

```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "mode": "Video",
  "resolution": "Best",
  "folder": "downloads",
  "subtitles": false,
  "embed_thumbnail": true,
  "download_type": "single",
  "channel_mode": "all",
  "video_count": 10
}
```

### GET /api/status

Response:

```json
{
  "status": "downloading",
  "progress": 42,
  "speed": "1.2MiB/s",
  "eta": "00:12",
  "current_action": "Downloading data (42%)"
}
```

### POST /api/cancel

Clears queued items and requests cancellation of the active download.

---

## 🧰 Troubleshooting

* **No audio / merge errors**: Run `python setup_dependencies.py` to install FFmpeg.
* **Missing formats**: Install Node.js so yt-dlp can use the YouTube JS runtime.
* **JS challenge warnings**: Set `USE_NODE_RUNTIME = False` in [config.py](config.py).
* **No JS runtime available**: Use `YOUTUBE_PLAYER_CLIENTS = ['web']` to avoid JS runtime dependency.
* **PO token required**: Set `YOUTUBE_PO_TOKEN_WEB` (or mweb/ios) in [config.py](config.py) following the yt-dlp PO token guide.
* **Age/region restricted**: Export browser cookies to a `cookies.txt` and set `COOKIES_FILE` in [config.py](config.py).
* **Stalling downloads**: Lower `CONCURRENT_FRAGMENT_DOWNLOADS` and `HTTP_CHUNK_SIZE`, and increase `SOCKET_TIMEOUT`.
* **Slow downloads**: Try a lower resolution or disable subtitles.
* **Permission errors**: Choose a writable output folder.

---

## 🎨 Visuals

The app features a modern, mobile-friendly UI with:

* **Dark Mode** terminal logs for that developer feel.
* **Dynamic progress bars** to keep you informed.
* **Foldable logs** to see the technical details or hide them away.

---

## 📂 Project Structure

```text
yt_downloader_plus/
├── app.py             # The brain (Flask Backend)
├── config.py          # The settings (Customizable!)
├── static/            # The beauty (CSS & JS)
├── templates/         # The frame (HTML)
└── downloads/         # The treasure (Your saved files!)
```

---

## 🤝 Contributing

Got a fun idea? Open an issue or submit a pull request! Let's make this the best local downloader together.

## ⚖️ License

Distributed under the MIT License. Use it, tweak it, love it!

---
*Created with ❤️ for the community. Happy downloading!* 🎧🍿
