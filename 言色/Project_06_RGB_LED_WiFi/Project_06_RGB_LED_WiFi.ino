//**********************************************************************
/*
 * 文件名  : RGB LED - WiFi Web Control
 * 描述 : 通过WiFi网页控制RGB LED，多设备同时访问
 *
 * 引脚说明:
 *   红 -> GPIO4
 *   绿 -> GPIO2
 *   蓝 -> GPIO15
 */
#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "533";
const char* password = "525331314";

WebServer server(80);

int ledPins[] = {4, 2, 15};
int currentR = 102, currentG = 16, currentB = 242;

const char HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RGB 灯控</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, sans-serif;
  background: #1a1a2e; color: #fff;
  min-height: 100vh; display: flex;
  flex-direction: column; align-items: center;
  padding: 20px;
}
h1 { font-size: 22px; margin-bottom: 20px; }
#preview {
  width: 200px; height: 200px; border-radius: 50%;
  margin-bottom: 20px; border: 3px solid rgba(255,255,255,0.2);
  box-shadow: 0 0 40px rgba(0,0,0,0.5);
  transition: background 0.3s;
}
#picker {
  width: 80px; height: 80px; border: none; border-radius: 16px;
  cursor: pointer; margin-bottom: 16px;
}
.btns { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; max-width: 400px; }
.btn {
  padding: 12px 20px; border: none; border-radius: 12px;
  font-size: 15px; color: #fff; cursor: pointer;
  font-weight: 600; transition: transform 0.1s;
}
.btn:active { transform: scale(0.95); }
.info { margin-top: 16px; font-size: 13px; color: #888; }
input[type=range] { width: 200px; margin: 5px; }
.sliders { display: flex; flex-direction: column; align-items: center; gap: 8px; margin-bottom: 16px; }
.slider-row { display: flex; align-items: center; gap: 8px; }
.slider-row label { width: 20px; font-weight: bold; }
</style>
</head>
<body>
<h1>RGB 灯控</h1>
<div id="preview"></div>
<input type="color" id="picker" value="#6610f2">
<div class="sliders">
  <div class="slider-row"><label>R</label><input type="range" id="r" min="0" max="255" value="102"><span id="rv">102</span></div>
  <div class="slider-row"><label>G</label><input type="range" id="g" min="0" max="255" value="16"><span id="gv">16</span></div>
  <div class="slider-row"><label>B</label><input type="range" id="b" min="0" max="255" value="242"><span id="bv">242</span></div>
</div>
<div class="btns">
  <button class="btn" style="background:#6610f2" onclick="sendHex('6610f2')">OpenVINO</button>
  <button class="btn" style="background:#e74c3c" onclick="sendHex('ff0000')">红</button>
  <button class="btn" style="background:#2ecc71" onclick="sendHex('00ff00')">绿</button>
  <button class="btn" style="background:#3498db" onclick="sendHex('0000ff')">蓝</button>
  <button class="btn" style="background:#f39c12" onclick="sendHex('ffa500')">橙</button>
  <button class="btn" style="background:#e84393" onclick="sendHex('ff1493')">粉</button>
  <button class="btn" style="background:#1abc9c" onclick="sendHex('00ffff')">青</button>
  <button class="btn" style="background:#ffffff;color:#333" onclick="sendHex('ffffff')">白</button>
  <button class="btn" style="background:#8e44ad" onclick="sendHex(random256())">随机</button>
  <button class="btn" style="background:#555" onclick="sendHex('000000')">关灯</button>
</div>
<div class="info" id="status">就绪</div>
<script>
function sendHex(hex) {
  fetch('/color?hex=' + hex).then(r => r.text()).then(t => {
    document.getElementById('status').textContent = t;
  });
  updatePreview(hex);
}
function sendRGB() {
  var r = document.getElementById('r').value;
  var g = document.getElementById('g').value;
  var b = document.getElementById('b').value;
  document.getElementById('rv').textContent = r;
  document.getElementById('gv').textContent = g;
  document.getElementById('bv').textContent = b;
  var hex = toHex(r) + toHex(g) + toHex(b);
  document.getElementById('picker').value = '#' + hex;
  sendHex(hex);
}
function toHex(n) { n = parseInt(n); return n < 16 ? '0' + n.toString(16) : n.toString(16); }
function random256() {
  return toHex(Math.floor(Math.random()*256)) + toHex(Math.floor(Math.random()*256)) + toHex(Math.floor(Math.random()*256));
}
function updatePreview(hex) {
  document.getElementById('preview').style.background = '#' + hex;
  document.getElementById('picker').value = '#' + hex;
  var r = parseInt(hex.substr(0,2),16);
  var g = parseInt(hex.substr(2,2),16);
  var b = parseInt(hex.substr(4,2),16);
  document.getElementById('r').value = r; document.getElementById('rv').textContent = r;
  document.getElementById('g').value = g; document.getElementById('gv').textContent = g;
  document.getElementById('b').value = b; document.getElementById('bv').textContent = b;
}
document.getElementById('picker').oninput = function() { sendHex(this.value.substr(1)); };
document.getElementById('r').oninput = sendRGB;
document.getElementById('g').oninput = sendRGB;
document.getElementById('b').oninput = sendRGB;
updatePreview('6610f2');
</script>
</body>
</html>
)rawliteral";

