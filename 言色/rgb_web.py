#!/usr/bin/env python3
"""
RGB LED 网页控制器 - 语音识别 + LLM颜色解析
按住说话 → DashScope ASR 识别 → LLM 解析颜色 → 控制 ESP32
"""

import requests
import json
import re
import os
import ssl
import subprocess
import tempfile
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ============ 配置 ============
API_KEY = os.environ.get(
    "DASHSCOPE_API_KEY",
    "sk-ws-H.ERYDYMM.22zF.MEUCIQD_WQQSfyT-GRI-l6hiJ6lCZ47_Q_RDRjtL5cTUAKqx1wIgTbL_lPG6LNDr0e5tGbnBEChqOjgom5a3xQox-rUBqLo"
)
dashscope.api_key = API_KEY
LLM_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
LLM_MODEL = "qwen-plus"
ASR_MODEL = "paraformer-realtime-v2"
ESP32_IP = "192.168.31.231"
SERVER_PORT = 8080

SYSTEM_PROMPT = """你是一个颜色解析器。用户会说一句话，你需要从中理解用户想要的颜色，只回复R,G,B三个0-255的整数，逗号分隔，不要任何其他文字。

规则：
1. 如果用户明确指定了颜色（如"贝加尔湖的蓝色"），返回该物体最具代表性的那个颜色的RGB值。
2. 如果用户提到一个事物但没指定颜色（如"同济大学的颜色"），返回该事物标志性的、最有辨识度的颜色。例如同济大学校徽的主色是蓝色，就返回校徽蓝。
3. 如果用户提到一幅画或艺术品（如"千里江山图"），返回该作品中最具代表性的标志性颜色。千里江山图的标志性颜色是石青蓝。
4. 如果用户说关灯/黑色/无光，回复0,0,0。
5. OpenVINO的品牌色是紫色，回复102,16,242。
6. 你只输出三个数字，用逗号分隔，绝对不要输出任何解释、文字或标点。"""

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RGB 灯控</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, sans-serif; background: #1a1a2e; color: #fff; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 20px; user-select: none; }
h1 { font-size: 22px; margin-bottom: 16px; }
#preview { width: 160px; height: 160px; border-radius: 50%; margin-bottom: 14px; border: 3px solid rgba(255,255,255,0.15); box-shadow: 0 0 60px rgba(102,16,242,0.3); transition: all 0.4s; }
.input-group { display: flex; gap: 8px; width: 90%; max-width: 420px; margin-bottom: 12px; }
#text { flex: 1; padding: 14px 16px; border: none; border-radius: 12px; font-size: 16px; background: #2a2a4e; color: #fff; outline: none; }
#text::placeholder { color: #666; }
#send { padding: 14px 18px; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; background: #6610f2; color: #fff; cursor: pointer; white-space: nowrap; }
#send:active { transform: scale(0.95); }
#mic {
  width: 100%; padding: 20px; border: none; border-radius: 16px;
  font-size: 18px; font-weight: 700; color: #fff; cursor: pointer;
  background: #2a2a4e; margin-bottom: 14px; transition: all 0.2s;
  max-width: 420px; -webkit-user-select: none; touch-action: manipulation;
}
#mic.recording { background: #e74c3c; animation: pulse 1s infinite; }
#mic:disabled { opacity: 0.5; }
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(231,76,60,0.5); }
  70% { box-shadow: 0 0 0 20px rgba(231,76,60,0); }
  100% { box-shadow: 0 0 0 0 rgba(231,76,60,0); }
}
#picker { width: 56px; height: 56px; border: none; border-radius: 14px; cursor: pointer; }
.picker-row { display: flex; gap: 12px; align-items: center; margin-bottom: 14px; }
.sliders { display: flex; flex-direction: column; gap: 6px; width: 90%; max-width: 340px; margin-bottom: 16px; }
.slider-row { display: flex; align-items: center; gap: 8px; }
.slider-row label { width: 20px; font-weight: bold; font-size: 14px; }
.slider-row input[type=range] { flex: 1; }
.slider-row span { width: 36px; text-align: right; font-size: 13px; color: #aaa; }
.btns { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; max-width: 420px; }
.btn { padding: 10px 18px; border: none; border-radius: 10px; font-size: 14px; color: #fff; cursor: pointer; font-weight: 600; transition: transform 0.1s; }
.btn:active { transform: scale(0.95); }
#status { margin-top: 14px; font-size: 14px; color: #888; min-height: 20px; text-align: center; }
#thinking { display: none; margin-top: 10px; font-size: 14px; color: #6610f2; }
</style>
</head>
<body>
<h1>RGB 灯控</h1>
<div id="preview"></div>
<button id="mic">🎤 按住说话</button>
<div class="input-group">
  <input type="text" id="text" placeholder="试试: 贝加尔湖的蓝色 / 千里江山图" onkeydown="if(event.key==='Enter')sendText()">
  <button id="send" onclick="sendText()">解析</button>
</div>
<div class="picker-row">
  <input type="color" id="picker" value="#6610f2" onchange="sendHex(this.value.substr(1))">
  <div class="sliders">
    <div class="slider-row"><label>R</label><input type="range" id="r" min="0" max="255" value="102" oninput="sendRGB()"><span id="rv">102</span></div>
    <div class="slider-row"><label>G</label><input type="range" id="g" min="0" max="255" value="16" oninput="sendRGB()"><span id="gv">16</span></div>
    <div class="slider-row"><label>B</label><input type="range" id="b" min="0" max="255" value="242" oninput="sendRGB()"><span id="bv">242</span></div>
  </div>
</div>
<div class="btns">
  <button class="btn" style="background:#6610f2" onclick="sendHex('6610f2')">OpenVINO</button>
  <button class="btn" style="background:#e74c3c" onclick="sendHex('ff0000')">红</button>
  <button class="btn" style="background:#2ecc71" onclick="sendHex('00ff00')">绿</button>
  <button class="btn" style="background:#3498db" onclick="sendHex('0000ff')">蓝</button>
  <button class="btn" style="background:#f39c12" onclick="sendHex('ffa500')">橙</button>
  <button class="btn" style="background:#e84393" onclick="sendHex('ff1493')">粉</button>
  <button class="btn" style="background:#1abc9c" onclick="sendHex('00ffff')">青</button>
  <button class="btn" style="background:#fff;color:#333" onclick="sendHex('ffffff')">白</button>
  <button class="btn" style="background:#8e44ad" onclick="randomColor()">随机</button>
  <button class="btn" style="background:#555" onclick="sendHex('000000')">关灯</button>
</div>
<div id="thinking">处理中...</div>
<div id="status">就绪</div>
<script>
var mediaRecorder = null;
var audioChunks = [];
var isRecording = false;
var micStream = null;

async function startRec() {
  if (isRecording) return;
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch(e) {
    showStatus('麦克风权限被拒绝: ' + e.message);
    return;
  }
  isRecording = true;
  audioChunks = [];
  var mime = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
  mediaRecorder = new MediaRecorder(micStream, { mimeType: mime });
  mediaRecorder.ondataavailable = function(e) { if (e.data.size > 0) audioChunks.push(e.data); };
  mediaRecorder.onstop = function() {
    var blob = new Blob(audioChunks, { type: mime });
    var ext = mime.includes('webm') ? 'webm' : 'm4a';
    sendAudio(blob, ext);
    if (micStream) { micStream.getTracks().forEach(t => t.stop()); micStream = null; }
  };
  mediaRecorder.start();
  var btn = document.getElementById('mic');
  btn.classList.add('recording');
  btn.textContent = '🔴 松开发送';
  showStatus('正在聆听...');
}

function stopRec() {
  if (!isRecording) return;
  isRecording = false;
  var btn = document.getElementById('mic');
  btn.classList.remove('recording');
  btn.textContent = '处理中...';
  btn.disabled = true;
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
}

function sendAudio(blob, ext) {
  showStatus('语音识别中...');
  var formData = new FormData();
  formData.append('file', blob, 'audio.' + ext);
  formData.append('model', 'paraformer-v2');
  fetch('/api/asr', { method: 'POST', body: formData })
    .then(r => r.json())
    .then(d => {
      var btn = document.getElementById('mic');
      btn.textContent = '🎤 按住说话';
      btn.disabled = false;
      if (d.ok && d.text) {
        document.getElementById('text').value = d.text;
        showStatus('识别: ' + d.text);
        sendText();
      } else {
        showStatus('识别失败: ' + (d.error || '未识别到内容'));
      }
    })
    .catch(e => {
      var btn = document.getElementById('mic');
      btn.textContent = '🎤 按住说话';
      btn.disabled = false;
      showStatus('请求失败: ' + e.message);
    });
}

var micBtn = document.getElementById('mic');
micBtn.addEventListener('touchstart', function(e) { e.preventDefault(); startRec(); });
micBtn.addEventListener('touchend', function(e) { e.preventDefault(); stopRec(); });
micBtn.addEventListener('mousedown', function(e) { e.preventDefault(); startRec(); });
micBtn.addEventListener('mouseup', function(e) { e.preventDefault(); stopRec(); });
micBtn.addEventListener('mouseleave', function(e) { if (isRecording) stopRec(); });

function sendHex(hex) {
  fetch('/api/color?hex=' + hex).then(r => r.json()).then(d => {
    if (d.ok) { updateUI(d.r, d.g, d.b); showStatus(d.hex + ' ' + d.desc); }
  });
}
function sendRGB() {
  var r = +document.getElementById('r').value;
  var g = +document.getElementById('g').value;
  var b = +document.getElementById('b').value;
  document.getElementById('rv').textContent = r;
  document.getElementById('gv').textContent = g;
  document.getElementById('bv').textContent = b;
  var hex = toHex(r) + toHex(g) + toHex(b);
  document.getElementById('picker').value = '#' + hex;
  sendHex(hex);
}
function sendText() {
  var text = document.getElementById('text').value.trim();
  if (!text) return;
  document.getElementById('thinking').style.display = 'block';
  document.getElementById('status').textContent = '';
  fetch('/api/parse?text=' + encodeURIComponent(text))
    .then(r => r.json())
    .then(d => {
      document.getElementById('thinking').style.display = 'none';
      if (d.ok) {
        updateUI(d.r, d.g, d.b);
        showStatus(d.hex + ' | ' + d.ms + 'ms | ' + text);
      } else {
        showStatus('解析失败: ' + (d.error || '未知错误'));
      }
    })
    .catch(e => {
      document.getElementById('thinking').style.display = 'none';
      showStatus('请求失败');
    });
}
function randomColor() {
  sendHex(toHex(Math.random()*256|0) + toHex(Math.random()*256|0) + toHex(Math.random()*256|0));
}
function toHex(n) { n = n|0; return n < 16 ? '0' + n.toString(16) : n.toString(16); }
function updateUI(r, g, b) {
  var hex = '#' + toHex(r) + toHex(g) + toHex(b);
  document.getElementById('preview').style.background = hex;
  document.getElementById('preview').style.boxShadow = '0 0 60px ' + hex + '88';
  document.getElementById('picker').value = hex;
  document.getElementById('r').value = r; document.getElementById('rv').textContent = r;
  document.getElementById('g').value = g; document.getElementById('gv').textContent = g;
  document.getElementById('b').value = b; document.getElementById('bv').textContent = b;
}
function showStatus(msg) { document.getElementById('status').textContent = msg; }
updateUI(102, 16, 242);
</script>
</body>
</html>"""


def llm_parse(text):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
        "max_tokens": 20,
    }
    resp = requests.post(LLM_URL, headers=headers, json=payload, timeout=10)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    match = re.findall(r"\d+", content)
    if len(match) >= 3:
        return (min(int(match[0]), 255), min(int(match[1]), 255), min(int(match[2]), 255))
    return None


def asr_transcribe(audio_data, filename):
    """使用 DashScope Recognition API 识别语音（支持本地文件直传）"""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'webm'
    with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name

    wav_path = tmp_path.rsplit('.', 1)[0] + '.wav'
    if ext != 'wav':
        subprocess.run(
            ['ffmpeg', '-y', '-i', tmp_path, '-ar', '16000', '-ac', '1', wav_path],
            capture_output=True, timeout=10,
        )
        os.unlink(tmp_path)
    else:
        wav_path = tmp_path

    class _Cb(RecognitionCallback):
        pass

    recognition = Recognition(
        model=ASR_MODEL,
        callback=_Cb(),
        format='wav',
        sample_rate=16000,
    )
    result = recognition.call(file=wav_path)
    os.unlink(wav_path)

    if result.status_code != 200:
        raise Exception(f"ASR error: {result.status_code}")

    sentences = result.output.get('sentence', [])
    if sentences:
        return sentences[-1].get('text', '').strip()
    return ''


def esp32_send_hex(hex_str):
    try:
        resp = requests.get(f"http://{ESP32_IP}/color?hex={hex_str}", timeout=3)
        return resp.text
    except:
        return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())

        elif path == "/api/parse":
            text = params.get("text", [""])[0]
            if not text:
                self._json({"ok": False, "error": "no text"})
                return
            import time
            t0 = time.time()
            try:
                result = llm_parse(text)
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
                return
            elapsed = int((time.time() - t0) * 1000)
            if result is None:
                self._json({"ok": False, "error": "parse failed"})
                return
            r, g, b = result
            hex_str = f"{r:02x}{g:02x}{b:02x}"
            esp32_send_hex(hex_str)
            self._json({
                "ok": True, "r": r, "g": g, "b": b,
                "hex": f"#{hex_str.upper()}",
                "ms": elapsed, "desc": text,
            })

        elif path == "/api/color":
            hex_str = params.get("hex", [""])[0]
            if hex_str:
                reply = esp32_send_hex(hex_str)
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                self._json({
                    "ok": True, "r": r, "g": g, "b": b,
                    "hex": f"#{hex_str.upper()}",
                    "desc": reply or "OK",
                })
            else:
                self._json({"ok": False, "error": "no hex"})

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/asr":
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._json({"ok": False, "error": "expected multipart"})
                return

            boundary = content_type.split("boundary=")[1].encode()
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))

            parts = body.split(b"--" + boundary)
            audio_data = None
            filename = "audio.webm"
            for part in parts:
                if b"filename=" in part:
                    name_match = re.search(rb'filename="([^"]+)"', part)
                    if name_match:
                        filename = name_match.group(1).decode()
                    header_end = part.find(b"\r\n\r\n")
                    if header_end >= 0:
                        audio_data = part[header_end + 4:].rstrip(b"\r\n")

            if not audio_data:
                self._json({"ok": False, "error": "no audio data"})
                return

            try:
                text = asr_transcribe(audio_data, filename)
                if text:
                    self._json({"ok": True, "text": text})
                else:
                    self._json({"ok": False, "error": "empty result"})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        else:
            self.send_response(404)
            self.end_headers()

    def _json(self, obj):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode())


def main():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    my_ip = s.getsockname()[0]
    s.close()

    cert_dir = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(cert_dir, "cert.pem")
    key_path = os.path.join(cert_dir, "key.pem")

    print("=" * 50)
    print("  RGB LED 网页控制器")
    print(f"  ESP32 地址: http://{ESP32_IP}")
    print(f"  本机 Web:  https://{my_ip}:{SERVER_PORT}")
    print()
    print("  手机/电脑浏览器打开上面的本机地址")
    print("  首次打开会提示证书不安全，点「高级」->「继续」即可")
    print("  按住语音按钮说话，松开后自动识别+解析颜色")
    print("=" * 50)

    server = HTTPServer(("0.0.0.0", SERVER_PORT), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, key_path)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
