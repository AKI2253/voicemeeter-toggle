"""Windows 默认音频设备控制层。

通过 pycaw 内置的 AudioUtilities.SetDefaultDevice() 接口，
实现对 Windows 默认播放/录音设备的保存、切换和恢复。

注意: 切换默认音频设备需要管理员权限。
"""

from pycaw.pycaw import AudioUtilities, ERole

from snapshot import WindowsDeviceSnapshot
from device_finder import DeviceFinder


class AudioControllerError(Exception):
    """Windows 音频设备操作错误。"""
    pass


class AudioController:
    """管理 Windows 默认音频设备的保存、切换和恢复。"""

    # 设置默认设备时为所有三个角色设置
    _ALL_ROLES = [ERole.eConsole, ERole.eMultimedia, ERole.eCommunications]

    # ── 快照 ──────────────────────────────────────────────────────────

    @staticmethod
    def capture() -> WindowsDeviceSnapshot:
        """读取当前默认播放和录音设备 ID。

        GetSpeakers/GetMicrophone 可能返回 AudioDevice (.id 属性)
        或 POINTER(IMMDevice) (.GetId() 方法)。

        Raises:
            AudioControllerError: 无法获取当前默认设备
        """
        try:
            playback = AudioUtilities.GetSpeakers()
            recording = AudioUtilities.GetMicrophone()
            return WindowsDeviceSnapshot(
                playback_device_id=AudioController._get_device_id(playback),
                recording_device_id=AudioController._get_device_id(recording),
            )
        except Exception as e:
            raise AudioControllerError(f"无法获取当前默认音频设备: {e}") from e

    # ── 应用切换 ──────────────────────────────────────────────────────

    @staticmethod
    def set_playback_to_vaio() -> bool:
        """将 Windows 默认播放设备设为 VoiceMeeter VAIO Input。

        Returns:
            True 成功, False 表示未找到 VAIO 设备
        """
        dev = DeviceFinder.find_vaio_playback()
        if dev is None:
            return False
        AudioController._set_default(dev.id)
        return True

    @staticmethod
    def set_recording_to_b1() -> bool:
        """将 Windows 默认录音设备设为 VoiceMeeter B1 Output。

        Returns:
            True 成功, False 表示未找到 B1 设备
        """
        dev = DeviceFinder.find_vaio_recording()
        if dev is None:
            return False
        AudioController._set_default(dev.id)
        return True

    @staticmethod
    def restore_snapshot(snapshot: WindowsDeviceSnapshot) -> None:
        """恢复 Windows 默认设备到快照中的值。

        同时设置 eConsole、eMultimedia、eCommunications 三个角色。

        Raises:
            AudioControllerError: 恢复失败
        """
        try:
            AudioController._set_default(snapshot.playback_device_id)
            AudioController._set_default(snapshot.recording_device_id)
        except Exception as e:
            raise AudioControllerError(f"恢复默认设备失败: {e}") from e

    # ── 底层调用 ─────────────────────────────────────────────────────

    @staticmethod
    def _get_device_id(dev) -> str:
        """从 AudioDevice 或 POINTER(IMMDevice) 提取设备 ID。

        pycaw 的 GetSpeakers() 返回 AudioDevice (.id 属性),
        但 GetMicrophone() 可能返回裸 POINTER(IMMDevice) (.GetId() 方法)。
        """
        if hasattr(dev, "id"):
            return dev.id
        if hasattr(dev, "GetId"):
            return dev.GetId()
        raise AudioControllerError(f"无法从 {type(dev).__name__} 获取设备 ID")

    @staticmethod
    def _set_default(device_id: str) -> None:
        """使用 pycaw 内置方法设置默认音频设备。

        该方法内部正确处理 IPolicyConfig COM 接口，
        比手写 COM vtable 更可靠。
        """
        try:
            AudioUtilities.SetDefaultDevice(device_id, roles=AudioController._ALL_ROLES)
        except Exception as e:
            raise AudioControllerError(f"设置默认设备失败 (需要管理员权限): {e}") from e
