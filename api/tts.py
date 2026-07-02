"""
Vercel Serverless Function: TTS (Text-to-Speech)
Uses edge-tts with zh-CN-XiaoxiaoNeural voice
"""
import asyncio
import re
import json
from http.server import BaseHTTPRequestHandler

VOICE = "zh-CN-XiaoxiaoNeural"

async def generate_tts(text: str) -> bytes:
    """Generate TTS audio using edge-tts"""
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            text = data.get("text", "").strip()

            if not text:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "text is required"}).encode())
                return

            # Clean text
            clean = re.sub(r'[#*_`~\[\](){}]', '', text)
            clean = re.sub(r'[\U0001F300-\U0001FAFF\u2600-\u27BF]', '', clean)
            clean = clean.strip()
            if len(clean) > 500:
                clean = clean[:500]

            # Generate audio
            audio = asyncio.run(generate_tts(clean))

            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(audio)

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
