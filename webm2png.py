# -*- coding: utf-8 -*-
"""
webm_to_png_gui.py
- webm -> png序列（ffmpeg）
- GUI（tkinter）+ 进度条（ffprobe + ffmpeg -progress）+ 编码安全日志
"""

import os
import shlex
import threading
import queue
import subprocess
import re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


def is_ffmpeg_available() -> bool:
    try:
        p = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return p.returncode == 0
    except Exception:
        return False


def is_ffprobe_available() -> bool:
    try:
        p = subprocess.run(["ffprobe", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return p.returncode == 0
    except Exception:
        return False


def probe_duration_seconds(input_file: Path) -> float | None:
    """返回视频总时长（秒），失败返回 None"""
    if not is_ffprobe_available():
        return None
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(input_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        out = (p.stdout or b"").decode("utf-8", errors="replace").strip()
        if p.returncode != 0 or not out:
            return None
        dur = float(out)
        if dur <= 0:
            return None
        return dur
    except Exception:
        return None


def normalize_hex_color(s: str) -> str:
    s = s.strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 3:
        s = "".join([c * 2 for c in s])
    if len(s) != 6 or any(c not in "0123456789abcdef" for c in s):
        raise ValueError("颜色必须是 6 位十六进制（如 000000 或 #000000）")
    return s


def build_ffmpeg_cmd(
    input_file: Path,
    out_dir: Path,
    pattern: str,
    width: int,
    height: int,
    fps: float,
    colorkey_hex: str,
    similarity: float,
    blend: float,
    overwrite: bool,
    extra_args: str,
    enable_progress: bool = True
):
    vf = (
        f"scale={width}:{height}:flags=lanczos,"
        f"fps={fps},"
        f"colorkey=0x{colorkey_hex}:{similarity}:{blend},"
        f"format=rgba"
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_pattern = str(out_dir / pattern)

    cmd = ["ffmpeg", "-hide_banner"]
    cmd += ["-y"] if overwrite else ["-n"]
    cmd += ["-i", str(input_file)]
    cmd += ["-vf", vf]

    # 进度输出到 stdout：key=value（out_time_ms / progress=continue|end）
    if enable_progress:
        cmd += ["-progress", "pipe:1", "-nostats"]

    if extra_args.strip():
        cmd += shlex.split(extra_args, posix=os.name != "nt")

    cmd += [out_pattern]
    return cmd


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WEBM → PNG 帧导出（ffmpeg）")
        self.geometry("900x600")

        self.proc = None
        self.worker_thread = None
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()

        self.duration_sec: float | None = None
        self._build_ui()
        self.after(80, self._poll_queue)

        if not is_ffmpeg_available():
            messagebox.showwarning(
                "未检测到 ffmpeg",
                "没有检测到可用的 ffmpeg。\n\n请先安装 ffmpeg，并确保命令行能运行：ffmpeg -version"
            )

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True)

        io_box = ttk.LabelFrame(frm, text="输入 / 输出")
        io_box.pack(fill="x", **pad)

        self.in_var = tk.StringVar()
        self.out_var = tk.StringVar(value=str(Path.cwd() / "out"))
        self.pattern_var = tk.StringVar(value="frame_%05d.png")

        r = 0
        ttk.Label(io_box, text="输入 WEBM：").grid(row=r, column=0, sticky="w", **pad)
        ttk.Entry(io_box, textvariable=self.in_var).grid(row=r, column=1, sticky="ew", **pad)
        ttk.Button(io_box, text="浏览…", command=self._pick_input).grid(row=r, column=2, **pad)

        r += 1
        ttk.Label(io_box, text="输出文件夹：").grid(row=r, column=0, sticky="w", **pad)
        ttk.Entry(io_box, textvariable=self.out_var).grid(row=r, column=1, sticky="ew", **pad)
        ttk.Button(io_box, text="选择…", command=self._pick_output_dir).grid(row=r, column=2, **pad)

        r += 1
        ttk.Label(io_box, text="文件名模板：").grid(row=r, column=0, sticky="w", **pad)
        ttk.Entry(io_box, textvariable=self.pattern_var).grid(row=r, column=1, sticky="ew", **pad)
        ttk.Label(io_box, text="（需包含 %d，如 frame_%05d.png）").grid(row=r, column=2, sticky="w", **pad)

        io_box.columnconfigure(1, weight=1)

        param_box = ttk.LabelFrame(frm, text="滤镜参数（-vf）")
        param_box.pack(fill="x", **pad)

        self.w_var = tk.IntVar(value=300)
        self.h_var = tk.IntVar(value=300)
        self.fps_var = tk.DoubleVar(value=30.0)
        self.ck_color_var = tk.StringVar(value="000000")
        self.ck_sim_var = tk.DoubleVar(value=0.08)
        self.ck_blend_var = tk.DoubleVar(value=0.05)
        self.overwrite_var = tk.BooleanVar(value=True)
        self.extra_args_var = tk.StringVar(value="")

        row = 0
        ttk.Label(param_box, text="width：").grid(row=row, column=0, sticky="w", **pad)
        ttk.Entry(param_box, textvariable=self.w_var, width=10).grid(row=row, column=1, sticky="w", **pad)
        ttk.Label(param_box, text="height：").grid(row=row, column=2, sticky="w", **pad)
        ttk.Entry(param_box, textvariable=self.h_var, width=10).grid(row=row, column=3, sticky="w", **pad)
        ttk.Label(param_box, text="FPS：").grid(row=row, column=4, sticky="w", **pad)
        ttk.Entry(param_box, textvariable=self.fps_var, width=10).grid(row=row, column=5, sticky="w", **pad)

        row += 1
        ttk.Label(param_box, text="Colorkey 颜色：").grid(row=row, column=0, sticky="w", **pad)
        ttk.Entry(param_box, textvariable=self.ck_color_var, width=12).grid(row=row, column=1, sticky="w", **pad)
        ttk.Label(param_box, text="similarity：").grid(row=row, column=2, sticky="w", **pad)
        ttk.Entry(param_box, textvariable=self.ck_sim_var, width=10).grid(row=row, column=3, sticky="w", **pad)
        ttk.Label(param_box, text="blend：").grid(row=row, column=4, sticky="w", **pad)
        ttk.Entry(param_box, textvariable=self.ck_blend_var, width=10).grid(row=row, column=5, sticky="w", **pad)

        row += 1
        ttk.Checkbutton(param_box, text="覆盖输出（-y）", variable=self.overwrite_var).grid(row=row, column=0, sticky="w", **pad)
        ttk.Label(param_box, text="额外 ffmpeg 参数：").grid(row=row, column=2, sticky="w", **pad)
        ttk.Entry(param_box, textvariable=self.extra_args_var).grid(row=row, column=3, columnspan=3, sticky="ew", **pad)
        param_box.columnconfigure(5, weight=1)

        # 操作 + 进度条
        bar = ttk.Frame(frm)
        bar.pack(fill="x", **pad)

        self.start_btn = ttk.Button(bar, text="开始转换", command=self._start)
        self.stop_btn = ttk.Button(bar, text="停止", command=self._stop, state="disabled")
        self.copy_btn = ttk.Button(bar, text="复制命令", command=self._copy_cmd)
        self.start_btn.pack(side="left")
        self.stop_btn.pack(side="left", padx=8)
        self.copy_btn.pack(side="left", padx=8)

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(bar, orient="horizontal", mode="determinate", maximum=100.0,
                                        variable=self.progress_var, length=320)
        self.progress.pack(side="left", padx=12)

        self.progress_text = tk.StringVar(value="0%")
        ttk.Label(bar, textvariable=self.progress_text, width=12).pack(side="left")

        # 日志
        log_box = ttk.LabelFrame(frm, text="运行日志")
        log_box.pack(fill="both", expand=True, **pad)

        self.log_text = tk.Text(log_box, wrap="word", height=18)
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)
        self.log_text.insert("end", "准备就绪。\n")

    def _append_log(self, s: str):
        self.log_text.insert("end", s)
        self.log_text.see("end")

    def _poll_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple):
                    kind = item[0]
                    if kind == "log":
                        self._append_log(item[1])
                    elif kind == "progress":
                        percent = float(item[1])
                        percent = max(0.0, min(100.0, percent))
                        self.progress_var.set(percent)
                        self.progress_text.set(f"{percent:.1f}%")
                    elif kind == "progress_mode":
                        mode = item[1]
                        self.progress.config(mode=mode)
                        if mode == "indeterminate":
                            self.progress.start(10)
                        else:
                            self.progress.stop()
                else:
                    self._append_log(str(item))
        except queue.Empty:
            pass
        self.after(80, self._poll_queue)

    def _pick_input(self):
        p = filedialog.askopenfilename(title="选择 WEBM 文件", filetypes=[("WebM", "*.webm"), ("All", "*.*")])
        if p:
            self.in_var.set(p)

    def _pick_output_dir(self):
        p = filedialog.askdirectory(title="选择输出文件夹")
        if p:
            self.out_var.set(p)

    def _validate_and_build_cmd(self):
        if not is_ffmpeg_available():
            raise RuntimeError("未检测到 ffmpeg。请先安装并配置 PATH。")

        in_path = Path(self.in_var.get().strip().strip('"'))
        if not in_path.exists():
            raise ValueError("输入文件不存在。")

        out_dir = Path(self.out_var.get().strip().strip('"'))
        pattern = self.pattern_var.get().strip()
        w = int(self.w_var.get())
        h = int(self.h_var.get())
        if w <= 0 or h <= 0:
            raise ValueError("width/height 必须为正整数。")

        fps = float(self.fps_var.get())
        if fps <= 0:
            raise ValueError("FPS 必须大于 0。")

        ck_color = normalize_hex_color(self.ck_color_var.get())
        sim = float(self.ck_sim_var.get())
        blend = float(self.ck_blend_var.get())
        if sim < 0 or blend < 0:
            raise ValueError("similarity / blend 不能为负数。")

        overwrite = bool(self.overwrite_var.get())
        extra_args = self.extra_args_var.get()

        cmd = build_ffmpeg_cmd(
            input_file=in_path,
            out_dir=out_dir,
            pattern=pattern,
            width=w,
            height=h,
            fps=fps,
            colorkey_hex=ck_color,
            similarity=sim,
            blend=blend,
            overwrite=overwrite,
            extra_args=extra_args,
            enable_progress=True
        )
        return in_path, cmd

    def _set_running(self, running: bool):
        self.start_btn.config(state="disabled" if running else "normal")
        self.stop_btn.config(state="normal" if running else "disabled")

    def _copy_cmd(self):
        try:
            _, cmd = self._validate_and_build_cmd()
        except Exception as e:
            messagebox.showerror("无法生成命令", str(e))
            return

        def q(x: str) -> str:
            if any(ch in x for ch in [' ', '\t', '"']):
                return '"' + x.replace('"', r'\"') + '"'
            return x

        cmd_str = " ".join(q(str(x)) for x in cmd)
        self.clipboard_clear()
        self.clipboard_append(cmd_str)
        self._append_log(f"\n[已复制命令]\n{cmd_str}\n")

    def _start(self):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("正在运行", "当前任务仍在运行。")
            return

        try:
            in_path, cmd = self._validate_and_build_cmd()
        except Exception as e:
            messagebox.showerror("参数错误", str(e))
            return

        # 进度条初始化
        self.progress_var.set(0.0)
        self.progress_text.set("0%")
        self.duration_sec = probe_duration_seconds(in_path)

        if self.duration_sec is None:
            # 无法拿到时长：用不确定进度条
            self.log_queue.put(("log", "[提示] 无法获取视频时长，进度条将以不确定模式显示。\n"))
            self.log_queue.put(("progress_mode", "indeterminate"))
        else:
            self.log_queue.put(("progress_mode", "determinate"))
            self.log_queue.put(("log", f"[提示] 视频时长：{self.duration_sec:.3f} 秒\n"))

        self.stop_event.clear()
        self._set_running(True)
        self.log_queue.put(("log", "\n========== 开始 ==========\n"))
        self.log_queue.put(("log", "命令：\n" + " ".join(map(str, cmd)) + "\n\n"))

        def stderr_reader(pipe):
            # 普通日志（编码安全）
            try:
                for raw in iter(pipe.readline, b""):
                    if self.stop_event.is_set():
                        break
                    line = raw.decode("utf-8", errors="replace").replace("\r", "\n")
                    self.log_queue.put(("log", line))
            finally:
                try:
                    pipe.close()
                except Exception:
                    pass

        def stdout_progress_reader(pipe):
            """
            解析 -progress pipe:1 输出：
              out_time_ms=...
              progress=continue/end
            """
            out_time_ms = None
            try:
                for raw in iter(pipe.readline, b""):
                    if self.stop_event.is_set():
                        break
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    if k == "out_time_ms":
                        try:
                            out_time_ms = int(v)
                        except ValueError:
                            out_time_ms = None

                        if out_time_ms is not None and self.duration_sec:
                            percent = (out_time_ms / 1_000_000.0) / self.duration_sec * 100.0
                            self.log_queue.put(("progress", percent))

                    elif k == "progress" and v == "end":
                        # 确保到 100%
                        if self.duration_sec is not None:
                            self.log_queue.put(("progress", 100.0))
            finally:
                try:
                    pipe.close()
                except Exception:
                    pass

        def worker():
            try:
                self.proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,   # progress
                    stderr=subprocess.PIPE,   # logs
                    text=False,
                    bufsize=0
                )

                assert self.proc.stdout is not None
                assert self.proc.stderr is not None

                t1 = threading.Thread(target=stdout_progress_reader, args=(self.proc.stdout,), daemon=True)
                t2 = threading.Thread(target=stderr_reader, args=(self.proc.stderr,), daemon=True)
                t1.start()
                t2.start()

                # 等待进程结束
                ret = None
                while ret is None:
                    if self.stop_event.is_set() and self.proc.poll() is None:
                        try:
                            self.proc.terminate()
                        except Exception:
                            pass
                    ret = self.proc.poll()

                t1.join(timeout=1.0)
                t2.join(timeout=1.0)

                if self.stop_event.is_set():
                    self.log_queue.put(("log", "\n[已停止]\n"))
                self.log_queue.put(("log", f"\n========== 结束（exit code={ret}）==========\n"))

            except FileNotFoundError:
                self.log_queue.put(("log", "\n[错误] 找不到 ffmpeg，请检查是否已安装并加入 PATH。\n"))
            except Exception as e:
                self.log_queue.put(("log", f"\n[错误] {e}\n"))
            finally:
                # 停止不确定进度条动画
                self.log_queue.put(("progress_mode", "determinate"))
                if self.stop_event.is_set():
                    # 停止时不要强行设 100%
                    pass
                self.proc = None
                self.stop_event.clear()
                self.after(0, lambda: self._set_running(False))

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def _stop(self):
        if not self.proc or self.proc.poll() is not None:
            return
        self.stop_event.set()
        self.log_queue.put(("log", "\n[请求停止…]\n"))
        try:
            self.proc.terminate()
        except Exception:
            pass


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
