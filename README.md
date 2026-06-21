# DeepSeek Monitor

> 🖥️ Windows 专用 — DeepSeek API 余额监控，直接嵌入任务栏显示

![Platform](https://img.shields.io/badge/Platform-Windows%20Only-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![UI](https://img.shields.io/badge/UI-PyQt5%2FQSS-purple)

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📌 **任务栏余额** | 余额直接嵌入 Windows 任务栏（SetParent + LWA_COLORKEY） |
| 💰 **余额查询** | 显示总余额 / 赠送余额 / 充值余额 / 今日花费 / 预计可用天数 |
| 📊 **花费曲线** | 面积渐变图 + MIN/MAX 标注 + 鼠标悬停 tooltip，5 档时间范围 |
| 🎨 **三模主题** | ☀️ Light / 🌙 Dark / 🔄 跟随系统，全局 QSS 即时切换 |
| 🎨 **自定义颜色** | 余额高/中/低三档颜色可用系统色盘自定义，即时生效 |
| 📏 **可调阈值** | 余额区间的 High / Low 阈值可自由修改 |
| 🚀 **开机自启** | 设置页 + 托盘右键菜单 ✓ 勾选 |
| ⏱️ **自动刷新** | 15 秒 ~ 1 小时，可配置 |
| 🔔 **系统托盘** | 最小化到通知区域，右键菜单含自启开关 |
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
| `tw_color_high` / `_mid` / `_low` | 余额高/中/低颜色 (RGB hex) | `#99FF66` / `#FFD66D` / `#FF6666` |
| `tw_threshold_high` / `_low` | 余额颜色切换阈值 | `20.0` / `5.0` |
| `auto_start` | 开机自启 | `false` |
| `theme_mode` | 主题 `"light"` / `"dark"` / `"system"` | `"system"` |

历史数据自动存储到 `~/.deepseek-monitor/balance_history_*.json`，分日/周/月/季度/年五个分层文件。

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
│   ├── app.py             # 主界面 (PyQt5)
│   ├── charts.py          # QPainter 余额趋势图
│   ├── config.py          # 配置管理 + 分层历史存储
│   ├── taskbar_widget.py  # 任务栏小组件 (Win32 API)
│   ├── theme.py           # QSS 主题系统 (Light/Dark/System)
│   ├── tray.py            # 系统托盘图标
│   └── widgets.py         # GlassCard / StatCard / CollapsibleSection
└── tests/
    ├── test_api.py
    └── test_config.py
```

---

## 🛠 打包

```bash
pip install pyinstaller Pillow PyQt5
pyinstaller --onefile --windowed --name DeepSeekMonitor \
  --icon=assets/favicon.ico --add-data "src;src" \
  --add-binary "path/to/libcrypto-3-x64.dll;." \
  --add-binary "path/to/libssl-3-x64.dll;." \
  --hidden-import ssl main.py
```

> 注意：需要显式打包 OpenSSL DLL（`libcrypto-3-x64.dll` / `libssl-3-x64.dll`），否则 HTTPS 请求会失败。

---

## ⚠ 系统要求

- **Windows 10 / 11**（仅 Windows，不支持 macOS / Linux）
- 任务栏小组件依赖 explorer.exe 运行
