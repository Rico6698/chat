"""
Vercel Serverless Function: /api/tts
Edge TTS with zh-CN-XiaoxiaoNeural voice
"""
import asyncio
import re
import json


VOICE = "zh-CN-XiaoxiaoNeural"


async def _generate(text: str) -> bytes:
    import edge_tts
    comm = edge_tts.Communicate(text, VOICE)
    data = b""
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            data += chunk["data"]
    return data


def handler(request):
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        }

    if request.method != "POST":
        return {"statusCode": 405, "body": json.dumps({"error": "POST only"})}

    try:
        body = json.loads(request.body)
    except Exception:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON"})}

    text = body.get("text", "").strip()
    if not text:
        return {"statusCode": 400, "body": json.dumps({"error": "text required"})}

    clean = re.sub(r"[#*_`~\[\](){}]", "", text)
    clean = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", clean).strip()
    if len(clean) > 500:
        clean = clean[:500]

    try:
        audio = asyncio.run(_generate(clean))
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    import base64
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "audio/mpeg",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
        },
        "body": base64.b64encode(audio).decode(),
        "isBase64Encoded": True,
    }
