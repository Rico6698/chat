"""
Vercel Serverless Function: /api/chat
RAG + LLM medical Q&A - API key stored in environment variables
"""
import os
import re
import json
from http.server import BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Knowledge base (embedded for serverless)
KB = json.loads(open(os.path.join(os.path.dirname(__file__), '..', 'knowledge.json'), 'r', encoding='utf-8').read()) if os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'knowledge.json')) else []

SYSTEM_PROMPT = """你是医学科普助手"医知"。只回答医学健康相关的问题。

原则：科学准确、简洁易懂、每条回答末尾加"仅供参考，请遵医嘱"。

格式要求：
- 回答控制在150字以内
- 只说最关键的信息
- 不要用markdown标题、不用emoji、不用粗体
- 直接用口语化短句回答

重要限制：
- 只回答与医学、健康、疾病、用药、急救、体检、营养、心理健康等直接相关的问题
- 如果用户的问题不属于医学健康范畴，必须拒绝回答，回复："抱歉，我只能回答医学健康相关的问题。如有健康方面的疑问，请随时提问。"
- 不回答与医学无关的闲聊、打招呼等"""


def retrieve(query, kb, top_k=3):
    scores = {}
    for entry in kb:
        score = 0
        if entry.get("title", "") in query:
            score += 3
        for kw in entry.get("keywords", []):
            if kw in query:
                score += 2
        if score > 0:
            scores[entry["id"]] = score
    sorted_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
    id_map = {e["id"]: e for e in kb}
    return [id_map[sid] for sid in sorted_ids if sid in id_map]


def build_context(results):
    if not results:
        return ""
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"【参考资料{i}】{r.get('title','')}（来源：{r.get('source','')}）\n{r.get('answer','')}")
    return "\n\n---\n\n".join(parts)


def call_mimo(messages, api_key, api_base, model):
    import json as _json
    data = _json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500,
    }).encode("utf-8")

    req = Request(
        f"{api_base}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"抱歉，服务暂时不可用：{str(e)}"


def handler(request):
    """Vercel serverless function handler"""
    if request.method != "POST":
        return {"statusCode": 405, "body": json.dumps({"error": "Method not allowed"})}

    try:
        body = json.loads(request.body)
    except Exception:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON"})}

    user_msg = body.get("message", "").strip()
    if not user_msg:
        return {"statusCode": 400, "body": json.dumps({"error": "Empty message"})}

    # RAG retrieval
    results = retrieve(user_msg, KB, top_k=3)
    context = build_context(results)

    # Build messages
    api_key = os.environ.get("API_KEY", "")
    api_base = os.environ.get("API_BASE", "https://token-plan-cn.xiaomimimo.com/v1")
    model = os.environ.get("MODEL", "mimo-v2.5")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append({"role": "system", "content": f"以下是检索到的相关医学知识，请参考回答：\n\n{context}"})

    history = body.get("history", [])
    for h in history[-10:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_msg})

    # Call LLM
    reply = call_mimo(messages, api_key, api_base, model)

    # Build sources
    sources = [{"title": r.get("title",""), "category": r.get("category",""), "source": r.get("source","")} for r in results]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"reply": reply, "sources": sources}, ensure_ascii=False),
    }
