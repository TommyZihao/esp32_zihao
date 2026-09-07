#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "533";
const char* password = "525331314";

int a = 16, b = 4, c = 5, d = 18, e = 19, f = 22, g = 23, dp = 17;

WebServer server(80);

volatile bool rolling = false;
unsigned long lastRollTime = 0;
const int rollInterval = 80;

void displayNumber(int num) {
  digitalWrite(a, LOW); digitalWrite(b, LOW); digitalWrite(c, LOW); digitalWrite(d, LOW);
  digitalWrite(e, LOW); digitalWrite(f, LOW); digitalWrite(g, LOW); digitalWrite(dp, LOW);

  switch (num) {
    case 0:
      digitalWrite(a, HIGH); digitalWrite(b, HIGH); digitalWrite(c, HIGH); digitalWrite(d, HIGH);
      digitalWrite(e, HIGH); digitalWrite(f, HIGH);
      break;
    case 1:
      digitalWrite(b, HIGH); digitalWrite(c, HIGH);
      break;
    case 2:
      digitalWrite(a, HIGH); digitalWrite(b, HIGH); digitalWrite(d, HIGH); digitalWrite(e, HIGH); digitalWrite(g, HIGH);
      break;
    case 3:
      digitalWrite(a, HIGH); digitalWrite(b, HIGH); digitalWrite(c, HIGH); digitalWrite(d, HIGH); digitalWrite(g, HIGH);
      break;
    case 4:
      digitalWrite(b, HIGH); digitalWrite(c, HIGH); digitalWrite(f, HIGH); digitalWrite(g, HIGH);
      break;
    case 5:
      digitalWrite(a, HIGH); digitalWrite(c, HIGH); digitalWrite(d, HIGH); digitalWrite(f, HIGH); digitalWrite(g, HIGH);
      break;
    case 6:
      digitalWrite(a, HIGH); digitalWrite(c, HIGH); digitalWrite(d, HIGH); digitalWrite(e, HIGH); digitalWrite(f, HIGH); digitalWrite(g, HIGH);
      break;
    case 7:
      digitalWrite(a, HIGH); digitalWrite(b, HIGH); digitalWrite(c, HIGH);
      break;
    case 8:
      digitalWrite(a, HIGH); digitalWrite(b, HIGH); digitalWrite(c, HIGH); digitalWrite(d, HIGH);
      digitalWrite(e, HIGH); digitalWrite(f, HIGH); digitalWrite(g, HIGH);
      break;
    case 9:
      digitalWrite(a, HIGH); digitalWrite(b, HIGH); digitalWrite(c, HIGH); digitalWrite(d, HIGH);
      digitalWrite(f, HIGH); digitalWrite(g, HIGH);
      break;
  }
}

