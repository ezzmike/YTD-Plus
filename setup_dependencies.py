# setup_dependencies.py
# Automated downloader for FFmpeg binaries (Windows)
# Part of YT Downloader Plus (Portable Edition)

import os
import urllib.request
import zipfile
import shutil

NODE_VERSION = "v20.11.1"

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
            # Find ffmpeg.exe and ffprobe.exe anywhere in the zip
            for member in zip_ref.namelist():
                if member.lower().endswith('ffmpeg.exe') or member.lower().endswith('ffprobe.exe'):
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


def setup_nodejs():
    print("🚀 Starting Node.js portable setup...")

    bin_dir = os.path.join(os.getcwd(), 'bin')
    temp_zip = os.path.join(os.getcwd(), 'node_temp.zip')
    node_exe = os.path.join(bin_dir, 'node.exe')

    if not os.path.exists(bin_dir):
        os.makedirs(bin_dir)
        print(f"Created directory: {bin_dir}")

    if os.path.exists(node_exe):
        print("✅ Node.js is already present in /bin folder.")
        return

    node_url = f"https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-win-x64.zip"

    try:
        print(f"📥 Downloading Node.js from: {node_url}")
        print("This might take a minute (approx 30-40MB)...")

        with urllib.request.urlopen(node_url) as response:
            with open(temp_zip, 'wb') as f:
                shutil.copyfileobj(response, f)

        print("📦 Extracting node.exe...")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if member.lower().endswith('node.exe'):
                    source = zip_ref.open(member)
                    target = open(node_exe, "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)
                    print("  Extracted: node.exe")
                    break

        if not os.path.exists(node_exe):
            raise Exception("node.exe not found in the archive")

        print("✨ Node.js setup complete! JS runtime is now available locally.")

    except Exception as e:
        print(f"❌ Error during setup: {str(e)}")
        print("\nManual fix: Install Node.js from nodejs.org or place node.exe in the /bin folder.")
    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)

if __name__ == "__main__":
    setup_ffmpeg()
    setup_nodejs()