void handleRoot() {
  server.send(200, "text/html", HTML);
}

void handleColor() {
  if (server.hasArg("hex")) {
    String hexStr = server.arg("hex");
    long hex = strtol(hexStr.c_str(), NULL, 16);
    byte r = (hex >> 16) & 0xFF;
    byte g = (hex >> 8) & 0xFF;
    byte b = hex & 0xFF;
    setColor(r, g, b);
    char buf[64];
    snprintf(buf, sizeof(buf), "OK R=%d G=%d B=%d #%02X%02X%02X", r, g, b, r, g, b);
    server.send(200, "text/plain", buf);
  } else if (server.hasArg("r") && server.hasArg("g") && server.hasArg("b")) {
    byte r = server.arg("r").toInt();
    byte g = server.arg("g").toInt();
    byte b = server.arg("b").toInt();
    setColor(r, g, b);
    char buf[64];
    snprintf(buf, sizeof(buf), "OK R=%d G=%d B=%d", r, g, b);
    server.send(200, "text/plain", buf);
  } else {
    server.send(400, "text/plain", "Missing params");
  }
}

void handleStatus() {
  char buf[80];
  snprintf(buf, sizeof(buf), "R=%d G=%d B=%d #%02X%02X%02X", currentR, currentG, currentB, currentR, currentG, currentB);
  server.send(200, "text/plain", buf);
}

void setColor(byte r, byte g, byte b) {
  currentR = r; currentG = g; currentB = b;
  ledcWrite(ledPins[0], r);
  ledcWrite(ledPins[1], g);
  ledcWrite(ledPins[2], b);
}

void setup() {
  Serial.begin(115200);
  delay(500);

  for (int i = 0; i < 3; i++) {
    ledcAttach(ledPins[i], 1000, 8);
  }
  setColor(102, 16, 242);

  WiFi.begin(ssid, password);
  Serial.print("连接WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP地址: ");
  Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.on("/color", handleColor);
  server.on("/status", handleStatus);
  server.begin();

  Serial.println("=== RGB LED WiFi控制已就绪 ===");
  Serial.printf("浏览器访问: http://%s\n", WiFi.localIP().toString().c_str());
}

void loop() {
  server.handleClient();
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      if (line.startsWith("#")) {
        long hex = strtol(line.substring(1).c_str(), NULL, 16);
        setColor((hex >> 16) & 0xFF, (hex >> 8) & 0xFF, hex & 0xFF);
      } else if (line.indexOf(',') >= 0) {
        int r = line.substring(0, line.indexOf(',')).toInt();
        int g = line.substring(line.indexOf(',') + 1, line.lastIndexOf(',')).toInt();
        int b = line.substring(line.lastIndexOf(',') + 1).toInt();
        setColor(r, g, b);
      }
      Serial.printf("当前: R=%d G=%d B=%d\n", currentR, currentG, currentB);
    }
  }
  delay(2);
}
//*************************************************************************************
