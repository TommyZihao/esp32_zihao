#!/usr/bin/env python3
"""
RGB LED 串口控制器 - 自然语言颜色解析
输入一段话，LLM 解析出颜色，通过串口控制 ESP32 RGB LED
"""

import serial
import requests
import sys
import os
import re
import time

# ============ 配置 ============
API_KEY = os.environ.get(
    "DASHSCOPE_API_KEY",
    "sk-ws-H.ERYDYMM.22zF.MEUCIQD_WQQSfyT-GRI-l6hiJ6lCZ47_Q_RDRjtL5cTUAKqx1wIgTbL_lPG6LNDr0e5tGbnBEChqOjgom5a3xQox-rUBqLo"
)
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen-plus"
SERIAL_PORT = "/dev/cu.usbserial-0001"
BAUD_RATE = 115200

SYSTEM_PROMPT = """你是一个颜色解析器。用户会说一句话，你需要从中理解用户想要的颜色，只回复R,G,B三个0-255的整数，逗号分隔，不要任何其他文字。

规则：
1. 如果用户明确指定了颜色（如"贝加尔湖的蓝色"），返回该物体最具代表性的那个颜色的RGB值。
2. 如果用户提到一个事物但没指定颜色（如"同济大学的颜色"），返回该事物标志性的、最有辨识度的颜色。例如同济大学校徽的主色是蓝色，就返回校徽蓝。
3. 如果用户提到一幅画或艺术品（如"千里江山图"），返回该作品中最具代表性的标志性颜色。千里江山图的标志性颜色是石青蓝。
4. 如果用户说关灯/黑色/无光，回复0,0,0。
5. OpenVINO的品牌色是紫色，回复102,16,242。
6. 你只输出三个数字，用逗号分隔，绝对不要输出任何解释、文字或标点。"""


def llm_parse(text):
    """调用 LLM 解析颜色，返回 (r, g, b) 或 None"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
        "max_tokens": 20,
    }
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=5)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    match = re.findall(r"\d+", content)
    if len(match) >= 3:
        return (min(int(match[0]), 255), min(int(match[1]), 255), min(int(match[2]), 255))
    return None


def send_color(ser, rgb):
    """通过串口发送颜色到 ESP32"""
    r, g, b = rgb
    cmd = f"{r},{g},{b}\n"
    ser.write(cmd.encode())
    time.sleep(0.1)
    reply = ""
    while ser.in_waiting > 0:
        reply += ser.read(ser.in_waiting).decode("utf-8", errors="replace")
    return reply.strip() or f"R={r} G={g} B={b}"


def main():
    print("=" * 50)
    print("  RGB LED 自然语言控制器")
    print("  试试: 贝加尔湖的颜色 / 故宫的中国红 / OpenVINO")
    print("  输入 quit 退出")
    print("=" * 50)

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.5)
        time.sleep(1)
        ser.reset_input_buffer()
        print(f"  [串口] 已连接 {SERIAL_PORT}\n")
    except Exception as e:
        print(f"  [串口错误] 无法连接 {SERIAL_PORT}: {e}")
        sys.exit(1)

    while True:
        try:
            text = input("🎨 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if not text:
            continue
        if text.lower() in ("quit", "exit", "q"):
            print("再见!")
            break

        t0 = time.time()
        try:
            result = llm_parse(text)
        except Exception as e:
            print(f"  [错误] {e}\n")
            continue

        if result is None:
            print("  无法解析颜色，请重试\n")
            continue

        elapsed = (time.time() - t0) * 1000
        reply = send_color(ser, result)
        r, g, b = result
        hex_color = f"#{r:02X}{g:02X}{b:02X}"
        # 终端真彩色色块
        bar = " " * 20
        swatch = f"\033[48;2;{r};{g};{b}m{bar}\033[0m"
        print(f"  {elapsed:.0f}ms | RGB({r},{g},{b}) {hex_color} | {swatch} | {reply}\n")

    ser.close()


if __name__ == "__main__":
    main()
