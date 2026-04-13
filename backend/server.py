"""
Smart Question Solver - Backend Server (Railway-ready)
======================================================
Environment variables to set in Railway dashboard:
    ANTHROPIC_API_KEY   → your Anthropic API key
    PHONE_IP            → your phone's IP from IP Webcam app (e.g. 192.168.1.105)
    PHONE_PORT          → IP Webcam port (default: 8080)
    CAPTURE_INTERVAL    → seconds between captures (default: 10)
"""

import base64
import threading
import time
import io
import os
import requests
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
from PIL import Image
import anthropic
import eventlet
eventlet.monkey_patch()

# ─────────────────────────────────────────────
#  CONFIGURATION — all from environment variables
# ─────────────────────────────────────────────
PHONE_IP          = os.environ.get("PHONE_IP", "192.168.1.100")
PHONE_PORT        = os.environ.get("PHONE_PORT", "8080")
CAPTURE_INTERVAL  = int(os.environ.get("CAPTURE_INTERVAL", "10"))
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PORT              = int(os.environ.get("PORT", 5000))

SNAPSHOT_URL = f"http://{PHONE_IP}:{PHONE_PORT}/shot.jpg"

# ─────────────────────────────────────────────
#  App setup
# ─────────────────────────────────────────────
app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "smartsolver2024")

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",       # eventlet required for production
    ping_timeout=60,
    ping_interval=25,
)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

solver_running  = False
last_image_b64  = None
capture_count   = 0

# ─────────────────────────────────────────────
#  Image Capture from IP Webcam
# ─────────────────────────────────────────────
def capture_frame():
    try:
        resp = requests.get(SNAPSHOT_URL, timeout=5)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        img.thumbnail((1280, 960), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[CAPTURE ERROR] {e}")
        return None

# ─────────────────────────────────────────────
#  Claude Vision Solver
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert tutor and problem solver.
A student has placed a question or problem in front of a camera.
Your job is to:
1. Identify what subject the question is from (Math, Physics, Chemistry, Biology, History, English, etc.)
2. Clearly state the question/problem you detected
3. Solve it step-by-step with clear explanations
4. Give the final answer prominently

Format your response in clean HTML using these exact section dividers:
<div class="subject-tag">SUBJECT: [subject name]</div>
<div class="detected-question"><strong>Question Detected:</strong> [restate the question clearly]</div>
<div class="solution-steps"><strong>Solution:</strong><br>[step by step solution]</div>
<div class="final-answer"><strong>Final Answer:</strong> [clear final answer]</div>

If there is no question visible, no text, or the image is blurry, respond with:
<div class="no-question">No clear question detected. Please hold the paper steady in front of the camera.</div>
"""

def solve_with_claude(image_b64: str) -> dict:
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": "Please identify and solve the question shown in this image."}
                    ],
                }
            ],
        )
        return {"success": True, "solution": message.content[0].text}
    except Exception as e:
        print(f"[CLAUDE ERROR] {e}")
        return {"success": False, "solution": f"<div class='error'>API Error: {str(e)}</div>"}

# ─────────────────────────────────────────────
#  Background Solver Loop
# ─────────────────────────────────────────────
def solver_loop():
    global solver_running, last_image_b64, capture_count

    while solver_running:
        capture_count += 1
        print(f"\n[#{capture_count}] Starting capture cycle...")

        for remaining in range(CAPTURE_INTERVAL, 0, -1):
            if not solver_running:
                break
            socketio.emit("countdown", {"seconds": remaining, "total": CAPTURE_INTERVAL})
            eventlet.sleep(1)

        if not solver_running:
            break

        socketio.emit("status", {"message": "📸 Capturing image...", "state": "capturing"})
        image_b64 = capture_frame()

        if image_b64 is None:
            socketio.emit("status", {
                "message": "❌ Could not reach phone camera. Check IP in Railway env vars.",
                "state": "error"
            })
            continue

        last_image_b64 = image_b64
        socketio.emit("new_image", {"image": image_b64})
        socketio.emit("status", {"message": "🧠 Solving with Claude AI...", "state": "solving"})

        result = solve_with_claude(image_b64)

        socketio.emit("solution", {
            "html": result["solution"],
            "capture_num": capture_count,
            "success": result["success"]
        })

        state = "done" if result["success"] else "error"
        msg   = "✅ Solution ready!" if result["success"] else "⚠️ Error solving. Retrying..."
        socketio.emit("status", {"message": msg, "state": state})

# ─────────────────────────────────────────────
#  Flask Routes
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("templates", "index.html")

@app.route("/health")
def health():
    return {"status": "ok", "phone": SNAPSHOT_URL, "interval": CAPTURE_INTERVAL}

# ─────────────────────────────────────────────
#  SocketIO Events
# ─────────────────────────────────────────────
@socketio.on("connect")
def on_connect():
    print("[WS] Client connected")
    emit("status", {"message": "🟢 Connected to solver server", "state": "connected"})
    if last_image_b64:
        emit("new_image", {"image": last_image_b64})

@socketio.on("start_solver")
def on_start():
    global solver_running
    if not solver_running:
        solver_running = True
        eventlet.spawn(solver_loop)
        emit("status", {"message": "🚀 Solver started!", "state": "running"}, broadcast=True)

@socketio.on("stop_solver")
def on_stop():
    global solver_running
    solver_running = False
    emit("status", {"message": "⏹️ Solver stopped.", "state": "stopped"}, broadcast=True)

@socketio.on("solve_now")
def on_solve_now():
    socketio.emit("status", {"message": "📸 Manual capture...", "state": "capturing"})
    image_b64 = capture_frame()
    if image_b64:
        socketio.emit("new_image", {"image": image_b64})
        socketio.emit("status", {"message": "🧠 Solving...", "state": "solving"})
        result = solve_with_claude(image_b64)
        socketio.emit("solution", {"html": result["solution"], "capture_num": capture_count, "success": result["success"]})
        socketio.emit("status", {"message": "✅ Done!", "state": "done"})
    else:
        socketio.emit("status", {"message": "❌ Camera not reachable", "state": "error"})

# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Starting on port {PORT} | Phone: {SNAPSHOT_URL}")
    socketio.run(app, host="0.0.0.0", port=PORT, debug=False)
