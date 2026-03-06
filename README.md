# RetroArch Local Japanese TTS Server (macOS Apple Silicon)

This project allows you to play Japanese retro games in RetroArch and hear the on-screen text read out loud instantly by a high-quality, anime-style AI voice. 

It is designed specifically for Japanese learners who want to practice their listening and reading skills using native game material. Unlike cloud services like zTranslate, this setup runs **100% locally on your Mac**.

---

## 🧠 How It Works
1. **RetroArch** secretly takes a screenshot of your game and sends it to our local Python server.
2. **Apple Vision AI** scans the image, ignores the game background, and flawlessly extracts the Japanese characters.
3. The server scrubs the text to remove line-breaks so the sentence flows naturally.
4. The server hands the text over to **VOICEVOX**.
5. VOICEVOX generates the audio, and your Mac plays it instantly.

---

## 💻 Requirements
* **A Mac with an Apple Silicon processor** (M1, M2, M3, or M4). 
* **RetroArch** installed.
* **VOICEVOX** installed.
* **Python 3** installed.

---

## 🚀 Step-by-Step Installation

### Step 1: Install Python 3
1. Go to python.org/downloads/macos
2. Download the macOS 64-bit universal2 installer.
3. Open the downloaded .pkg file and install.

### Step 2: Install VOICEVOX
1. Go to voicevox.hiroshiba.jp
2. Download the macOS version and drag it to Applications.
3. Open VOICEVOX and leave it running in the background.

### Step 3: Create the Server Folder
Open your Mac's Terminal app and run these commands one by one:

    mkdir ~/RetroArch_AI_Server
    cd ~/RetroArch_AI_Server
    python3 -m venv venv
    source venv/bin/activate

### Step 4: Install Dependencies
Run this command in the Terminal:

    pip3 install flask pyobjc-framework-Vision pyobjc-framework-Quartz requests

### Step 5: Create the Script
Download the `server.py` from this repository into your folder

### Step 6: Configure RetroArch
You only need to do this once. Open RetroArch and navigate to the settings:
1. Go to **Settings > AI Service**:
    * Set **AI Service Enabled** to ON.
    * Set **AI Service Output** to `Speech Mode`.
    * Set **AI Service URL** to `http://127.0.0.1:4404/`.
2. Go to **Settings > Input > Hotkeys**:
    * Scroll down and assign a button to **AI Service**. This is the button you will press in-game to hear the text!

## 🎮 How to Play
1. Open VOICEVOX.
2. Open a new terminal and run these commands to start the tool:
    cd ~/RetroArch_AI_Server
    source venv/bin/activate
    python3 server.py
3. Open RetroArch and run your game
4. Have fun!

VOICEVOX and the server tool needs to be running during your gaming session.