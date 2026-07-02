// Cloudflare Worker: Edge TTS Proxy
// 部署到 Cloudflare Workers（免费，无需手机号）
// 注册: https://dash.cloudflare.com/sign-up

export default {
  async fetch(request) {
    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'POST only' }), {
        status: 405,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    try {
      const { text, voice = 'zh-CN-XiaoxiaoNeural' } = await request.json();
      if (!text) {
        return new Response(JSON.stringify({ error: 'text required' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Clean text
      let clean = text.replace(/[#*_`~\[\](){}]/g, '').replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '').trim();
      if (clean.length > 500) clean = clean.slice(0, 500);

      // Generate TTS via edge-tts WebSocket
      const audio = await edgeTTS(clean, voice);

      return new Response(audio, {
        headers: {
          ...corsHeaders,
          'Content-Type': 'audio/mpeg',
          'Cache-Control': 'public, max-age=3600',
        }
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  }
};

async function edgeTTS(text, voice) {
  const crypto = globalThis.crypto;
  const cid = crypto.randomUUID();
  const url = `wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?TrustedClientToken=6A5AA1D4EAFF4E9FB37E23D68491D6F4&ConnectionId=${cid}`;

  const ws = new WebSocket(url);
  ws.accept();

  return new Promise((resolve, reject) => {
    const chunks = [];
    const timeout = setTimeout(() => { ws.close(); reject(new Error('TTS timeout')); }, 15000);

    ws.addEventListener('message', (evt) => {
      if (typeof evt.data === 'string') {
        if (evt.data.includes('Path:turn.end')) {
          ws.close();
          clearTimeout(timeout);
          // Concatenate all audio chunks
          const total = chunks.reduce((s, c) => s + c.byteLength, 0);
          const result = new Uint8Array(total);
          let offset = 0;
          for (const chunk of chunks) {
            result.set(new Uint8Array(chunk), offset);
            offset += chunk.byteLength;
          }
          resolve(result.buffer);
        }
      } else if (evt.data instanceof ArrayBuffer) {
        const view = new DataView(evt.data);
        const headerLen = view.getUint16(0);
        const body = evt.data.slice(headerLen + 2);
        if (body.byteLength > 0) chunks.push(body);
      }
    });

    ws.addEventListener('error', (e) => { clearTimeout(timeout); reject(new Error('WebSocket error')); });
    ws.addEventListener('close', () => { clearTimeout(timeout); });

    ws.addEventListener('open', () => {
      // Send config
      const cfg = 'X-Timestamp:Tue Jan 01 2025 00:00:00 GMT+0000 (UTC)\r\nContent-Type:application/json; charset=utf-8\r\nPath:speech.config\r\n\r\n{"context":{"synthesis":{"audio":{"metadataoptions":{"sentenceBoundaryEnabled":"false","wordBoundaryEnabled":"false"},"outputFormat":"audio-24khz-48kbitrate-mono-mp3"}}}}';
      ws.send(cfg);

      // Send SSML
      const rid = crypto.randomUUID().replace(/-/g, '');
      const safe = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const ssml = `X-RequestId:${rid}\r\nContent-Type:application/ssml+xml\r\nX-Timestamp:Tue Jan 01 2025 00:00:00 GMT+0000 (UTC)\r\nPath:ssml\r\n\r\n<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN"><voice name="${voice}"><prosody rate="+0%" pitch="+0Hz">${safe}</prosody></voice></speak>`;
      ws.send(ssml);
    });
  });
}
