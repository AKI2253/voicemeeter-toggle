"""VoiceMeeter 路由控制层。

通过 voicemeeter-api (voicemeeterlib) 封装 VoiceMeeter Remote API，
实现对 VoiceMeeter Standard 内部 Strip/Bus 路由的读取、设置和恢复。
"""

from typing import Optional

import voicemeeterlib

from snapshot import VmSnapshot
from settings import VOICEMEETER_KIND, ROUTING_ON, RECORDER_ROUTING


class VmControllerError(Exception):
    """VoiceMeeter 操作错误。"""
    pass


class VoicemeeterController:
    """管理 VoiceMeeter 内部路由状态。"""

    def __init__(self):
        self._vm: Optional[voicemeeterlib.Remote] = None

    # ── 连接生命周期 ──────────────────────────────────────────────────

    def connect(self) -> bool:
        """连接到 VoiceMeeter 引擎。

        Returns:
            True 连接成功, False 表示 VoiceMeeter 未运行或版本不匹配
        """
        try:
            self._vm = voicemeeterlib.api(VOICEMEETER_KIND)
        except voicemeeterlib.error.CAPIError:
            # 某些 VoiceMeeter 版本 GetVoicemeeterVersion 返回 -2
            # 这是已知的非致命问题, 连接仍然可能成功
            pass
        except Exception:
            self._vm = None
            return False

        if self._vm is None:
            return False

        try:
            self._vm.login()
            return True
        except (voicemeeterlib.error.VMRError, OSError, Exception):
            self._vm = None
            return False

    def disconnect(self) -> None:
        """断开与 VoiceMeeter 的连接。"""
        if self._vm is not None:
            try:
                self._vm.logout()
            except Exception:
                pass  # 断开时忽略错误
            self._vm = None

    def is_connected(self) -> bool:
        """检查是否已连接到 VoiceMeeter。"""
        return self._vm is not None

    def _require_connection(self) -> voicemeeterlib.Remote:
        """获取 VM 实例，未连接则抛出异常。"""
        if self._vm is None:
            raise VmControllerError("未连接到 VoiceMeeter，请先调用 connect()")
        return self._vm

    # ── 快照 ──────────────────────────────────────────────────────────

    def capture(self) -> VmSnapshot:
        """读取当前 VoiceMeeter 路由状态。

        Raises:
            VmControllerError: 未连接或读取失败
        """
        vm = self._require_connection()
        try:
            return VmSnapshot(
                strip_0_B1=bool(vm.strip[0].B1),
                strip_1_B1=bool(vm.strip[1].B1),
                strip_2_B1=bool(vm.strip[2].B1),
                strip_2_A1=bool(vm.strip[2].A1),
                strip_2_gain=float(vm.strip[2].gain),
                bus_0_mute=bool(vm.bus[0].mute),
                bus_1_mute=bool(vm.bus[1].mute),
            )
        except Exception as e:
            raise VmControllerError(f"读取 VoiceMeeter 状态失败: {e}") from e

    def restore_snapshot(self, snapshot: VmSnapshot) -> None:
        """恢复 VoiceMeeter 路由到快照中的值。

        使用 vm.apply() 批量设置，避免中间状态。

        Raises:
            VmControllerError: 未连接或恢复失败
        """
        vm = self._require_connection()
        try:
            vm.apply({
                "strip-0": {"B1": snapshot.strip_0_B1},
                "strip-1": {"B1": snapshot.strip_1_B1},
                "strip-2": {
                    "B1": snapshot.strip_2_B1,
                    "A1": snapshot.strip_2_A1,
                    "gain": snapshot.strip_2_gain,
                },
                "bus-0": {"mute": snapshot.bus_0_mute},
                "bus-1": {"mute": snapshot.bus_1_mute},
            })
        except Exception as e:
            raise VmControllerError(f"恢复 VoiceMeeter 状态失败: {e}") from e

    # ── 应用路由 (ON 状态) ───────────────────────────────────────────

    def apply_mp3_to_mic_routing(self) -> None:
        """应用 MP3→麦克风 路由配置。

        设置:
        - Strip[2] (VAIO) → B1=ON, A1=ON (用户可听到 + 传输到虚拟麦)
        - Strip[0] (物理麦) → B1=ON (保留真实麦,可边放歌边说话)
        - Bus[1] (B1) → Mute=OFF (确保虚拟麦输出启用)

        Raises:
            VmControllerError: 未连接或设置失败
        """
        vm = self._require_connection()
        try:
            vm.apply(ROUTING_ON)
        except Exception as e:
            raise VmControllerError(f"应用 MP3-to-Mic 路由失败: {e}") from e

    # ── Recorder (内建播放器) ──────────────────────────────────────────

    def recorder_setup_routing(self) -> None:
        """配置 Recorder 输出到 B1 虚拟麦克风。"""
        vm = self._require_connection()
        try:
            for param, value in RECORDER_ROUTING.items():
                vm.set(param, value)
        except Exception as e:
            raise VmControllerError(f"配置 Recorder 路由失败: {e}") from e

    def recorder_load(self, filepath: str) -> None:
        """加载音频文件到 VoiceMeeter Recorder。

        支持 MP3/WAV/FLAC/OGG 等格式 (取决于 VoiceMeeter 内建解码器)。

        Raises:
            VmControllerError: 加载失败
        """
        vm = self._require_connection()
        try:
            vm.set("Recorder.Load", filepath)
        except Exception as e:
            raise VmControllerError(f"加载音频文件失败: {e}") from e

    def recorder_play(self) -> None:
        """播放 Recorder 中已加载的音频。

        如果 Recorder 已在播放，调用此方法会从头重新开始。
        使用 recorder_stop() 来停止。
        """
        vm = self._require_connection()
        try:
            vm.set("Recorder.Play", 1.0)
        except Exception as e:
            raise VmControllerError(f"播放失败: {e}") from e

    def recorder_stop(self) -> None:
        """停止 Recorder 播放。"""
        vm = self._require_connection()
        try:
            vm.set("Recorder.Play", 0.0)
        except Exception as e:
            raise VmControllerError(f"停止失败: {e}") from e

    def recorder_is_playing(self) -> bool:
        """检查 Recorder 是否正在播放。

        通过读取 Recorder.Play 参数判断 (1.0=播放中, 0.0=已停止)。
        """
        vm = self._require_connection()
        try:
            return bool(vm.get("Recorder.Play"))
        except Exception:
            return False

    # ── 信息查询 ──────────────────────────────────────────────────────

    def get_edition_name(self) -> str:
        """获取 VoiceMeeter 版本名称 (仅调试用)。"""
        vm = self._require_connection()
        try:
            kind_map = {1: "Standard", 2: "Banana", 3: "Potato"}
            kind = vm.kind  # 从 api() 的参数可判断
            return kind_map.get(kind, f"Unknown({kind})")
        except Exception:
            return "Unknown"
