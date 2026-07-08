"""全局常量与配置"""

# VoiceMeeter 版本: 'basic' (Standard), 'banana', 或 'potato'
VOICEMEETER_KIND = "basic"

# VoiceMeeter 可执行文件路径 (用于启动 VoiceMeeter)
VOICEMEETER_EXE = r"C:\Program Files (x86)\VB\Voicemeeter\voicemeeter_x64.exe"

# 快照文件存储路径
SNAPSHOT_FILE = "vm_toggle_snapshot.json"

# 设备名称匹配关键词 (不区分大小写, 所有关键词都必须匹配)
# 注意: 不要匹配到 AUX/VAIO3/In 1-5 等扩展设备
VAIO_PLAYBACK_KEYWORDS = ["VoiceMeeter", "Input"]   # 播放设备: VAIO Input
VAIO_PLAYBACK_EXCLUDE = ["AUX", "VAIO3", "In 1", "In 2", "In 3", "In 4", "In 5"]
VAIO_RECORDING_KEYWORDS = ["VoiceMeeter", "B1"]     # 录音设备: B1 Output

# 路由配置: ON 状态下的目标值
ROUTING_ON = {
    "strip-0": {"B1": True},            # 物理麦 → B1
    "strip-2": {"A1": True, "B1": True}, # VAIO → 音响 + B1
    "bus-1":   {"mute": False},          # B1 不静音
}

# ── Recorder 配置 ──
RECORDER_ROUTING = {
    "Recorder.B1": 1.0,   # Recorder 输出 → B1 虚拟麦 (QQ采集)
    "Recorder.A1": 1.0,   # Recorder 输出 → A1 音响 (自己监听)
}
RECORDER_POLL_INTERVAL = 300  # 轮询播放状态间隔 (ms)
RECORDER_FILE_FILTERS = [
    ("音频文件", "*.mp3 *.wav *.flac *.ogg *.aac *.m4a *.wma"),
    ("MP3 文件", "*.mp3"),
    ("WAV 文件", "*.wav"),
    ("所有文件", "*.*"),
]

# ── 全局热键配置 ──
HOTKEY_PLAY_STOP = "f1+f2"    # 播放/停止切换
HOTKEY_TOGGLE = "f3"          # 开启/关闭功能切换

# ── GUI 配置 ──
WINDOW_TITLE = "VoiceMeeter 一键切换"
WINDOW_SIZE = "380x420"              # 加高以容纳播放器
BUTTON_TEXT_OFF = "已关闭\n点击开启"
BUTTON_TEXT_ON = "工作中\n点击恢复"
BUTTON_TEXT_ERROR = "错误\n点击重试"
PLAY_BUTTON_TEXT = "▶ 播放"
STOP_BUTTON_TEXT = "■ 停止"
