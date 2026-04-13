"""
Smart Question Solver - Backend Server (Upload Mode)
=====================================================
Environment variables to set in Railway dashboard:
    ANTHROPIC_API_KEY   → your Anthropic API key
    SECRET_KEY          → random secret string
"""

import base64
import io
import os
import anthropic
from flask import Flask, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit
from PIL import Image
import eventlet
eventlet.monkey_patch()

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PORT              = int(os.environ.get("PORT", 5000))

# ─────────────────────────────────────────────
#  App setup
# ─────────────────────────────────────────────
app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"]      = os.environ.get("SECRET_KEY", "smartsolver2024")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    ping_timeout=60,
    ping_interval=25,
)

client        = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
solve_count   = 0
last_image_b64 = None

# ─────────────────────────────────────────────
#  Image Processing
# ─────────────────────────────────────────────
def process_image(file_bytes: bytes) -> str:
    """Resize and encode image to base64."""
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img.thumbnail((1280, 960), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# ─────────────────────────────────────────────
#  Claude Vision Solver
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert tutor and problem solver.
A student has taken a photo of a question or problem.
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
<div class="no-question">No clear question detected. Please retake the photo with better lighting and hold the paper steady.</div>
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
#  Flask Routes
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("templates", "index.html")

@app.route("/health")
def health():
    return {"status": "ok"}

@app.route("/upload", methods=["POST"])
def upload():
    """Receive image upload, solve it, broadcast result via SocketIO."""
    global solve_count, last_image_b64

    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        file_bytes = file.read()
        image_b64  = process_image(file_bytes)
        last_image_b64 = image_b64

        # Broadcast image to all connected dashboard clients
        socketio.emit("new_image", {"image": image_b64})
        socketio.emit("status", {"message": "🧠 Solving with Claude AI...", "state": "solving"})

        result = solve_with_claude(image_b64)

        if result["success"]:
            solve_count += 1
            socketio.emit("solution", {
                "html": result["solution"],
                "solve_num": solve_count,
                "success": True
            })
            socketio.emit("status", {"message": "✅ Solution ready!", "state": "done"})
            return jsonify({"success": True, "solve_count": solve_count})
        else:
            socketio.emit("status", {"message": "⚠️ Error solving. Try again.", "state": "error"})
            return jsonify({"success": False, "error": "Claude error"}), 500

    except Exception as e:
        print(f"[UPLOAD ERROR] {e}")
        socketio.emit("status", {"message": f"❌ Error: {str(e)}", "state": "error"})
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────
#  SocketIO Events
# ─────────────────────────────────────────────
@socketio.on("connect")
def on_connect():
    print("[WS] Client connected")
    emit("status", {"message": "🟢 Connected — ready to solve!", "state": "connected"})
    if last_image_b64:
        emit("new_image",  {"image": last_image_b64})

# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Starting on port {PORT}")
    socketio.run(app, host="0.0.0.0", port=PORT, debug=False)
