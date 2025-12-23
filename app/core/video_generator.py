"""
SUNO Radio Lite - 映像生成
静止画背景をrawvideoでFIFOに出力
"""

import asyncio
import os
import subprocess
import threading
import time
from config import config


class VideoGenerator:
    """映像生成プロセス管理"""

    def __init__(self):
        self.fifo_path = os.path.join(config.DATA_DIR, 'video_fifo')
        self._process = None
        self._running = False
        self._writer_thread = None
        self._auto_restart = True

    def _create_fifo(self):
        """Video FIFOを作成"""
        if os.path.exists(self.fifo_path):
            os.remove(self.fifo_path)
        os.mkfifo(self.fifo_path)
        print(f"Video FIFO作成: {self.fifo_path}", flush=True)

    def _cleanup_fifo(self):
        """Video FIFOを削除"""
        if os.path.exists(self.fifo_path):
            try:
                os.remove(self.fifo_path)
            except:
                pass

    def _get_background_path(self) -> str:
        """背景画像パスを取得"""
        for ext in ['jpg', 'jpeg', 'png']:
            path = os.path.join(config.ASSETS_DIR, f'background.{ext}')
            if os.path.exists(path):
                return path
        return None

    def _build_ffmpeg_command(self, background_path: str) -> list:
        """FFmpegコマンドを構築"""
        resolution = config.STREAM_RESOLUTION.replace('x', ':')
        fps = config.STREAM_FPS

        # スケールフィルター（アスペクト比維持、パディング、YUV420p変換）
        scale_filter = (
            f"scale={resolution}:force_original_aspect_ratio=decrease,"
            f"pad={resolution}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"fps={fps},"
            f"format=yuv420p"
        )

        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-re',
            '-i', background_path,
            '-vf', scale_filter,
            '-f', 'rawvideo',
            '-pix_fmt', 'yuv420p',
            'pipe:1'
        ]

        return cmd

    def _writer_loop(self, background_path: str):
        """映像書き込みスレッド"""
        try:
            print("Video FIFO接続待機...", flush=True)
            fifo = open(self.fifo_path, 'wb')
            print("Video FIFO接続完了", flush=True)

            while self._running:
                try:
                    cmd = self._build_ffmpeg_command(background_path)
                    print(f"映像生成開始: {os.path.basename(background_path)}", flush=True)

                    self._process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL
                    )

                    while self._running:
                        if self._process.poll() is not None:
                            break

                        data = self._process.stdout.read(65536)
                        if not data:
                            break

                        try:
                            fifo.write(data)
                        except (BrokenPipeError, OSError):
                            self._running = False
                            break

                    self._cleanup_process()

                    if self._running and self._auto_restart:
                        print("映像生成再起動...", flush=True)
                        time.sleep(0.5)
                    else:
                        break

                except Exception as e:
                    print(f"映像生成エラー: {e}", flush=True)
                    self._cleanup_process()
                    if self._running and self._auto_restart:
                        time.sleep(0.5)
                    else:
                        break

            fifo.close()

        except Exception as e:
            print(f"映像書き込みスレッドエラー: {e}", flush=True)

    def _cleanup_process(self):
        """プロセスをクリーンアップ"""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except:
                try:
                    self._process.kill()
                except:
                    pass
            self._process = None

    async def start(self):
        """映像生成を開始"""
        if self._running:
            return

        background_path = self._get_background_path()
        if not background_path:
            print("背景ファイルが見つかりません", flush=True)
            return False

        self._create_fifo()
        self._running = True

        self._writer_thread = threading.Thread(
            target=self._writer_loop,
            args=(background_path,),
            daemon=True
        )
        self._writer_thread.start()
        return True

    async def stop(self):
        """映像生成を停止"""
        if not self._running:
            return

        print("映像生成停止", flush=True)
        self._running = False
        self._auto_restart = False
        self._cleanup_process()

        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=3)

        self._cleanup_fifo()
        self._auto_restart = True

    def get_fifo_path(self) -> str:
        """Video FIFOパスを取得"""
        return self.fifo_path

    def is_running(self) -> bool:
        """実行中かどうか"""
        return self._running


# シングルトン
video_generator = VideoGenerator()
