# DeepSeek Monitor

> 🖥️ Windows 专用 — DeepSeek API 余额监控，直接嵌入任务栏显示

![Platform](https://img.shields.io/badge/Platform-Windows%20Only-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📌 **任务栏余额** | 余额直接嵌入 Windows 任务栏（SetParent + LWA_COLORKEY） |
| 💰 **余额查询** | 显示总余额 / 赠送余额 / 充值余额，支持 CNY / USD |
| ⏱️ **自动刷新** | 15 秒 ~ 1 小时，可配置 |
| 🔔 **系统托盘** | 最小化到通知区域，双击恢复 |
| 🌐 **中英双语** | 一键切换 |
| 🔒 **单实例** | 重复启动自动激活已有窗口 |

---

## 🚀 使用

### 直接下载（推荐）

从 [Releases](../../releases) 下载 `DeepSeekMonitor.exe`，双击运行。

### 从源码运行

```bash
pip install -r requirements.txt
set DEEPSEEK_API_KEY=sk-xxxxxxxx
python main.py
```

首次启动会弹出 API Key 输入框，填入后自动保存到本地。

---

## ⚙ 配置

运行后自动生成 `~/.deepseek-monitor/config.json`：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `api_key` | DeepSeek API Key | `""` |
| `refresh_interval` | 刷新间隔（秒） | `60` |
| `language` | 界面语言 `"zh"` / `"en"` | `"zh"` |
| `show_taskbar_widget` | 任务栏小组件开关 | `true` |
| `taskbar_widget_position` | 靠左 `"left"` / 靠右 `"right"` | `"right"` |

---

## 📁 结构

```
deepseek-monitor/
├── main.py               # 入口 + 单实例检测
├── requirements.txt
├── config.example.json
├── assets/
│   └── favicon.ico
├── src/
│   ├── api.py             # DeepSeek API 客户端
│   ├── app.py             # 主界面 (tkinter)
│   ├── config.py          # 配置管理
│   ├── taskbar_widget.py  # 任务栏小组件 (Win32 API)
│   └── tray.py            # 系统托盘图标
└── tests/
    ├── test_api.py
    └── test_config.py
```

---

## 🛠 打包

```bash
pip install pyinstaller Pillow
pyinstaller --onefile --windowed --name DeepSeekMonitor --icon=assets/favicon.ico --add-data "src;src" main.py
```

---

## ⚠ 系统要求

- **Windows 10 / 11**（仅 Windows，不支持 macOS / Linux）
- 任务栏小组件依赖 explorer.exe 运行
