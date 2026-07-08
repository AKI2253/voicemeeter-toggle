"""快照数据类 — 纯数据，无逻辑。

用于在切换前后保存/恢复 Windows 音频设备和 VoiceMeeter 内部路由状态。
"""

from dataclasses import dataclass, asdict
from datetime import datetime
import json
from pathlib import Path


@dataclass
class VmSnapshot:
    """VoiceMeeter 内部路由快照。

    保存 VoiceMeeter Standard 的关键 Strip/Bus 状态。
    仅保存会被切换操作改变的参数，不保存全部。
    """
    strip_0_B1: bool       # 物理麦克风 → B1
    strip_1_B1: bool       # HW Input 2 → B1
    strip_2_B1: bool       # VAIO → B1 (核心路由)
    strip_2_A1: bool       # VAIO → 音响
    strip_2_gain: float    # VAIO 增益 (-60.0 ~ +12.0 dB)
    bus_0_mute: bool       # A1 静音
    bus_1_mute: bool       # B1 静音


@dataclass
class WindowsDeviceSnapshot:
    """Windows 默认音频设备快照。

    保存设备 ID 字符串，用于恢复时通过 IPolicyConfig 设置回去。
    """
    playback_device_id: str      # 默认播放设备 ID
    recording_device_id: str     # 默认录音设备 ID


@dataclass
class FullSnapshot:
    """完整快照 = VM 路由 + Windows 设备。"""
    vm: VmSnapshot
    windows: WindowsDeviceSnapshot
    timestamp: str = ""    # ISO 时间戳，调试用

    def to_json(self) -> str:
        """序列化为 JSON 字符串。"""
        data = {
            "vm": asdict(self.vm),
            "windows": asdict(self.windows),
            "timestamp": self.timestamp or datetime.now().isoformat(),
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "FullSnapshot":
        """从 JSON 字符串反序列化。"""
        data = json.loads(json_str)
        return cls(
            vm=VmSnapshot(**data["vm"]),
            windows=WindowsDeviceSnapshot(**data["windows"]),
            timestamp=data.get("timestamp", ""),
        )

    def save_to_file(self, path: Path) -> None:
        """保存快照到磁盘文件。"""
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load_from_file(cls, path: Path) -> "FullSnapshot | None":
        """从磁盘文件加载快照。文件不存在或损坏返回 None。"""
        try:
            if not path.exists():
                return None
            return cls.from_json(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError, TypeError):
            return None
