"""全局常量与配置"""

import json
import os
import sys

# VoiceMeeter 版本: 'basic' (Standard), 'banana', 或 'potato'
VOICEMEETER_KIND = "basic"

# VoiceMeeter 可执行文件路径 (用于启动 VoiceMeeter)
VOICEMEETER_EXE = r"C:\Program Files (x86)\VB\Voicemeeter\voicemeeter_x64.exe"

# 快照文件存储路径
SNAPSHOT_FILE = "vm_toggle_snapshot.json"

# 配置文件路径 (与 exe 同目录 或 源码目录)
CONFIG_FILE = "config.json"

# 设备名称匹配关键词 (不区分大小写, 所有关键词都必须匹配)
VAIO_PLAYBACK_KEYWORDS = ["VoiceMeeter", "Input"]
VAIO_PLAYBACK_EXCLUDE = ["AUX", "VAIO3", "In 1", "In 2", "In 3", "In 4", "In 5"]
VAIO_RECORDING_KEYWORDS = ["VoiceMeeter", "B1"]

ROUTING_ON = {
    "strip-0": {"B1": True},
    "strip-2": {"A1": True, "B1": True},
    "bus-1":   {"mute": False},
}

RECORDER_ROUTING = {
    "Recorder.B1": 1.0,
    "Recorder.A1": 1.0,
}
RECORDER_POLL_INTERVAL = 300
RECORDER_FILE_FILTERS = [
    ("音频文件", "*.mp3 *.wav *.flac *.ogg *.aac *.m4a *.wma"),
    ("MP3 文件", "*.mp3"),
    ("WAV 文件", "*.wav"),
    ("所有文件", "*.*"),
]

# ── 默认快捷键 ──
DEFAULT_HOTKEYS = {
    "hotkey_play": "f1+f2",
    "hotkey_toggle": "f3",
}

# ── 配置读写 ──

def _config_path() -> str:
    """获取 config.json 的完整路径 (与可执行文件/脚本同目录)。"""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, CONFIG_FILE)


def load_hotkeys() -> dict:
    """加载用户快捷键配置, 文件不存在则返回默认值。"""
    path = _config_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            # 合并默认值, 确保所有键都存在
            merged = dict(DEFAULT_HOTKEYS)
            merged.update(cfg)
            return merged
        except (json.JSONDecodeError, KeyError):
            pass
    return dict(DEFAULT_HOTKEYS)


def save_hotkeys(hotkeys: dict) -> None:
    """保存快捷键配置到文件。"""
    path = _config_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(hotkeys, f, indent=2, ensure_ascii=False)


# ── 全局热键 (会从 config.json 覆盖) ──
_cfg = load_hotkeys()
HOTKEY_PLAY_STOP = _cfg["hotkey_play"]
HOTKEY_TOGGLE = _cfg["hotkey_toggle"]

# ── GUI 配置 ──
WINDOW_TITLE = "VoiceMeeter 一键切换"
WINDOW_SIZE = "380x440"
BUTTON_TEXT_OFF = "已关闭\n点击开启"
BUTTON_TEXT_ON = "工作中\n点击恢复"
BUTTON_TEXT_ERROR = "错误\n点击重试"
PLAY_BUTTON_TEXT = "▶ 播放"
STOP_BUTTON_TEXT = "■ 停止"
