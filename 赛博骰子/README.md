# 赛博骰子

ESP32 + WiFi + 一位数码管的电子骰子。手机浏览器控制，按住按钮或摇一摇手机掷骰，数码管同步显示结果。

## 功能

- 手机浏览器访问 ESP32 网页，按住按钮掷骰，松开显示结果
- 摇一摇手机自动触发掷骰
- 掷骰时手机振动反馈（Android）
- 数码管同步滚动 + 显示最终数字
- 网页显示最近 8 次历史记录
- 零延迟：手机本地生成结果，异步通知 ESP32

## 硬件

| 组件 | 说明 |
|------|------|
| ESP32-WROVER 开发板 | 主控 |
| 一位数码管 | 共阴/共阳均可，段位对应见下表 |
| 杜邦线若干 | 连接数码管到 ESP32 |

### 引脚接线

| 数码管段 | ESP32 GPIO |
|----------|-----------|
| a        | 16        |
| b        | 4         |
| c        | 5         |
| d        | 18        |
| e        | 19        |
| f        | 22        |
| g        | 23        |
| dp       | 17        |

## 安装

### 所需工具

- [Arduino CLI](https://github.com/arduino/arduino-cli) 或 Arduino IDE
- ESP32 开发板支持包（arduino-esp32 v3.x）

### 编译烧录

```bash
# 编译
arduino-cli compile --fqbn esp32:esp32:esp32wrover WifiDice/WifiDice.ino

# 烧录（替换为实际串口）
arduino-cli upload -p /dev/cu.usbserial-XXXX --fqbn esp32:esp32:esp32wrover WifiDice/WifiDice.ino
```

### WiFi 配置

打开 `WifiDice/WifiDice.ino`，修改顶部两行为你的 WiFi 信息：

```cpp
const char* ssid = "你的WiFi名";
const char* password = "你的WiFi密码";
```

## 使用

1. 烧录后打开串口监视器（115200），等待 ESP32 连上 WiFi 并打印 IP 地址
2. 手机连上同一 WiFi
3. 浏览器访问 ESP32 的 IP 地址
4. 按住按钮掷骰，或摇一摇手机
5. 松开 / 停止摇晃后显示最终结果

## 项目结构

```
赛博骰子/
├── README.md
└── WifiDice/
    └── WifiDice.ino      # 主程序（Arduino + 内嵌网页）
```

## 技术要点

- ESP32 内置 WebServer 提供 HTTP 服务
- 网页内嵌在 Arduino 代码中（R 原始字符串字面量）
- 掷骰结果在手机端本地生成，fire-and-forget 通知 ESP32，实现零延迟
- DeviceMotion API 实现摇一摇检测
- Vibration API 实现振动反馈
