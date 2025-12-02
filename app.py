from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from flask_cors import CORS
import yt_dlp
import os
import re
import time
import shutil

app = Flask(__name__)
CORS(app)

# Downloads folder
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# --- SABSE IMPORTANT SETUP ---
# Hum zabardasti current folder me ffmpeg dhundenge
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_PATH = os.path.join(BASE_DIR, 'ffmpeg.exe')

print("------------------------------------------------")
if os.path.exists(FFMPEG_PATH):
    print(f"✅ SUCCESS: FFmpeg mil gaya yahan: {FFMPEG_PATH}")
    print("   Ab High Quality Merge kaam karega!")
else:
    print(f"❌ ERROR: FFmpeg nahi mila yahan: {FFMPEG_PATH}")
    print("   Please 'ffmpeg.exe' ko isi folder me paste karein!")
print("------------------------------------------------")

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

    try:
        ydl_opts = {
            'quiet': True, 
            'no_warnings': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Formats Scan
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
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/process-download')
def process_download():
    url = request.args.get('url')
    mode = request.args.get('mode', 'video') 
    quality = request.args.get('quality') 
    
    timestamp = int(time.time())
    
    # Check FFmpeg again before download
    if not os.path.exists(FFMPEG_PATH) and mode != 'audio':
        return "<h1>Error: ffmpeg.exe missing!</h1><p>Folder check karein. Bina FFmpeg ke High Quality merge nahi hoga.</p>", 500

    common_opts = {
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_PATH, # Zabardasti Path
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}
    }

    if mode == 'audio':
        ydl_opts = {
            **common_opts,
            'format': 'bestaudio/best',
            'outtmpl': f'downloads/{timestamp}_%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        # VIDEO LOGIC
        if quality == 'best':
            format_str = 'bestvideo+bestaudio/best'
        else:
            format_str = f'bestvideo[height={quality}]+bestaudio/best[height={quality}]/best'

        ydl_opts = {
            **common_opts,
            'format': format_str,
            'outtmpl': f'downloads/{timestamp}_%(title)s.%(ext)s',
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
        
        # FIX FOR FLASK VERSION ERROR
        try:
            return send_file(final_filename, as_attachment=True, download_name=branding_name)
        except TypeError:
            return send_file(final_filename, as_attachment=True, attachment_filename=branding_name)

    except Exception as e:
        return f"Download Failed: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)