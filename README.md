# 🎙️ VoiceMeeter Toggle — MP3 一键转麦克风

将 MP3 音频通过 VoiceMeeter 虚拟混音，伪装成麦克风输入，实现"在 QQ/微信中以语音消息形式发送 MP3"。

**一键切换 · 全局热键 · 播完自动停止**

---

## 🎯 功能

| 功能 | 说明 |
|------|------|
| 🔘 **一键切换** | 点击按钮，自动配置音频路由 |
| 🎵 **内建播放器** | 选择 MP3/WAV/FLAC，直接播放到虚拟麦克风 |
| ⌨ **全局热键** | `F1+F2` 播放/停止，`F3` 开启/关闭功能，在 QQ 里也能触发 |
| 🔁 **循环播放** | 可选的循环模式 |
| ⏹ **播完自动停止** | 默认开启，播放完毕自动复位 |
| 🛡 **防呆关闭** | ON 状态下关闭程序时弹出确认对话框，防止误关 |
| 💾 **状态记忆** | 切换前自动保存原始设置，关闭时一键恢复 |

---

## 📋 前置要求

| 依赖 | 说明 |
|------|------|
| **VoiceMeeter** | [下载 Standard 版](https://vb-audio.com/Voicemeeter/)（免费） |
| **Windows 10/11** | 64 位 |
| **ffmpeg**（可选） | 播放 MP3 需要，[下载](https://ffmpeg.org/download.html)后添加到系统 PATH |

> VoiceMeeter 虚拟音频驱动会在安装时自动配置，无需手动操作。

---

## 🚀 快速开始

### 方式一：使用打包好的 EXE

1. 从 [Releases](../../releases) 下载 `VoiceMeeterToggle.exe`
2. 右键 → **以管理员身份运行**（切换音频设备需要）
3. 确保 VoiceMeeter 已启动
4. 点击按钮 或 按 `F3` → 变绿 → 选择 MP3 → 播放！
5. 在 QQ 按住录音 → 按 `F1+F2` 触发播放，松手后按 `F3` 一键关闭

### 方式二：从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/voicemeeter-toggle.git
cd voicemeeter-toggle

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
# 或双击 launcher.bat（自动提权）
```

---

## 📖 使用说明

### 基本操作

```
1. 启动 VoiceMeeter（托盘有图标即可）
2. 双击 VoiceMeeterToggle.exe（管理员）
3. 点击按钮 或 按 F3 → 开启功能（按钮变绿）
4. 点击 "浏览..." 选择 MP3 文件
5. 在 QQ 中按住空格录音 → 按 F1+F2 播放
6. 松空格 → 语音消息发送成功 🎉
7. 再次点击按钮 或 按 F3 → 恢复原始设置
```

### 界面说明

```
┌─────────────────────────────────┐
│  VoiceMeeter MP3 → 麦克风        │
│                                 │
│  ┌─────────────────────┐        │
│  │    🟢 工作中 / 点击恢复  │        │  ← 主切换按钮
│  └─────────────────────┘        │
│  ✅ MP3 → 麦克风 工作中           │  ← 状态信息
│  ─────────────────────────────  │
│  全局热键: F3 开启/关闭功能       │  ← 🆕 始终可见
│  ─────────────────────────────  │
│  音频文件: [song.mp3    ] [浏览] │  ← 文件选择 (ON 时显示)
│  [ ▶ 播放 ]  [ ■ 停止 ]         │  ← 播放控制 (ON 时显示)
│  ☑ 循环播放  ☑ 播完自动停止       │  ← 选项 (ON 时显示)
│  热键: F1+F2 播放/停止           │  ← 快捷键提示 (ON 时显示)
└─────────────────────────────────┘
```

### 音频流向

```
[MP3 文件]
    ↓ sounddevice
[VoiceMeeter Input (VAIO)]  ← 虚拟播放设备（不干扰系统默认设备）
    ↓ VoiceMeeter Strip[2]
    ├→ B1 总线 → "VoiceMeeter Out B1" → QQ/微信 采集 ✅
    └→ A1 总线 → 耳机/音响（需在 VoiceMeeter 中配置 A1 硬件输出）
```

---

## ⚙️ 配置

编辑 `settings.py` 可修改：

```python
# 全局热键
HOTKEY_PLAY_STOP = "f1+f2"    # 播放/停止
HOTKEY_TOGGLE = "f3"          # 开启/关闭功能切换

# VoiceMeeter 版本
VOICEMEETER_KIND = "basic"    # basic / banana / potato

# 轮询间隔
RECORDER_POLL_INTERVAL = 300  # 播放状态检测间隔 (ms)
```

支持的快捷键格式参考 [keyboard 库文档](https://github.com/boppreh/keyboard)。

---

## 🔧 常见问题

### Q: 点击按钮报错 "VoiceMeeter 未运行"
**A:** 确保 VoiceMeeter 已启动。可以双击 `C:\Program Files (x86)\VB\Voicemeeter\voicemeeter_x64.exe`

### Q: 对方听不到 MP3 声音
**A:** 检查：
1. VoiceMeeter 中 **Strip[2] 的 B1 按钮是否亮起**
2. QQ/微信的麦克风是否选择了 "**VoiceMeeter Out B1**"
3. Windows 声音设置 → 录制 → 默认设备是否为 B1

### Q: 自己能听到 MP3 但对方听不到
**A:** 检查 VoiceMeeter 中 Bus[1] (B1) 是否静音（Mute 灯不能亮）

### Q: 播放 MP3 报错
**A:** MP3 解码需要 ffmpeg。安装后确保 `ffmpeg.exe` 在系统 PATH 中，或使用 WAV 格式。

### Q: 热键不生效
**A:** 以管理员身份运行程序（全局热键钩子需要权限）

### Q: 更换耳机/麦克风后还能用吗
**A:** 可以。程序每次启动自动扫描设备，不硬编码设备 ID。

---

## 🛠 开发

```
# 项目结构
voicemeeter-toggle/
├── main.py                      # 入口
├── toggle_app.py                # GUI + 状态机
├── audio_controller.py          # Windows 音频设备控制
├── voicemeeter_controller.py    # VoiceMeeter 路由控制
├── player.py                    # 音频播放器 (sounddevice)
├── device_finder.py             # 设备名称匹配
├── snapshot.py                  # 快照数据类
├── settings.py                  # 全局配置
├── launcher.bat                 # 一键启动脚本
├── build.bat                    # PyInstaller 打包脚本
├── requirements.txt             # Python 依赖
└── README.md                    # 本文件
```

### 打包

```bash
python -m PyInstaller --onefile --windowed --name "VoiceMeeterToggle" ^
    --hidden-import=comtypes.stream ^
    --add-data "settings.py;." ^
    --add-data "snapshot.py;." ^
    main.py
```

---

## 📄 许可

MIT License

---

## 🙏 致谢

- [VB-Audio VoiceMeeter](https://vb-audio.com/Voicemeeter/) — 虚拟音频混音器
- [voicemeeter-api](https://github.com/onyx-and-iris/voicemeeter-api-python) — Python VoiceMeeter Remote API 封装
- [pycaw](https://github.com/AndreMiras/pycaw) — Python Windows Core Audio 封装
- [sounddevice](https://github.com/spatialaudio/python-sounddevice) — Python 音频播放库
