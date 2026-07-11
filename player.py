"""音频播放器模块。

使用 sounddevice 直接将音频播放到 VoiceMeeter VAIO Input 设备。

线程安全: Lock 保护可变状态, 避免 sd.stop() 跨线程调用导致 PortAudio 崩溃。
停止策略: 不跨线程 sd.stop(), 而是在播放线程内检测停止信号。
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
        self._vaio_device: Optional[int] = None
        self._audio_data: Optional[np.ndarray] = None
        self._sample_rate: int = 44100
        self._is_playing: bool = False
        self._on_finished: Optional[Callable[[], None]] = None

        self._lock = threading.Lock()
        self._stop_requested = threading.Event()

        self._find_vaio_device()

    def _find_vaio_device(self) -> None:
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if d["max_output_channels"] <= 0:
                continue
            name = d["name"]
            if ("Voicemeeter" in name and "Input" in name
                    and "VAIO" in name
                    and "AUX" not in name
                    and "VAIO3" not in name
                    and "In " not in name.split("(")[0]):
                self._vaio_device = i
                return
        for i, d in enumerate(devices):
            if d["max_output_channels"] <= 0:
                continue
            if "Voicemeeter" in name and "Input" in name:
                self._vaio_device = i
                return

    @property
    def is_available(self) -> bool:
        return self._vaio_device is not None

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return self._is_playing

    def load(self, filepath: str) -> None:
        path = Path(filepath)
        if not path.exists():
            raise PlayerError(f"文件不存在: {filepath}")

        suffix = path.suffix.lower()
        try:
            if suffix in (".wav", ".flac", ".ogg"):
                import soundfile as sf
                data, sr = sf.read(filepath, dtype="float32")
            elif suffix in (".mp3", ".m4a", ".aac", ".wma"):
                data, sr = self._load_with_pydub(filepath)
            else:
                import soundfile as sf
                data, sr = sf.read(filepath, dtype="float32")
        except Exception as e:
            raise PlayerError(f"加载音频失败: {e}") from e

        if data.ndim > 1:
            data = data.mean(axis=1).astype(np.float32)

        with self._lock:
            self._audio_data = data
            self._sample_rate = sr

    def _load_with_pydub(self, filepath: str):
        try:
            # 屏蔽 ffmpeg 命令行窗口, 防止弹窗打断 QQ 录音
            import subprocess as _sp
            _orig = _sp.Popen
            _no_win = 0x08000000
            _sp.Popen = lambda *a, **kw: _orig(*a, **{**kw, 'creationflags': kw.get('creationflags', 0) | _no_win})
            from pydub import AudioSegment
            audio = AudioSegment.from_file(filepath)
            _sp.Popen = _orig
            sr = audio.frame_rate
            if audio.channels > 1:
                audio = audio.set_channels(1)
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples /= np.iinfo(audio.array_type).max
            return samples, sr
        except FileNotFoundError:
            raise PlayerError(
                "播放 MP3 需要 ffmpeg。\n"
                "请安装 ffmpeg 并添加到 PATH，\n"
                "或使用 WAV/FLAC 格式。"
            )

    def play(self, on_finished: Optional[Callable[[], None]] = None) -> None:
        """开始播放。"""
        with self._lock:
            if self._audio_data is None:
                raise PlayerError("没有加载音频文件")
            self._is_playing = True
            self._on_finished = on_finished
            self._stop_requested.clear()

        thread = threading.Thread(target=self._play_thread, daemon=True)
        thread.start()

    def _play_thread(self) -> None:
        """使用 OutputStream + callback 播放 (可在回调中安全终止)。"""
        data = None
        sr = 44100
        device = None

        with self._lock:
            if self._audio_data is not None:
                data = self._audio_data.copy()  # 拷贝, 避免主线程 load() 修改
                sr = self._sample_rate
            device = self._vaio_device

        if data is None or device is None:
            with self._lock:
                self._is_playing = False
            return

        position = [0]  # 用列表在闭包中修改

        def callback(outdata, frames, time_info, status):
            if status:
                return
            if self._stop_requested.is_set():
                raise sd.CallbackStop()

            remaining = len(data) - position[0]
            if remaining <= 0:
                raise sd.CallbackStop()

            chunk = min(frames, remaining)
            outdata[:chunk, 0] = data[position[0]:position[0] + chunk]
            if chunk < frames:
                outdata[chunk:, 0] = 0
            position[0] += chunk

        try:
            stream = sd.OutputStream(
                samplerate=sr,
                device=device,
                channels=1,
                callback=callback,
            )
            with stream:
                while stream.active:
                    sd.sleep(100)
        except sd.CallbackStop:
            pass
        except Exception:
            pass
        finally:
            stopped_by_user = self._stop_requested.is_set()
            with self._lock:
                self._is_playing = False
                cb = self._on_finished
                self._on_finished = None
            # 自然播完才触发回调; 被 stop 中断则跳过
            if cb and not stopped_by_user:
                try:
                    cb()
                except Exception:
                    pass

    def stop(self) -> None:
        """请求停止 — 线程安全, 不跨线程调 sd.stop()。"""
        self._stop_requested.set()
        with self._lock:
            self._is_playing = False
