"""设备名称匹配器。

通过关键词子串匹配查找 VoiceMeeter 虚拟音频设备。
兼容中英文 Windows —— VoiceMeeter 的设备名称在不同语言 Windows 上保持一致。
"""

from typing import Optional

# pycaw 类型: 实际是 comtypes 封装的 IMMDevice 对象
# 但我们只使用 .FriendlyName 和 .GetId() 属性，不直接操作 COM
from pycaw.pycaw import AudioUtilities, EDataFlow, DEVICE_STATE
from settings import (
    VAIO_PLAYBACK_KEYWORDS,
    VAIO_PLAYBACK_EXCLUDE,
    VAIO_RECORDING_KEYWORDS,
)


class DeviceFinder:
    """通过名称关键词查找音频设备。"""

    @staticmethod
    def get_all_playback_devices() -> list:
        """返回所有活跃的播放设备列表 (IMMDevice 对象)。"""
        return AudioUtilities.GetAllDevices(
            EDataFlow.eRender.value,
            DEVICE_STATE.ACTIVE.value,
        )

    @staticmethod
    def get_all_recording_devices() -> list:
        """返回所有活跃的录音设备列表 (IMMDevice 对象)。"""
        return AudioUtilities.GetAllDevices(
            EDataFlow.eCapture.value,
            DEVICE_STATE.ACTIVE.value,
        )

    @staticmethod
    def find_device(
        devices: list,
        keywords: list,
        exclude_keywords: list | None = None,
    ) -> Optional[object]:
        """从设备列表中查找第一个匹配所有关键词且不含排除词的设备。

        匹配规则:
        - 不区分大小写
        - FriendlyName 必须包含 keywords 中的每一个子串
        - FriendlyName 不能包含 exclude_keywords 中的任意一个子串
        - 返回 None 表示未找到

        例: keywords=["VoiceMeeter", "Input"], exclude=["AUX", "VAIO3"]
        可匹配 "VoiceMeeter Input (VB-Audio VoiceMeeter VAIO)"
        不会匹配 "VoiceMeeter AUX Input" 或 "VoiceMeeter VAIO3 Input"
        """
        for dev in devices:
            name_lower = dev.FriendlyName.lower()
            # 必须匹配所有 include 关键词
            if not all(kw.lower() in name_lower for kw in keywords):
                continue
            # 不能匹配任何 exclude 关键词
            if exclude_keywords and any(
                kw.lower() in name_lower for kw in exclude_keywords
            ):
                continue
            return dev
        return None

    @classmethod
    def find_vaio_playback(cls) -> Optional[object]:
        """查找 VoiceMeeter VAIO 主播放设备 (Input)。

        排除 AUX、VAIO3 和 VAIO 扩展 (In 1-5)。
        """
        devices = cls.get_all_playback_devices()
        return cls.find_device(
            devices,
            VAIO_PLAYBACK_KEYWORDS,
            VAIO_PLAYBACK_EXCLUDE,
        )

    @classmethod
    def find_vaio_recording(cls) -> Optional[object]:
        """查找 VoiceMeeter B1 录音设备。

        B1 是主虚拟输出总线，设备名包含 "B1"。
        """
        devices = cls.get_all_recording_devices()
        return cls.find_device(devices, VAIO_RECORDING_KEYWORDS)

    @classmethod
    def list_playback_names(cls) -> list:
        """列出所有播放设备名称（调试用）。"""
        return [d.FriendlyName for d in cls.get_all_playback_devices()]

    @classmethod
    def list_recording_names(cls) -> list:
        """列出所有录音设备名称（调试用）。"""
        return [d.FriendlyName for d in cls.get_all_recording_devices()]
