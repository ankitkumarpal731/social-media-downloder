from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from flask_cors import CORS
import yt_dlp
import os
import re
import time
import shutil

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- FFmpeg Auto-Detect (Windows vs Linux Fix) ---
# Pehle system me check karo (Render ke liye)
FFMPEG_PATH = shutil.which("ffmpeg")

# Agar system me nahi mila, to local file check karo (Windows ke liye)
if not FFMPEG_PATH:
    local_ffmpeg = os.path.join(os.getcwd(), 'ffmpeg.exe')
    if os.path.exists(local_ffmpeg):
        FFMPEG_PATH = local_ffmpeg

print(f"\n[SYSTEM CHECK]")
print(f"FFmpeg Path: {FFMPEG_PATH if FFMPEG_PATH else '❌ NOT FOUND'}")
# Cookies check
COOKIES_FILE = os.path.join(os.getcwd(), 'cookies.txt')
print(f"Cookies File: {'✅ FOUND' if os.path.exists(COOKIES_FILE) else '❌ NOT FOUND'}")
print("------------------------------------------------\n")

def clean_filename(title):
    cleaned = title.encode('ascii', 'ignore').decode('ascii')
    cleaned = re.sub(r'[^\w\s-]', '', cleaned).strip()
    return cleaned if cleaned else "media_file"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-info', methods=['POST'])
def get_info():
    url = request.form.get('url')
    if not url: return jsonify({'status': 'error', 'message': 'Please enter a link!'})

    # Cookies Option
    cookie_ops = {}
    if os.path.exists(COOKIES_FILE):
        cookie_ops = {'cookiefile': COOKIES_FILE}

    try:
        ydl_opts = {
            'quiet': True, 
            'no_warnings': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            **cookie_ops
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = info.get('formats', [])
            available_qualities = set()
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('height'):
                    available_qualities.add(f.get('height'))
            
            sorted_qualities = sorted(list(available_qualities), reverse=True)

            return jsonify({
                'status': 'success', 
                'data': {
                    'title': info.get('title', 'Video'),
                    'thumbnail': info.get('thumbnail'),
                    'duration': info.get('duration_string'),
                    'platform': info.get('extractor_key'),
                    'original_url': url,
                    'qualities': sorted_qualities
                }
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Bot Blocked: Cookies Required on Server'})

@app.route('/process-download')
def process_download():
    url = request.args.get('url')
    mode = request.args.get('mode', 'video') 
    quality = request.args.get('quality') 
    
    timestamp = int(time.time())
    
    # Options setup
    common_opts = {
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_PATH, # Auto-detected path
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
    }

    if os.path.exists(COOKIES_FILE):
        common_opts['cookiefile'] = COOKIES_FILE

    if mode == 'audio':
        ydl_opts = {
            **common_opts,
            'format': 'bestaudio/best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/{timestamp}_%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        if quality == 'best':
            format_str = 'bestvideo+bestaudio/best'
        else:
            format_str = f'bestvideo[height={quality}]+bestaudio/best[height={quality}]/best'

        ydl_opts = {
            **common_opts,
            'format': format_str,
            'outtmpl': f'{DOWNLOAD_FOLDER}/{timestamp}_%(title)s.%(ext)s',
            'merge_output_format': 'mp4',
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            base = filename.rsplit('.', 1)[0]
            
            if mode == 'audio':
                final_filename = base + ".mp3"
                dl_name_ext = ".mp3"
            else:
                if os.path.exists(base + '.mp4'): final_filename = base + '.mp4'
                elif os.path.exists(base + '.mkv'): final_filename = base + '.mkv'
                else: final_filename = filename
                dl_name_ext = ".mp4"

        @after_this_request
        def remove_file(response):
            try:
                if os.path.exists(final_filename): os.remove(final_filename)
            except: pass
            return response

        clean_title = clean_filename(info.get('title', 'video'))
        branding_name = f"{clean_title}_By_ErAnkit{dl_name_ext}"
        
        try:
            return send_file(final_filename, as_attachment=True, download_name=branding_name)
        except TypeError:
            return send_file(final_filename, as_attachment=True, attachment_filename=branding_name)

    except Exception as e:
        return f"Download Failed: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
