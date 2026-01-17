# setup_dependencies.py
# Automated downloader for FFmpeg binaries (Windows)
# Part of YT Downloader Plus (Portable Edition)

import os
import urllib.request
import zipfile
import shutil

def setup_ffmpeg():
    print("🚀 Starting FFmpeg portable setup...")
    
    bin_dir = os.path.join(os.getcwd(), 'bin')
    temp_zip = os.path.join(os.getcwd(), 'ffmpeg_temp.zip')
    
    if not os.path.exists(bin_dir):
        os.makedirs(bin_dir)
        print(f"Created directory: {bin_dir}")

    # Check if already installed
    if os.path.exists(os.path.join(bin_dir, 'ffmpeg.exe')):
        print("✅ FFmpeg is already present in /bin folder.")
        return

    # Direct link to a stable static build (gyan.dev is standard for Windows)
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    try:
        print(f"📥 Downloading FFmpeg from: {ffmpeg_url}")
        print("This might take a minute (approx 100MB)...")
        
        with urllib.request.urlopen(ffmpeg_url) as response:
            with open(temp_zip, 'wb') as f:
                shutil.copyfileobj(response, f)
        
        print("📦 Extracting binaries...")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            # Find the bin folder inside the zip
            for member in zip_ref.namelist():
                if member.endswith('bin/ffmpeg.exe') or member.endswith('bin/ffprobe.exe'):
                    filename = os.path.basename(member)
                    source = zip_ref.open(member)
                    target = open(os.path.join(bin_dir, filename), "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)
                    print(f"  Extracted: {filename}")

        print("✨ FFmpeg setup complete! Your app is now fully portable.")
        
    except Exception as e:
        print(f"❌ Error during setup: {str(e)}")
        print("\nManual fix: Download FFmpeg from ffmpeg.org and place 'ffmpeg.exe' and 'ffprobe.exe' in the /bin folder.")
    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)

if __name__ == "__main__":
    setup_ffmpeg()
