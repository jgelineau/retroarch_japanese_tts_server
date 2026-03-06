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

app = Flask(__name__)
print("Loading Apple Vision AI & Connecting to VOICEVOX...")

# --- CONFIGURATION ---
VOICEVOX_SPEAKER_ID = 23
VOICEVOX_SPEED_SCALE = 1.15 
VOICEVOX_VOLUME_SCALE = 2.0 

# Shrinks 4K/Retina screenshots down to speed up AI processing. 
# 1024 is plenty large enough for SNES/GBA pixel fonts.
MAX_IMAGE_WIDTH = 1024 
# ---------------------

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
        
        # Strip out any newlines, carriage returns, or spaces that cause VOICEVOX to pause
        text = text.replace('\n', '').replace('\r', '').replace(' ', '')
        return text.strip()
    return ""

def play_voicevox(text):
    if not text:
        return
        
    try:
        # 1. Ask VOICEVOX how to pronounce the text
        query_payload = {'text': text, 'speaker': VOICEVOX_SPEAKER_ID}
        query_res = requests.post("http://127.0.0.1:50021/audio_query", params=query_payload)
        query_res.raise_for_status()
        
        # 2. Apply the global speed and volume variables
        query_data = query_res.json()
        query_data['speedScale'] = VOICEVOX_SPEED_SCALE 
        query_data['volumeScale'] = VOICEVOX_VOLUME_SCALE
        
        # 3. Tell VOICEVOX to generate the audio file
        synth_payload = {'speaker': VOICEVOX_SPEAKER_ID}
        synth_res = requests.post("http://127.0.0.1:50021/synthesis", params=synth_payload, json=query_data)
        synth_res.raise_for_status()
        
        # 4. Save it and play it using macOS's native audio player
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(synth_res.content)
            temp_filename = f.name
            
        subprocess.run(["afplay", temp_filename])
        os.remove(temp_filename)
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to VOICEVOX. Is the VOICEVOX app open?")
    except Exception as e:
        print(f"VOICEVOX Error: {e}")

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

        # --- NEW: SHRINK IMAGE TO SPEED UP PROCESSING ---
        img = Image.open(io.BytesIO(image_bytes))
        if img.width > MAX_IMAGE_WIDTH:
            # Calculate the new height to maintain the exact aspect ratio
            ratio = MAX_IMAGE_WIDTH / img.width
            new_height = int(img.height * ratio)
            
            # Resize it cleanly
            img = img.resize((MAX_IMAGE_WIDTH, new_height), Image.Resampling.LANCZOS)
            
            # Convert it back to raw bytes for Apple Vision to read
            byte_io = io.BytesIO()
            img.save(byte_io, format='PNG')
            image_bytes = byte_io.getvalue()
        # ------------------------------------------------

        text = recognize_japanese_text(image_bytes)
        print(f"Detected Text: {text}")
        
        if text.strip():
            play_voicevox(text)
            
        return jsonify({"text": ""})
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4404)