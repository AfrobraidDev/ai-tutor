# 🔬 Smart Question Solver — Setup Guide

### Android + Windows + Claude AI

---

## 📦 What's in this folder

```
backend/
├── server.py          ← Main Python backend
├── requirements.txt   ← Python dependencies
├── templates/
│   └── index.html     ← Live dashboard (auto-served)
└── README.md          ← This file
```

---

## 🚀 Step-by-Step Setup

### STEP 1 — Install Python (if not already)

Download Python 3.10+ from https://python.org  
During install, ✅ check "Add Python to PATH"

---

### STEP 2 — Install Dependencies

Open **Command Prompt** in this folder and run:

```
pip install -r requirements.txt
```

---

### STEP 3 — Set up IP Webcam on your Android phone

1. Open Google Play Store on your phone
2. Search and install: **"IP Webcam"** by Pavel Khlebovich (free)
3. Open the app → scroll down → tap **"Start server"**
4. The app will show an IP address like:  
   `http://192.168.1.105:8080`
5. Note this IP address — you'll need it next

> ⚠️ Your phone and laptop must be on the **same WiFi network**

---

### STEP 4 — Configure server.py

Open `server.py` in Notepad and change line 26:

```python
PHONE_IP = "192.168.1.100"   # ← Replace with YOUR phone's IP from IP Webcam
```

Also set your Anthropic API key on line 28:

```python
ANTHROPIC_API_KEY = "sk-ant-..."   # ← Your API key from console.anthropic.com
```

Or set it as a Windows environment variable (more secure):

```
set ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

### STEP 5 — Run the server

```
python server.py
```

You should see:

```
═══════════════════════════════════════════════════════
  Smart Question Solver — Backend
═══════════════════════════════════════════════════════
  Phone stream : http://192.168.1.xxx:8080/shot.jpg
  Interval     : every 10s
  Dashboard    : http://localhost:5000
═══════════════════════════════════════════════════════
```

---

### STEP 6 — Open the Dashboard

Open your browser and go to:  
👉 **http://localhost:5000**

---

### STEP 7 — Mount your phone & start solving!

1. Mount your Android phone on a stand facing your whiteboard or paper
2. Click **"▶ Start Auto-Solve"** in the dashboard
3. Hold any question in front of the camera
4. Every 10 seconds it will:
   - 📸 Capture a photo
   - 🧠 Send it to Claude AI
   - ✅ Display the full solution on screen

> Use **"⚡ Solve Now"** to skip the countdown and solve immediately

---

## 🔧 Customization

| Setting          | Location            | Default       |
| ---------------- | ------------------- | ------------- |
| Capture interval | `server.py` line 27 | 10 seconds    |
| Phone IP         | `server.py` line 26 | 192.168.1.100 |
| Phone port       | `server.py` line 27 | 8080          |

---

## ❓ Troubleshooting

| Problem                        | Solution                                                      |
| ------------------------------ | ------------------------------------------------------------- |
| "Could not reach phone camera" | Check phone IP, ensure same WiFi, IP Webcam server is running |
| "API Error"                    | Check your ANTHROPIC_API_KEY is correct                       |
| Port 5000 busy                 | Change `port=5000` to `port=5001` in server.py                |
| Blurry captures                | Ensure good lighting, hold paper steady                       |
| Camera shows wrong image       | Tap "Start server" again in IP Webcam app                     |

---

## 💡 Tips for Best Results

- 📐 Angle the paper toward the camera at ~45°
- 💡 Use good lighting — avoid glare on paper
- ✍️ Printed or clearly handwritten text works best
- 🔤 Works for: Math, Physics, Chemistry, Biology, History, English, and more
- 🌐 The dashboard can be opened on any device on your local network
  (use your laptop's local IP instead of localhost)

---

## 🔑 Getting an Anthropic API Key

1. Go to https://console.anthropic.com
2. Sign up / log in
3. Click "API Keys" → "Create Key"
4. Copy the key (starts with `sk-ant-...`)
