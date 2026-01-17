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
*   **📊 Live Progress** — Watch your downloads happen with real-time speed, ETA, and logs.
*   **🔀 Resumable** — Interrupted? No problem. yt-dlp picks up right where it left off.

---

## 🛠️ Quick Start

### 1. Prerequisites
Make sure you have [FFmpeg](https://ffmpeg.org/download.html) installed on your system. It's the magic engine that merges videos and extracts audio!

### 2. Setup & Run
```bash
# Clone the magic
git clone https://github.com/ezzmike/YTD-Plus.git
cd YTD-Plus

# Install dependencies
pip install -r requirements.txt

# Launch the server
python app.py
```

### 3. Open the UI
Grab your browser and head to:
- **Local:** `http://localhost:5000`
- **Network:** `http://YOUR-IP:5000` (The IP will be shown in your terminal on startup!)

---

## 🎨 Visuals

The app features a modern, mobile-friendly UI with:
- **Dark Mode** terminal logs for that developer feel.
- **Dynamic progress bars** to keep you informed.
- **Foldable logs** to see the technical details or hide them away.

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
