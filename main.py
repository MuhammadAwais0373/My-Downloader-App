from flask import Flask, request, render_template, jsonify, send_file, Response
import yt_dlp
import os
import time
import datetime
import json

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

FFMPEG_PATH = r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"  # Update if needed
os.environ["PATH"] += os.pathsep + os.path.dirname(FFMPEG_PATH)

# Global variable to store download progress
download_progress = {"percent": 0}

def get_formats(url):
    """Fetch available formats for a YouTube video."""
    ydl_opts = {"quiet": True}
    common_formats = {"18", "22", "135", "136", "137", "313", "399", "401", "bestaudio"}
    formats_list = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        for fmt in info.get("formats", []):
            if fmt.get("format_id") in common_formats:
                formats_list.append({
                    "format_id": fmt["format_id"],
                    "ext": fmt["ext"],
                    "resolution": fmt.get("resolution", "Audio"),
                    "fps": fmt.get("fps", ""),
                    "filesize": fmt.get("filesize", ""),
                })
    return formats_list

def update_progress(d):
    """Update download progress for real-time display."""
    if d["status"] == "downloading":
        percent_str = d.get("_percent_str", "0%").strip().replace("%", "")
        try:
            download_progress["percent"] = int(float(percent_str))  # Convert safely
        except ValueError:
            download_progress["percent"] = 0  # Default to 0% if parsing fails


# def download_video(url, format_id, type="video"):
#     """Download YouTube video or audio with improved speed and unique filename."""
#     timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
#     output_template = os.path.join(DOWNLOAD_FOLDER, f"%(title)s_{timestamp}.%(ext)s")
    
#     ydl_opts = {
#         "format": f"{format_id}+bestaudio" if type == "video" else "bestaudio",
#         "outtmpl": output_template,
#         "merge_output_format": "mp4" if type == "video" else "mp3",
#         "ffmpeg_location": FFMPEG_PATH,
#         "progress_hooks": [update_progress],
#         "nocheckcertificate": True,
#         "cachedir": False,
#         "fragment_retries": 5,  # Retry failed fragments
#         "concurrent_fragment_downloads": 5,  # Download multiple fragments at a time
#         "noprogress": False  # Show progress updates
#     }
    
#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         info = ydl.extract_info(url, download=True)
#         filename = ydl.prepare_filename(info).replace(".webm", ".mp4" if type == "video" else ".mp3")
#         return filename

def download_video(url, format_id, type="video"):
    """Download YouTube video or audio with improved speed and unique filename."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    output_template = os.path.join(DOWNLOAD_FOLDER, f"%(title)s_{timestamp}.%(ext)s")
    
    ydl_opts = {
        "format": f"{format_id}+bestaudio" if type == "video" else "bestaudio",
        "outtmpl": output_template,
        "merge_output_format": "mp4" if type == "video" else "mp3",
        "ffmpeg_location": FFMPEG_PATH,
        "progress_hooks": [update_progress],
        "nocheckcertificate": True,
        "cachedir": False,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 5,
        "noprogress": False
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        # Ensure proper extension
        if type == "audio":
            if filename.endswith(".webm") or filename.endswith(".m4a"):
                new_filename = filename.rsplit(".", 1)[0] + ".mp3"
                os.rename(filename, new_filename)
                filename = new_filename

        return filename

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_formats", methods=["POST"])
def get_video_formats():
    """Fetch available formats for the given YouTube URL."""
    try:
        data = request.json
        url = data.get("url")
        if not url:
            return jsonify({"error": "Invalid URL"}), 400
        formats = get_formats(url)
        return jsonify({"formats": formats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download", methods=["POST"])
def download():
    """Download the selected format (merged with audio or standalone audio)."""
    try:
        data = request.json
        url = data.get("url")
        format_id = data.get("format_id")
        type = data.get("type", "video")

        if not url or not format_id:
            return jsonify({"error": "Invalid input"}), 400

        file_path = download_video(url, format_id, type)
        return jsonify({"success": True, "file": file_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/progress")
def progress():
    """Stream download progress to the client."""
    def generate():
        while True:
            yield f"data: {json.dumps(download_progress)}\n\n"
            time.sleep(1)
    return Response(generate(), mimetype="text/event-stream")

@app.route("/download_file")
def download_file():
    """Serve the downloaded file."""
    file_path = request.args.get("file")
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway assigns PORT dynamically
    app.run(host="0.0.0.0", port=port, debug=True)
