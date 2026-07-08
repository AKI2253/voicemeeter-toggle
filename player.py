"""音频播放器模块。

使用 sounddevice 直接将音频播放到 VoiceMeeter VAIO Input 设备，
不改变 Windows 默认播放设备（耳机/音响不受影响）。

音频流向:
  Python sounddevice → "VoiceMeeter Input (VAIO)" → VoiceMeeter Strip[2]
    → B1 (虚拟麦, QQ 采集)
    → A1 (物理输出, 用户监听)

支持格式: WAV/FLAC/OGG (原生), MP3 (需 ffmpeg)
"""

import threading
from pathlib import Path
from typing import Optional, Callable

import numpy as np
import sounddevice as sd


class PlayerError(Exception):
    """播放器错误。"""
    pass


class AudioPlayer:
    """音频播放器 —— 输出到 VoiceMeeter VAIO 虚拟输入。"""

    def __init__(self):
        self._stream: Optional[sd.OutputStream] = None
        self._vaio_device: Optional[int] = None
        self._is_playing: bool = False
        self._audio_data: Optional[np.ndarray] = None
        self._sample_rate: int = 44100
        self._position: int = 0
        self._on_finished: Optional[Callable[[], None]] = None

        # 查找 VAIO 设备
        self._find_vaio_device()

    def _find_vaio_device(self) -> None:
        """查找 VoiceMeeter VAIO Input 播放设备。"""
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if d["max_output_channels"] <= 0:
                continue
            name = d["name"]
            # 匹配主 VAIO Input, 排除 AUX/VAIO3/In 1-5
            if ("Voicemeeter" in name and "Input" in name
                    and "VAIO" in name
                    and "AUX" not in name
                    and "VAIO3" not in name
                    and "In " not in name.split("(")[0]):
                self._vaio_device = i
                return

        # 降级: 接受任何含 VoiceMeeter + Input 的设备
        for i, d in enumerate(devices):
            if d["max_output_channels"] <= 0:
                continue
            name = d["name"]
            if "Voicemeeter" in name and "Input" in name:
                self._vaio_device = i
                return

    @property
    def is_available(self) -> bool:
        """VAIO 设备是否可用。"""
        return self._vaio_device is not None

    @property
    def is_playing(self) -> bool:
        """是否正在播放。"""
        return self._is_playing

    def load(self, filepath: str) -> None:
        """加载音频文件。

        支持 WAV/FLAC/OGG (soundfile) 和 MP3 (pydub + ffmpeg)。

        Raises:
            PlayerError: 加载失败
        """
        path = Path(filepath)
        if not path.exists():
            raise PlayerError(f"文件不存在: {filepath}")

        suffix = path.suffix.lower()

        try:
            if suffix in (".wav", ".flac", ".ogg"):
                import soundfile as sf
                self._audio_data, self._sample_rate = sf.read(filepath, dtype="float32")
            elif suffix in (".mp3", ".m4a", ".aac", ".wma"):
                self._load_with_pydub(filepath)
            else:
                # 尝试 soundfile 兜底
                import soundfile as sf
                self._audio_data, self._sample_rate = sf.read(filepath, dtype="float32")
        except Exception as e:
            raise PlayerError(f"加载音频失败: {e}") from e

        # 转单声道 (VoiceMeeter VAIO 支持多声道，但保险起见统一转)
        if self._audio_data.ndim > 1:
            self._audio_data = self._audio_data.mean(axis=1).astype(np.float32)

        self._position = 0

    def _load_with_pydub(self, filepath: str) -> None:
        """使用 pydub 加载 MP3 等格式 (需要 ffmpeg)。"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(filepath)
            self._sample_rate = audio.frame_rate
            # 转单声道
            if audio.channels > 1:
                audio = audio.set_channels(1)
            # 转 numpy float32
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples /= np.iinfo(audio.array_type).max
            self._audio_data = samples
        except FileNotFoundError:
            raise PlayerError(
                "播放 MP3 需要 ffmpeg。\n"
                "请安装 ffmpeg 并添加到 PATH，\n"
                "或使用 WAV/FLAC 格式。\n"
                "下载: https://ffmpeg.org/download.html"
            )
        except Exception as e:
            raise PlayerError(f"MP3 解码失败: {e}") from e

    def play(self, on_finished: Optional[Callable[[], None]] = None) -> None:
        """开始播放。

        Args:
            on_finished: 播放完毕回调 (在音频线程中调用)
        """
        if self._audio_data is None:
            raise PlayerError("没有加载音频文件，请先调用 load()")
        if self._vaio_device is None:
            raise PlayerError("未找到 VoiceMeeter VAIO 设备")

        self._on_finished = on_finished
        self._position = 0
        self._is_playing = True

        # 在后台线程中播放 (避免阻塞 GUI)
        thread = threading.Thread(target=self._play_thread, daemon=True)
        thread.start()

    def _play_thread(self) -> None:
        """后台播放线程。"""
        try:
            remaining = self._audio_data[self._position:]

            # 确保采样率匹配 VAIO 设备
            try:
                device_info = sd.query_devices(self._vaio_device)
                device_sr = int(device_info.get("default_samplerate", self._sample_rate))
            except Exception:
                device_sr = self._sample_rate

            sd.play(
                remaining,
                samplerate=self._sample_rate,
                device=self._vaio_device,
                blocking=True,
            )
        except Exception:
            pass  # 播放错误不崩溃
        finally:
            self._audio_data = None  # 释放内存
            self._position = 0
            self._is_playing = False
            if self._on_finished:
                try:
                    self._on_finished()
                except Exception:
                    pass

    def stop(self) -> None:
        """停止播放。"""
        try:
            sd.stop()
        except Exception:
            pass
        self._is_playing = False
        self._position = 0
