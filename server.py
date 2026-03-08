import subprocess
from flask import Flask, request, jsonify
import json
import base64
import Vision
import Quartz
from Foundation import NSData
import requests
import tempfile
import os
from PIL import Image
import io
import logging

# --- CONFIGURATION ---
VOICEVOX_SPEAKER_ID = 23
VOICEVOX_SPEED_SCALE = 1.15 
VOICEVOX_VOLUME_SCALE = 2.0 

# Shrinks 4K/Retina screenshots down to speed up AI processing.
MAX_IMAGE_WIDTH = 1024 
# ---------------------

app = Flask(__name__)

# --- SILENCE FLASK PING LOGS ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
# -------------------------------

print("Loading Apple Vision AI & Connecting to VOICEVOX...")

# Global list to store the last 100 lines for the Web UI
dialog_history = []

def recognize_japanese_text(image_bytes):
    ns_data = NSData.dataWithBytes_length_(image_bytes, len(image_bytes))
    ci_image = Quartz.CIImage.imageWithData_(ns_data)
    
    if not ci_image:
        return ""

    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLanguages_(["ja-JP"])
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setUsesLanguageCorrection_(True)

    handler = Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(ci_image, None)
    success, error = handler.performRequests_error_([req], None)

    if success:
        results = req.results()
        text = ""
        for observation in results:
            text += observation.topCandidates_(1)[0].string()
        
        # Strip out spaces and newlines
        text = text.replace('\n', '').replace('\r', '').replace(' ', '')
        return text.strip()
    return ""

def play_voicevox(text):
    if not text:
        return
        
    try:
        query_payload = {'text': text, 'speaker': VOICEVOX_SPEAKER_ID}
        query_res = requests.post("http://127.0.0.1:50021/audio_query", params=query_payload)
        query_res.raise_for_status()
        
        query_data = query_res.json()
        query_data['speedScale'] = VOICEVOX_SPEED_SCALE 
        query_data['volumeScale'] = VOICEVOX_VOLUME_SCALE
        
        synth_payload = {'speaker': VOICEVOX_SPEAKER_ID}
        synth_res = requests.post("http://127.0.0.1:50021/synthesis", params=synth_payload, json=query_data)
        synth_res.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(synth_res.content)
            temp_filename = f.name
            
        subprocess.run(["afplay", temp_filename])
        os.remove(temp_filename)
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to VOICEVOX. Is the app open?")
    except Exception as e:
        print(f"VOICEVOX Error: {e}")

# --- WEB UI ROUTES ---
@app.route('/logs', methods=['GET'])
def web_ui():
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="utf-8">
        <title>RetroArch Dialog Logs</title>
        <style>
            body { font-family: 'Hiragino Kaku Gothic Pro', 'Meiryo', sans-serif; background: #121212; color: #e0e0e0; padding: 20px; max-width: 800px; margin: auto; }
            #latest { font-size: 2.5em; padding: 20px; background: #1e1e1e; border-left: 5px solid #4CAF50; border-radius: 5px; margin-bottom: 20px; line-height: 1.5; min-height: 1.5em; }
            #history { display: flex; flex-direction: column; gap: 10px; }
            .history-item { font-size: 1.2em; padding: 15px; background: #1a1a1a; border-radius: 5px; color: #888; }
            .history-item:hover { color: #ccc; }
        </style>
    </head>
    <body>
        <div id="latest">Waiting for dialog...</div>
        <div id="history"></div>
        <script>
            let lastData = "";
            setInterval(() => {
                fetch('/api/logs')
                    .then(r => r.json())
                    .then(data => {
                        const currentStr = JSON.stringify(data);
                        if (currentStr !== lastData && data.length > 0) {
                            lastData = currentStr;
                            document.getElementById('latest').innerText = data[0];
                            
                            const histDiv = document.getElementById('history');
                            histDiv.innerHTML = '';
                            for(let i = 1; i < data.length; i++) {
                                let div = document.createElement('div');
                                div.className = 'history-item';
                                div.innerText = data[i];
                                histDiv.appendChild(div);
                            }
                        }
                    }).catch(e => console.error(e));
            }, 1000);
        </script>
    </body>
    </html>
    """
    return html_content

@app.route('/api/logs', methods=['GET'])
def api_logs():
    return jsonify(dialog_history)
# ---------------------

@app.route('/', defaults={'path': ''}, methods=['POST'])
@app.route('/<path:path>', methods=['POST'])
def translate(path):
    try:
        raw_data = request.get_data()
        
        try:
            payload = json.loads(raw_data)
            if 'image' in payload:
                image_bytes = base64.b64decode(payload['image'])
            else:
                raise ValueError("JSON received, but no 'image' key found.")
        except json.JSONDecodeError:
            image_bytes = raw_data

        img = Image.open(io.BytesIO(image_bytes))
        if img.width > MAX_IMAGE_WIDTH:
            ratio = MAX_IMAGE_WIDTH / img.width
            new_height = int(img.height * ratio)
            img = img.resize((MAX_IMAGE_WIDTH, new_height), Image.Resampling.LANCZOS)
            
            byte_io = io.BytesIO()
            img.save(byte_io, format='PNG')
            image_bytes = byte_io.getvalue()

        text = recognize_japanese_text(image_bytes)
        print(f"Detected Text: {text}")
        
        # --- SAVE TO HISTORY ---
        if text.strip():
            if not dialog_history or dialog_history[0] != text.strip():
                dialog_history.insert(0, text.strip())
            if len(dialog_history) > 100:
                dialog_history.pop()
        # -----------------------
        
        if text.strip():
            play_voicevox(text)
            
        return jsonify({"text": ""})
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    # 0.0.0.0 allows the Steam Deck to connect if needed
    app.run(host='0.0.0.0', port=4404)