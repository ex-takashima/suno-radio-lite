"""
SUNO Radio Lite - オーディオプレイヤー
FIFOベースの音声処理
"""

import asyncio
import os
import random
import subprocess
import threading
import time
from config import config


# タイムアウト設定
MAX_TRACK_DURATION = 600  # 1曲の最大再生時間（秒）= 10分
DATA_TIMEOUT = 30  # データ受信タイムアウト（秒）

# PCMフォーマット定数
SAMPLE_RATE = 48000
CHANNELS = 2
BYTES_PER_SAMPLE = 2  # s16le
BYTES_PER_SECOND = SAMPLE_RATE * CHANNELS * BYTES_PER_SAMPLE


class AudioPlayer:
    """FIFOベースのオーディオプレイヤー"""

    def __init__(self):
        self.fifo_path = os.path.join(config.DATA_DIR, 'audio_fifo')
        self.is_playing = False
        self.current_track = None
        self.playlist = []
        self.playlist_index = 0
        self._stop_requested = False
        self._skip_requested = False
        self._decoder_process = None
        self._writer_thread = None
        self._fifo_fd = None
        self._track_start_time = None
        self._last_data_time = None

    def _create_fifo(self):
        """FIFOを作成"""
        if os.path.exists(self.fifo_path):
            os.remove(self.fifo_path)
        os.mkfifo(self.fifo_path)
        print(f"FIFO作成: {self.fifo_path}", flush=True)

    def _cleanup_fifo(self):
        """FIFOを削除"""
        if os.path.exists(self.fifo_path):
            try:
                os.remove(self.fifo_path)
            except:
                pass

    def _load_playlist(self) -> bool:
        """楽曲ディレクトリからプレイリストを読み込み"""
        if not os.path.exists(config.MUSIC_DIR):
            print(f"楽曲ディレクトリが見つかりません: {config.MUSIC_DIR}", flush=True)
            return False

        tracks = []
        supported_ext = {'.mp3', '.wav', '.flac', '.m4a', '.ogg'}

        for file in os.listdir(config.MUSIC_DIR):
            if os.path.splitext(file)[1].lower() in supported_ext:
                tracks.append(os.path.join(config.MUSIC_DIR, file))

        if not tracks:
            print("楽曲がありません", flush=True)
            return False

        # シャッフル
        random.shuffle(tracks)
        print(f"プレイリスト読込: {len(tracks)}曲", flush=True)

        self.playlist = tracks
        self.playlist_index = 0

        return True

    def _get_next_track(self) -> str:
        """次のトラックを取得"""
        if not self.playlist:
            if not self._load_playlist():
                return None

        track = self.playlist[self.playlist_index]
        self.playlist_index += 1

        if self.playlist_index >= len(self.playlist):
            print("プレイリスト終端、再シャッフル", flush=True)
            random.shuffle(self.playlist)
            self.playlist_index = 0

        return track

    def _write_silence(self, fifo_fd: int, duration_seconds: float) -> bool:
        """無音をFIFOに書き込み（曲間のギャップ用）"""
        if duration_seconds <= 0:
            return True

        total_bytes = int(BYTES_PER_SECOND * duration_seconds)
        chunk_size = 4096
        silence_chunk = bytes(chunk_size)

        try:
            bytes_written = 0
            while bytes_written < total_bytes:
                if self._stop_requested or self._skip_requested:
                    return False

                write_size = min(chunk_size, total_bytes - bytes_written)
                os.write(fifo_fd, silence_chunk[:write_size])
                bytes_written += write_size

            return True
        except (BrokenPipeError, OSError):
            return False

    def _decode_and_write(self, track_path: str, fifo_fd: int) -> bool:
        """トラックをデコードしてFIFOに書き込み"""
        import select

        track_name = os.path.basename(track_path)
        print(f"再生中: {track_name}", flush=True)
        self.current_track = track_name

        current_time = time.time()
        self._track_start_time = current_time
        self._last_data_time = current_time

        cmd = [
            'ffmpeg',
            '-i', track_path,
            '-f', 's16le',
            '-acodec', 'pcm_s16le',
            '-ar', str(SAMPLE_RATE),
            '-ac', str(CHANNELS),
            '-loglevel', 'error',
            'pipe:1'
        ]

        try:
            self._decoder_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )

            fd = self._decoder_process.stdout.fileno()

            while True:
                if self._stop_requested or self._skip_requested:
                    break

                # タイムアウトチェック
                current_time = time.time()
                elapsed = current_time - self._track_start_time
                data_idle = current_time - self._last_data_time

                if elapsed > MAX_TRACK_DURATION:
                    print(f"トラックタイムアウト、自動スキップ", flush=True)
                    break

                if data_idle > DATA_TIMEOUT:
                    print(f"データ受信タイムアウト、自動スキップ", flush=True)
                    break

                ready, _, _ = select.select([fd], [], [], 0.1)
                if not ready:
                    if self._decoder_process.poll() is not None:
                        break
                    continue

                data = os.read(fd, 4096)
                if not data:
                    break

                self._last_data_time = time.time()

                try:
                    os.write(fifo_fd, data)
                except (BrokenPipeError, OSError):
                    break

            # プロセスを確実に終了
            if self._decoder_process.poll() is None:
                self._decoder_process.kill()
            self._decoder_process.wait()
            self._decoder_process = None

            self._track_start_time = None
            self._last_data_time = None

            return not (self._stop_requested or self._skip_requested)

        except Exception as e:
            print(f"デコードエラー: {e}", flush=True)
            if self._decoder_process:
                try:
                    self._decoder_process.kill()
                    self._decoder_process.wait()
                except:
                    pass
                self._decoder_process = None
            return False

    def _writer_loop(self):
        """書き込みスレッドのメインループ"""
        try:
            print("FIFO書き込み待機中...", flush=True)
            self._fifo_fd = os.open(self.fifo_path, os.O_WRONLY)
            print("FIFO接続完了", flush=True)

            while self.is_playing and not self._stop_requested:
                track = self._get_next_track()
                if not track:
                    print("再生可能なトラックがありません", flush=True)
                    break

                self._skip_requested = False
                self._decode_and_write(track, self._fifo_fd)

                if self._skip_requested:
                    print("スキップ完了", flush=True)

                # 曲間に無音を挿入
                if not self._stop_requested and not self._skip_requested:
                    self._write_silence(self._fifo_fd, config.TRACK_GAP_SECONDS)

        except Exception as e:
            print(f"書き込みスレッドエラー: {e}", flush=True)
        finally:
            if self._fifo_fd is not None:
                try:
                    os.close(self._fifo_fd)
                except:
                    pass
                self._fifo_fd = None

        self.is_playing = False
        print("書き込みスレッド終了", flush=True)

    async def start(self):
        """再生を開始"""
        if self.is_playing:
            print("既に再生中です", flush=True)
            return

        self._create_fifo()
        self.is_playing = True
        self._stop_requested = False

        print("オーディオプレイヤー開始", flush=True)

        if not self._load_playlist():
            self.is_playing = False
            self._cleanup_fifo()
            return

        # 書き込みスレッドを開始
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._writer_thread.start()

        # スレッドが終了するまで待機
        while self._writer_thread.is_alive() and not self._stop_requested:
            await asyncio.sleep(0.5)

        self.is_playing = False
        self.current_track = None
        self._cleanup_fifo()
        print("オーディオプレイヤー停止", flush=True)

    async def stop(self):
        """再生を停止"""
        if not self.is_playing:
            return

        print("停止リクエスト", flush=True)
        self._stop_requested = True

        if self._decoder_process:
            try:
                self._decoder_process.terminate()
                self._decoder_process.wait(timeout=2)
            except:
                self._decoder_process.kill()

        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=3)

    def skip(self) -> bool:
        """現在の曲をスキップ"""
        if not self.is_playing:
            return False

        print("スキップリクエスト", flush=True)
        self._skip_requested = True
        return True

    def shuffle(self) -> bool:
        """プレイリストを再読み込み＆シャッフル"""
        if not self._load_playlist():
            return False

        print("プレイリスト再シャッフル", flush=True)

        if self.is_playing:
            self._skip_requested = True

        return True

    def get_current_track(self) -> dict:
        """現在のトラック情報を取得"""
        if not self.current_track:
            return None

        result = {
            'title': self.current_track
        }

        if self._track_start_time:
            elapsed = int(time.time() - self._track_start_time)
            result['elapsed_seconds'] = elapsed
            result['elapsed_formatted'] = f"{elapsed // 60}:{elapsed % 60:02d}"

        return result

    def get_fifo_path(self) -> str:
        """FIFOパスを取得"""
        return self.fifo_path


# シングルトン
audio_player = AudioPlayer()
