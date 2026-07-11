"""GUI 界面 + 切换状态机 + Recorder 播放控制。

基于 tkinter 的一键切换窗口:
- 灰色按钮 = OFF (原始状态)
- 绿色按钮 = ON (MP3 路由到麦克风)
- 红色按钮 = ERROR (出错状态)

ON 状态下展示 Recorder 播放控制 + 全局热键支持。
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from enum import Enum

from audio_controller import AudioController, AudioControllerError
from voicemeeter_controller import VoicemeeterController, VmControllerError
from player import AudioPlayer, PlayerError
from snapshot import FullSnapshot
from settings import (
    WINDOW_TITLE, WINDOW_SIZE,
    BUTTON_TEXT_OFF, BUTTON_TEXT_ON, BUTTON_TEXT_ERROR,
    PLAY_BUTTON_TEXT, STOP_BUTTON_TEXT,
    SNAPSHOT_FILE, RECORDER_FILE_FILTERS,
    HOTKEY_PLAY_STOP, HOTKEY_TOGGLE, RECORDER_POLL_INTERVAL,
    load_hotkeys, save_hotkeys,
)


class ToggleMode(Enum):
    OFF = "off"
    ON = "on"
    ERROR = "error"


class ToggleApp:
    """VoiceMeeter MP3-to-Mic 一键切换 GUI。"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(False, False)

        # ── 控制器 ──
        self.audio_ctrl = AudioController()
        self.vm_ctrl = VoicemeeterController()
        self.player = AudioPlayer()

        # ── 状态 ──
        self._mode = ToggleMode.OFF
        self._snapshot_path = Path(SNAPSHOT_FILE)
        self._selected_file: str = ""       # 当前选择的音频文件路径
        self._hotkey_available: bool = False  # 全局热键是否可用
        self._poll_id = None                # 轮询 ID
        self._current_hotkeys = load_hotkeys()  # 当前快捷键配置

        # ── UI 变量 ──
        self._file_var = tk.StringVar()
        self._loop_var = tk.BooleanVar(value=False)
        self._auto_stop_var = tk.BooleanVar(value=True)  # 默认开启播完自动停止

        # ── 构建 UI ──
        self._build_ui()

        # ── 启动时检查残留快照 ──
        self._check_residual_snapshot()

        # ── 注册全局热键 ──
        self._setup_hotkeys()

        # ── 关闭窗口时的清理 ──
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI 构建 ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """构建 tkinter 界面。"""
        main_frame = tk.Frame(self.root, padx=20, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── 标题 ──
        tk.Label(
            main_frame,
            text="VoiceMeeter MP3 → 麦克风",
            font=("Microsoft YaHei UI", 12, "bold"),
        ).pack(pady=(0, 5))

        # ── 大按钮 (ON/OFF) ──
        self._btn = tk.Button(
            main_frame,
            text=BUTTON_TEXT_OFF,
            font=("Microsoft YaHei UI", 11),
            width=20, height=3,
            bg="#d9d9d9", fg="#333333",
            activebackground="#c0c0c0",
            relief=tk.RAISED, bd=3,
            command=self._on_toggle_click,
        )
        self._btn.pack(pady=5)

        # ── 状态文字 ──
        self._status_label = tk.Label(
            main_frame,
            text="就绪 — 点击按钮开启",
            font=("Microsoft YaHei UI", 9),
            fg="#666666",
        )
        self._status_label.pack(pady=2)

        # ── 分隔线 ──
        self._separator = tk.Frame(main_frame, height=1, bg="#cccccc")
        self._separator.pack(fill=tk.X, pady=8)

        # ── Recorder 控制区 (初始隐藏) ──
        self._recorder_frame = tk.Frame(main_frame)

        # 文件选择
        file_row = tk.Frame(self._recorder_frame)
        file_row.pack(fill=tk.X, pady=2)
        tk.Label(file_row, text="音频文件:", font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        self._file_entry = tk.Entry(
            file_row, textvariable=self._file_var,
            font=("Microsoft YaHei UI", 8), width=28,
            state="readonly",
        )
        self._file_entry.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
        self._browse_btn = tk.Button(
            file_row, text="浏览...",
            font=("Microsoft YaHei UI", 8),
            command=self._on_browse_file,
        )
        self._browse_btn.pack(side=tk.RIGHT)

        # 播放控制
        btn_row = tk.Frame(self._recorder_frame)
        btn_row.pack(pady=5)

        self._play_btn = tk.Button(
            btn_row, text=PLAY_BUTTON_TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
            width=10, height=1,
            bg="#4caf50", fg="white",
            activebackground="#388e3c",
            command=self._on_play_click,
        )
        self._play_btn.pack(side=tk.LEFT, padx=5)

        self._stop_btn = tk.Button(
            btn_row, text=STOP_BUTTON_TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
            width=10, height=1,
            bg="#f44336", fg="white",
            activebackground="#d32f2f",
            command=self._on_stop_click,
        )
        self._stop_btn.pack(side=tk.LEFT, padx=5)

        # 循环 + 自动停止
        opt_row = tk.Frame(self._recorder_frame)
        opt_row.pack(pady=2)
        self._loop_cb = tk.Checkbutton(
            opt_row, text="循环播放",
            variable=self._loop_var,
            font=("Microsoft YaHei UI", 9),
            command=self._on_loop_toggle,
        )
        self._loop_cb.pack(side=tk.LEFT, padx=5)

        self._auto_stop_cb = tk.Checkbutton(
            opt_row, text="播完自动停止",
            variable=self._auto_stop_var,
            font=("Microsoft YaHei UI", 9),
        )
        self._auto_stop_cb.pack(side=tk.LEFT, padx=10)

        # ── 快捷键提示 (始终可见，放在 Recorder 区域下方) ──
        self._hotkey_label = tk.Label(
            self._recorder_frame,
            text="",
            font=("Microsoft YaHei UI", 8),
            fg="#999999",
        )
        self._hotkey_label.pack(pady=(5, 0), fill=tk.X)

        # ── 全局快捷键提示 (始终可见) ──
        self._global_hotkey_label = tk.Label(
            main_frame,
            text="",
            font=("Microsoft YaHei UI", 9),
            fg="#888888",
        )
        self._global_hotkey_label.pack(pady=(2, 0), fill=tk.X)

        # 快捷键设置按钮 (始终可见)
        self._setting_btn = tk.Button(
            main_frame,
            text="⚙ 快捷键设置",
            font=("Microsoft YaHei UI", 9),
            command=self._open_hotkey_settings,
        )
        self._setting_btn.pack(pady=(4, 0))

        # ── 底部提示 ──
        tk.Label(
            main_frame,
            text="使用前请确保 VoiceMeeter 已运行",
            font=("Microsoft YaHei UI", 7),
            fg="#aaaaaa",
        ).pack(side=tk.BOTTOM, pady=(10, 0))

    # ── Recorder UI 显隐 ──────────────────────────────────────────────

    def _show_recorder(self) -> None:
        """显示 Recorder 控制区。"""
        self._recorder_frame.pack(
            after=self._separator, fill=tk.X, pady=5
        )

    def _hide_recorder(self) -> None:
        """隐藏 Recorder 控制区。"""
        self._recorder_frame.pack_forget()

    def _set_play_state(self, playing: bool) -> None:
        """更新播放按钮状态。"""
        if playing:
            self._play_btn.config(text="⏸ 暂停", bg="#ff9800")
            self._status_label.config(text="▶ Recorder 播放中...", fg="#4caf50")
        else:
            self._play_btn.config(text=PLAY_BUTTON_TEXT, bg="#4caf50")
            self._status_label.config(
                text="✅ MP3 → 麦克风 工作中" if self._mode == ToggleMode.ON
                else self._status_label.cget("text"),
                fg="#333333",
            )

    # ── 文件选择 ──────────────────────────────────────────────────────

    def _on_browse_file(self) -> None:
        """打开文件选择对话框。"""
        path = filedialog.askopenfilename(
            title="选择音频文件",
            filetypes=RECORDER_FILE_FILTERS,
        )
        if path:
            self._selected_file = path
            self._file_var.set(Path(path).name)
            # 预加载到播放器
            try:
                self.player.load(path)
                self._set_status(f"已加载: {Path(path).name}")
            except PlayerError as e:
                self._set_status(f"加载失败: {e}")

    # ── 播放控制 ──────────────────────────────────────────────────────

    def _on_play_click(self) -> None:
        """播放/暂停按钮。"""
        if not self._selected_file:
            self._set_status("请先选择一个音频文件")
            return
        if not self.player.is_available:
            self._set_status("未找到 VoiceMeeter VAIO 设备")
            return

        try:
            if self.player.is_playing:
                # 暂停
                self.player.stop()
                self._set_play_state(False)
                self._stop_polling()
            else:
                # 加载并播放
                self.player.load(self._selected_file)
                self.player.play(on_finished=self._on_playback_finished)
                self._set_play_state(True)
                self._start_polling()
        except PlayerError as e:
            self._set_status(f"播放失败: {e}")
            self._stop_polling()

    def _on_stop_click(self) -> None:
        """停止按钮。"""
        self.player.stop()
        self._set_play_state(False)
        self._stop_polling()

    def _on_loop_toggle(self) -> None:
        """循环播放开关: 播完后自动从头重播。"""
        pass  # 由 _on_playback_finished 处理

    # ── 播放状态轮询 (播完自动停止) ──────────────────────────────────

    def _on_playback_finished(self) -> None:
        """播放结束回调 (在音频线程调用, 需调度到主线程)。"""
        self.root.after(0, self._handle_playback_finished)

    def _handle_playback_finished(self) -> None:
        """主线程处理播放结束。"""
        if self._loop_var.get():
            # 循环播放: 重新加载并播放
            try:
                self.player.load(self._selected_file)
                self.player.play(on_finished=self._on_playback_finished)
                return
            except PlayerError:
                pass
        # 停止或自动停止
        self._stop_polling()
        if self._auto_stop_var.get():
            self._set_play_state(False)
            self._set_status("✅ 播放完毕 — MP3 → 麦克风 工作中")

    def _start_polling(self) -> None:
        """开始轮询播放器状态。"""
        self._stop_polling()  # 先取消旧的
        self._poll_playback()

    def _stop_polling(self) -> None:
        """停止轮询 — 真正取消已排队的回调。"""
        if self._poll_id is not None:
            self.root.after_cancel(self._poll_id)
            self._poll_id = None

    def _poll_playback(self) -> None:
        """轮询检查播放器是否播完。"""
        if not self.player.is_playing:
            return

        # 继续轮询 (作为 on_finished 的兜底, 防止回调丢失)
        self._poll_id = self.root.after(RECORDER_POLL_INTERVAL, self._poll_playback)

    # ── 快捷键设置 ────────────────────────────────────────────────────

    def _open_hotkey_settings(self) -> None:
        """打开快捷键设置弹窗 (非阻塞, 有录入按钮)。"""
        dialog = tk.Toplevel(self.root)
        dialog.title("快捷键设置")
        dialog.geometry("400x270")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 270) // 2
        dialog.geometry(f"+{x}+{y}")

        tk.Label(dialog, text="快捷键设置",
                 font=("Microsoft YaHei UI", 11, "bold")).pack(pady=(15, 8))

        def make_row(label_text, var_name):
            row = tk.Frame(dialog)
            row.pack(pady=5, fill=tk.X, padx=25)
            tk.Label(row, text=label_text, font=("Microsoft YaHei UI", 10),
                     width=10, anchor="e").pack(side=tk.LEFT)

            display_var = tk.StringVar(value=self._current_hotkeys[var_name])
            entry = tk.Entry(row, textvariable=display_var,
                             font=("Consolas", 11, "bold"),
                             width=16, justify="center", state="readonly",
                             readonlybackground="white")
            entry.pack(side=tk.LEFT, padx=8)

            btn_text = tk.StringVar(value="开始录入")
            btn = tk.Button(row, textvariable=btn_text,
                            font=("Microsoft YaHei UI", 8),
                            width=9,
                            command=lambda dv=display_var, bt=btn_text, dl=dialog:
                            self._capture_hotkey(dv, bt, dl))
            btn.pack(side=tk.LEFT)

            return display_var, btn_text

        play_var, play_btn_text = make_row("播放/停止:", "hotkey_play")
        toggle_var, toggle_btn_text = make_row("开关功能:", "hotkey_toggle")

        tk.Label(dialog, text="点击「开始录入」后按下组合键，松手自动完成",
                 font=("Microsoft YaHei UI", 8), fg="#999999").pack(pady=(8, 0))

        status_var = tk.StringVar()
        tk.Label(dialog, textvariable=status_var,
                 font=("Microsoft YaHei UI", 8), fg="#999999").pack(pady=(2, 5))

        def on_save():
            new_hotkeys = {
                "hotkey_play": play_var.get().strip(),
                "hotkey_toggle": toggle_var.get().strip(),
            }
            if not new_hotkeys["hotkey_play"] or not new_hotkeys["hotkey_toggle"]:
                status_var.set("快捷键不能为空！")
                return
            save_hotkeys(new_hotkeys)
            self._current_hotkeys = new_hotkeys
            self._reregister_hotkeys()
            status_var.set("已保存！")
            dialog.after(800, dialog.destroy)

        tk.Button(dialog, text="保存", font=("Microsoft YaHei UI", 10),
                  width=10, command=on_save,
                  bg="#4caf50", fg="white").pack(pady=(8, 0))

    def _capture_hotkey(self, var: tk.StringVar, btn_text: tk.StringVar,
                        dialog: tk.Toplevel) -> None:
        """非阻塞按键捕获: hook 监听 + 实时显示, 松手自动完成。"""
        import keyboard
        import ctypes

        pressed = set()
        original_value = var.get()

        # 切英文键盘, 防止输入法拦截
        try:
            user32 = ctypes.windll.user32
            hkl_en = user32.LoadKeyboardLayoutW("00000409", 1)
            self._ime_layout = user32.GetKeyboardLayout(0)
            user32.ActivateKeyboardLayout(hkl_en, 0)
        except Exception:
            self._ime_layout = None

        def on_key(e):
            if e.event_type == "down":
                name = e.name.lower() if e.name else e.scan_code
                # 规范化键名
                if name in ("left shift", "shift"): name = "shift"
                elif name in ("left ctrl", "ctrl"): name = "ctrl"
                elif name in ("left alt", "alt"): name = "alt"
                elif name in ("left windows", "right windows"): name = "windows"
                pressed.add(name)
                combo = "+".join(sorted(pressed))
                var.set(combo)
            elif e.event_type == "up":
                # 松手: 所有键都松开了 → 完成
                pass

        # 先用一个小延迟确保之前的状态清掉
        dialog.after(100, lambda: _start_capture())

        def _start_capture():
            btn_text.set("录入中...")
            var.set("按下组合键...")
            pressed.clear()
            keyboard.hook(on_key)

            def check_done():
                # 检查是否所有键都松开了 (通过持续监控)
                # 简化: 用 keyboard 的 unhook + 一个短暂等待
                pass

            # 实际: 监听直到所有按下键释放
            def on_key_full(e):
                if e.event_type == "down":
                    name = e.name.lower() if e.name else str(e.scan_code)
                    if name in ("left shift", "shift"): name = "shift"
                    elif name in ("left ctrl", "ctrl"): name = "ctrl"
                    elif name in ("left alt", "alt"): name = "alt"
                    elif name in ("left windows", "right windows"): name = "windows"
                    pressed.add(name)
                    combo = "+".join(sorted(pressed))
                    var.set(combo)
                elif e.event_type == "up":
                    # 短暂延迟后检查是否全部松开
                    name = e.name.lower() if e.name else str(e.scan_code)
                    if name in ("left shift", "shift"): name = "shift"
                    elif name in ("left ctrl", "ctrl"): name = "ctrl"
                    elif name in ("left alt", "alt"): name = "alt"
                    elif name in ("left windows", "right windows"): name = "windows"
                    pressed.discard(name)
                    if not pressed:
                        # 全部松开 → 完成录入
                        keyboard.unhook_all()
                        btn_text.set("开始录入")
                        # 恢复输入法
                        self._restore_ime()
                        # 验证: 至少有一个非修饰键
                        combo = var.get()
                        if not combo or combo == "按下组合键...":
                            var.set(original_value)
                        return

            keyboard.unhook_all()
            keyboard.hook(on_key_full)

    def _restore_ime(self) -> None:
        """恢复原始输入法布局。"""
        if getattr(self, '_ime_layout', None):
            try:
                ctypes.windll.user32.ActivateKeyboardLayout(self._ime_layout, 0)
            except Exception:
                pass
            self._ime_layout = None

    def _reregister_hotkeys(self) -> None:
        """取消旧热键, 用新配置重新注册。"""
        import keyboard
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self._setup_hotkeys()

    def _setup_hotkeys(self) -> None:
        """注册全局热键 (使用当前配置的值)。"""
        try:
            import keyboard
            play_key = self._current_hotkeys.get("hotkey_play", "f1+f2")
            toggle_key = self._current_hotkeys.get("hotkey_toggle", "f3")
            keyboard.add_hotkey(play_key, self._on_play_hotkey)
            keyboard.add_hotkey(toggle_key, self._on_toggle_hotkey)
            self._hotkey_available = True
            self._hotkey_label.config(text=f"热键: {play_key} 播放/停止")
            self._global_hotkey_label.config(
                text=f"全局热键: {toggle_key} 开启/关闭功能"
            )
        except ImportError:
            self._hotkey_available = False
        except Exception:
            self._hotkey_available = False

    # ── 全局热键回调 ──────────────────────────────────────────────────

    def _on_play_hotkey(self) -> None:
        """F1+F2 触发的播放/停止切换。"""
        if self._mode != ToggleMode.ON:
            return
        self.root.after(0, self._hotkey_action)

    def _on_toggle_hotkey(self) -> None:
        """F3 触发的开启/关闭功能切换。"""
        self.root.after(0, self._on_toggle_click)

    def _hotkey_action(self) -> None:
        """在主线程中执行热键动作 (播放/停止切换)。"""
        if self.player.is_playing:
            self.player.stop()
            self._set_play_state(False)
            self._stop_polling()
        else:
            self._on_play_click()

    # ── 切换逻辑 ──────────────────────────────────────────────────────

    def _on_toggle_click(self) -> None:
        """按钮点击 → 根据当前模式分派。"""
        if self._mode == ToggleMode.OFF:
            self._toggle_on()
        elif self._mode == ToggleMode.ON:
            self._toggle_off()
        elif self._mode == ToggleMode.ERROR:
            self._reset_to_off()

    # ── OFF → ON ──────────────────────────────────────────────────────

    def _toggle_on(self) -> None:
        """执行 OFF → ON 切换。"""
        self._set_ui_state("正在连接 VoiceMeeter...")

        # 1. 连接 VoiceMeeter
        if not self.vm_ctrl.connect():
            self._set_error("VoiceMeeter 未运行！请先启动 VoiceMeeter")
            return

        # 2. 快照当前状态
        try:
            vm_snapshot = self.vm_ctrl.capture()
            windows_snapshot = self.audio_ctrl.capture()
        except (VmControllerError, AudioControllerError) as e:
            self._set_error(f"获取状态失败:\n{e}")
            self.vm_ctrl.disconnect()
            return

        full_snapshot = FullSnapshot(vm=vm_snapshot, windows=windows_snapshot)
        full_snapshot.save_to_file(self._snapshot_path)

        # 3. 应用路由: 先 VM Strip/Bus, 然后 Recorder, 最后 Windows
        try:
            self.vm_ctrl.apply_mp3_to_mic_routing()
        except VmControllerError as e:
            self._set_error(f"VM 路由设置失败:\n{e}")
            self._rollback(full_snapshot)
            return

        # 4. Windows 设备切换 (只切录音设备，不切播放设备)
        #    播放设备不动 = 耳机正常监听
        #    录音设备切 B1 = QQ/微信从虚拟麦采集
        recording_ok = self.audio_ctrl.set_recording_to_b1()

        if not recording_ok:
            self._set_error(
                "未找到录音设备 (VoiceMeeter Out B1)\n"
                "请确认 VoiceMeeter 音频驱动已安装"
            )
            self._rollback(full_snapshot)
            return

        # 5. 成功 — 进入 ON 状态
        self._mode = ToggleMode.ON
        self._set_button(BUTTON_TEXT_ON, "#4caf50", "#ffffff")
        self._set_status("✅ MP3 → 麦克风 工作中")
        self._show_recorder()

        # 如果有之前选择的文件, 重新加载
        if self._selected_file:
            try:
                self.player.load(self._selected_file)
            except PlayerError:
                pass

    # ── ON → OFF ──────────────────────────────────────────────────────

    def _toggle_off(self) -> None:
        """执行 ON → OFF 恢复。"""
        # 停止播放器 + 轮询
        self._stop_polling()
        self.player.stop()
        self._set_play_state(False)

        full_snapshot = FullSnapshot.load_from_file(self._snapshot_path)

        if full_snapshot is None:
            self._set_error("未找到快照文件！\n请手动恢复音频设置")
            return

        errors = []

        # 1. 先恢复 Windows 默认设备
        try:
            self.audio_ctrl.restore_snapshot(full_snapshot.windows)
        except AudioControllerError as e:
            errors.append(f"Windows 设备: {e}")

        # 2. 再恢复 VoiceMeeter 路由
        try:
            self.vm_ctrl.restore_snapshot(full_snapshot.vm)
        except VmControllerError as e:
            errors.append(f"VoiceMeeter: {e}")

        # 3. 清理
        self._snapshot_path.unlink(missing_ok=True)
        self.vm_ctrl.disconnect()

        if errors:
            self._set_error("部分恢复失败:\n" + "\n".join(errors))
            return

        # 4. 成功 → 回到 OFF
        self._mode = ToggleMode.OFF
        self._set_button(BUTTON_TEXT_OFF, "#d9d9d9", "#333333")
        self._set_status("✅ 已恢复原始音频设置")
        self._hide_recorder()

    # ── 回滚 & 重置 ───────────────────────────────────────────────────

    def _rollback(self, snapshot: FullSnapshot) -> None:
        """切换失败时回滚。"""
        try:
            self.audio_ctrl.restore_snapshot(snapshot.windows)
        except AudioControllerError:
            pass
        try:
            self.vm_ctrl.restore_snapshot(snapshot.vm)
        except VmControllerError:
            pass
        self.vm_ctrl.disconnect()
        self._snapshot_path.unlink(missing_ok=True)

    def _reset_to_off(self) -> None:
        """从 ERROR 状态重置到 OFF。"""
        self._toggle_off()
        if self._mode != ToggleMode.ERROR:
            return
        self._mode = ToggleMode.OFF
        self._set_button(BUTTON_TEXT_OFF, "#d9d9d9", "#333333")
        self._set_status("就绪 — 点击按钮开启")
        self._hide_recorder()
        self.vm_ctrl.disconnect()

    # ── 残留快照检查 ─────────────────────────────────────────────────

    def _check_residual_snapshot(self) -> None:
        """检查磁盘上是否有上次未正常恢复的快照。"""
        if self._snapshot_path.exists():
            self._set_status("⚠ 检测到未恢复的快照 — 点击按钮可恢复")

    # ── UI 辅助 ───────────────────────────────────────────────────────

    def _set_button(self, text: str, bg: str, fg: str) -> None:
        self._btn.config(text=text, bg=bg, fg=fg, activebackground=bg)

    def _set_status(self, text: str) -> None:
        fg = "#333333"
        if "✅" in text:
            fg = "#4caf50"
        elif "⚠" in text:
            fg = "#ff9800"
        self._status_label.config(text=text, fg=fg)

    def _set_error(self, text: str) -> None:
        self._mode = ToggleMode.ERROR
        self._set_button(BUTTON_TEXT_ERROR, "#f44336", "#ffffff")
        self._status_label.config(text=text, fg="#d32f2f")

    def _set_ui_state(self, text: str) -> None:
        """临时显示过渡状态。"""
        self._status_label.config(text=text, fg="#999999")
        self.root.update_idletasks()

    # ── 关闭 ──────────────────────────────────────────────────────────

    def _on_close(self) -> None:
        """窗口关闭: 防呆确认 + 清理资源。"""
        # 防呆: ON 状态下关闭时弹出确认对话框
        if self._mode == ToggleMode.ON:
            result = messagebox.askyesnocancel(
                "确认关闭",
                "功能仍在运行中（麦克风已切换到虚拟设备）\n\n"
                "「是」= 恢复原始设置并关闭\n"
                "「否」= 直接关闭（不恢复设置）\n"
                "「取消」= 不关闭程序",
                parent=self.root,
            )
            if result is None:  # 取消
                return
            if result:  # 是 — 恢复并关闭
                self._toggle_off()

        self.player.stop()
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        self.vm_ctrl.disconnect()
        self.root.destroy()

    # ── 启动 ──────────────────────────────────────────────────────────

    def run(self) -> None:
        """启动 GUI 主循环。"""
        self.root.mainloop()