void handleRoot() {
  String html = R"HTML(
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<style>
* { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
body {
  font-family: -apple-system, "PingFang SC", sans-serif;
  background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
  color: #eee; min-height: 100vh;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
h1 { font-size: 1.8em; margin-bottom: 25px; letter-spacing:2px; }
.sub { font-size:0.85em; color:#888; margin-bottom:30px; }
.dice-btn {
  width: 180px; height: 180px; border-radius: 50%;
  border: 4px solid rgba(255,255,255,0.15);
  font-size: 1.4em; font-weight: bold; color: #fff;
  background: radial-gradient(circle at 30% 30%, #e94560, #0f3460);
  box-shadow: 0 8px 25px rgba(233,69,96,0.35), inset 0 2px 10px rgba(255,255,255,0.2);
  cursor: pointer; user-select: none; -webkit-user-select: none;
  transition: transform 0.08s, box-shadow 0.08s;
}
.dice-btn:active {
  transform: scale(0.90);
  box-shadow: 0 3px 12px rgba(233,69,96,0.5), inset 0 4px 15px rgba(0,0,0,0.3);
}
.dice-btn.rolling {
  animation: shake 0.12s infinite;
}
@keyframes shake {
  0% { transform: translate(0,0) rotate(0); }
  25% { transform: translate(-3px,2px) rotate(-3deg); }
  50% { transform: translate(3px,-2px) rotate(3deg); }
  75% { transform: translate(-2px,1px) rotate(-2deg); }
  100% { transform: translate(0,0) rotate(0); }
}
.result-wrap { margin-top: 35px; text-align:center; }
.result {
  font-size: 3.5em; font-weight: bold;
  color: #e94560; min-height: 70px; line-height:70px;
}
.result.pop { animation: pop 0.35s ease; }
@keyframes pop {
  0% { transform: scale(0); opacity:0; }
  60% { transform: scale(1.35); opacity:1; }
  100% { transform: scale(1); }
}
.history { margin-top:15px; font-size:0.85em; color:#666; }
.ip-info { position: fixed; bottom: 8px; font-size: 0.75em; color: #444; }
</style>
</head>
<body>
<h1>&#127922; ESP32 电子骰子</h1>
<div class="sub">按住按钮或摇一摇手机掷骰</div>
<button class="dice-btn" id="btn">&#127922; 按住掷骰</button>
<div class="result-wrap">
  <div class="result" id="result"></div>
  <div class="history" id="history"></div>
</div>
<div class="ip-info">ESP32 Dice</div>
<script>
var btn=document.getElementById('btn');
var result=document.getElementById('result');
var historyEl=document.getElementById('history');
var hist=[];
var rolling=false;
var rollTimer=null;

function start(e){e.preventDefault();startRoll();}
function stop(e){e.preventDefault();stopRoll();}

btn.addEventListener('touchstart',start,{passive:false});
btn.addEventListener('touchend',stop,{passive:false});
btn.addEventListener('touchcancel',stop,{passive:false});
btn.addEventListener('mousedown',start);
btn.addEventListener('mouseup',stop);
btn.addEventListener('mouseleave',function(e){if(rolling)stopRoll();});

var shakeThreshold=15;
var lastShake=0;
var shakeCooldown=1200;
window.addEventListener('devicemotion',function(e){
  var acc=e.accelerationIncludingGravity;
  if(!acc)return;
  var mag=Math.sqrt((acc.x||0)*(acc.x||0)+(acc.y||0)*(acc.y||0)+(acc.z||0)*(acc.z||0));
  if(mag>shakeThreshold && !rolling && Date.now()-lastShake>shakeCooldown){
    lastShake=Date.now();
    startRoll();
    setTimeout(function(){
      if(rolling)stopRoll();
    },1000+Math.random()*800);
  }
});

function startRoll(){
  if(rolling)return;
  rolling=true;
  btn.classList.add('rolling');
  btn.textContent='\u0FD0 掷骰中...';
  result.textContent='';
  result.classList.remove('pop');
  if(navigator.vibrate)navigator.vibrate(40);
  fetch('/roll',{mode:'no-cors'});
  rollTimer=setInterval(function(){
    result.textContent='\u{1F3B2} '+Math.floor(Math.random()*6+1);
    if(navigator.vibrate)navigator.vibrate(15);
  },80);
}
function stopRoll(){
  if(!rolling)return;
  rolling=false;
  btn.classList.remove('rolling');
  btn.innerHTML='\uD83C\uDFB2 按住掷骰';
  if(rollTimer){clearInterval(rollTimer);rollTimer=null;}
  var finalNum=Math.floor(Math.random()*6+1);
  result.textContent='\u{1F3B2} '+finalNum;
  result.classList.add('pop');
  if(navigator.vibrate)navigator.vibrate([60,40,100]);
  hist.unshift(finalNum);
  if(hist.length>8)hist.pop();
  historyEl.textContent='历史: '+hist.join(' ');
  fetch('/stop?n='+finalNum,{mode:'no-cors'});
}
</script>
</body>
</html>
)HTML";
  server.send(200, "text/html", html);
}

void handleRoll() {
  rolling = true;
  server.send(200, "application/json", "{\"status\":\"rolling\"}");
}

void handleStop() {
  rolling = false;
  int finalNum = 1;
  if (server.hasArg("n")) {
    finalNum = server.arg("n").toInt();
    if (finalNum < 0 || finalNum > 9) finalNum = 1;
  }
  displayNumber(finalNum);
  server.send(200, "application/json", "{\"number\":" + String(finalNum) + "}");
}

void setup() {
  Serial.begin(115200);

  pinMode(a, OUTPUT); pinMode(b, OUTPUT); pinMode(c, OUTPUT); pinMode(d, OUTPUT);
  pinMode(e, OUTPUT); pinMode(f, OUTPUT); pinMode(g, OUTPUT); pinMode(dp, OUTPUT);

  displayNumber(8);
  delay(300);
  displayNumber(0);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("WiFi connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected! IP: ");
  Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.on("/roll", handleRoll);
  server.on("/stop", HTTP_GET, handleStop);
  server.begin();

  Serial.println("Dice ready!");
}

void loop() {
  server.handleClient();

  if (rolling) {
    if (millis() - lastRollTime > rollInterval) {
      lastRollTime = millis();
      displayNumber(random(1, 7));
    }
  }
}
