"""
SUNO Radio Lite - ストリーム管理
FIFOベースの配信処理
"""

import asyncio
import json
import os
from datetime import datetime
from config import config
from core.audio_player import audio_player
from core.video_generator import video_generator


class StreamManager:
    def __init__(self):
        self.process = None
        self.is_streaming = False
        self.start_time = None
        self._stop_requested = False
        self._state_file = os.path.join(config.DATA_DIR, 'stream_state.json')
        # 自動復旧関連
        self._recovery_count = 0
        self._max_recovery_retries = 5
        self._recovery_delay = 10

    def _save_state(self, streaming: bool):
        """配信状態をファイルに保存"""
        try:
            state = {'streaming': streaming, 'timestamp': datetime.now().isoformat()}
            with open(self._state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            print(f"状態保存エラー: {e}", flush=True)

    def _load_state(self) -> bool:
        """保存された配信状態を読み込み"""
        try:
            if os.path.exists(self._state_file):
                with open(self._state_file, 'r') as f:
                    state = json.load(f)
                return state.get('streaming', False)
        except Exception as e:
            print(f"状態読み込みエラー: {e}", flush=True)
        return False

    def _can_recover(self) -> bool:
        """自動復旧可能かチェック"""
        return self._recovery_count < self._max_recovery_retries

    def _increment_recovery(self):
        """復旧カウンターを増加"""
        self._recovery_count += 1
        print(f"復旧試行 {self._recovery_count}/{self._max_recovery_retries}", flush=True)

    def _reset_recovery_count(self):
        """復旧カウンターをリセット（正常動作時）"""
        if self._recovery_count > 0:
            print("安定動作確認、復旧カウンターをリセット", flush=True)
        self._recovery_count = 0

    async def _restart_audio_player(self) -> bool:
        """オーディオプレイヤーを再起動"""
        try:
            print("オーディオプレイヤー再起動中...", flush=True)
            await audio_player.stop()
            await asyncio.sleep(1)
            asyncio.create_task(audio_player.start())

            # FIFOが準備されるまで待機
            audio_fifo_path = audio_player.get_fifo_path()
            for _ in range(30):
                if os.path.exists(audio_fifo_path):
                    print("オーディオプレイヤー再起動完了", flush=True)
                    return True
                await asyncio.sleep(0.1)

            print("オーディオプレイヤー再起動タイムアウト", flush=True)
            return False
        except Exception as e:
            print(f"オーディオプレイヤー再起動エラー: {e}", flush=True)
            return False

    async def _restart_video_generator(self) -> bool:
        """映像生成を再起動"""
        try:
            print("映像生成再起動中...", flush=True)
            await video_generator.stop()
            await asyncio.sleep(1)
            await video_generator.start()

            # FIFOが準備されるまで待機
            video_fifo_path = video_generator.get_fifo_path()
            for _ in range(30):
                if os.path.exists(video_fifo_path):
                    print("映像生成再起動完了", flush=True)
                    return True
                await asyncio.sleep(0.1)

            print("映像生成再起動タイムアウト", flush=True)
            return False
        except Exception as e:
            print(f"映像生成再起動エラー: {e}", flush=True)
            return False

    async def auto_start_if_needed(self) -> bool:
        """前回配信中だった場合は自動開始"""
        if self._load_state():
            print("前回配信中だったため、自動で配信を再開します", flush=True)
            success, msg = await self.start()
            print(f"自動開始結果: {msg}", flush=True)
            return success
        return False

    def _build_ffmpeg_command(self) -> list:
        """ffmpegコマンドを構築"""
        stream_url = config.get_rtmp_output_url()
        video_fifo_path = video_generator.get_fifo_path()
        audio_fifo_path = audio_player.get_fifo_path()

        resolution = config.STREAM_RESOLUTION
        fps = config.STREAM_FPS

        cmd = [
            'ffmpeg',
            # Video FIFO入力
            '-thread_queue_size', '512',
            '-f', 'rawvideo',
            '-pix_fmt', 'yuv420p',
            '-s', resolution,
            '-r', str(fps),
            '-i', video_fifo_path,
            # Audio FIFO入力
            '-thread_queue_size', '512',
            '-f', 's16le',
            '-ar', str(config.SAMPLE_RATE),
            '-ac', str(config.CHANNELS),
            '-i', audio_fifo_path,
            # 映像エンコード
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'stillimage',
            '-b:v', config.STREAM_VIDEO_BITRATE,
            '-maxrate', config.STREAM_VIDEO_BITRATE,
            '-bufsize', '1000k',
            '-pix_fmt', 'yuv420p',
            '-r', str(fps),
            '-g', str(fps * 2),
            '-keyint_min', str(fps * 2),
            '-sc_threshold', '0',
            # 音声エンコード
            '-c:a', 'aac',
            '-b:a', config.STREAM_AUDIO_BITRATE,
            '-ar', str(config.SAMPLE_RATE),
            '-ac', str(config.CHANNELS),
            # 出力
            '-f', 'flv',
            '-flvflags', 'no_duration_filesize',
            stream_url
        ]

        return cmd

    async def start(self) -> tuple[bool, str]:
        """配信を開始"""
        if self.is_streaming:
            return False, "既に配信中です"

        # 設定確認
        if not config.is_configured():
            return False, "配信設定がありません。`/config url` と `/config key` で設定してください。"

        # 楽曲確認
        from core.gdrive_sync import gdrive_sync
        if not gdrive_sync.get_tracks():
            return False, "楽曲がありません。`/sync` で楽曲を同期してください。"

        # ノーマライズ確認
        unnormalized = gdrive_sync.get_unnormalized_count()
        if unnormalized > 0:
            return False, f"未ノーマライズの楽曲が{unnormalized}曲あります。\n`/sync` を実行してノーマライズを完了してください。"

        # 背景確認
        if not os.path.exists(config.get_background_path()):
            return False, "背景画像がありません。assets/background.jpg を配置してください。"

        self.is_streaming = True
        self.start_time = datetime.now()
        self._stop_requested = False
        self._save_state(True)  # 配信状態を保存

        print("=" * 50, flush=True)
        print("SUNO Radio Lite 配信開始", flush=True)
        print(f"  配信先: {config.get_stream_url()}", flush=True)
        print("=" * 50, flush=True)

        # オーディオプレイヤーを開始
        audio_task = asyncio.create_task(audio_player.start())

        # Audio FIFOが作成されるまで待機
        audio_fifo_path = audio_player.get_fifo_path()
        for _ in range(50):
            if os.path.exists(audio_fifo_path):
                break
            await asyncio.sleep(0.1)
        else:
            await self.stop()
            return False, "Audio FIFOの作成がタイムアウト"

        # 映像生成を開始
        if not await video_generator.start():
            await self.stop()
            return False, "映像生成の開始に失敗"

        # Video FIFOが作成されるまで待機
        video_fifo_path = video_generator.get_fifo_path()
        for _ in range(50):
            if os.path.exists(video_fifo_path):
                break
            await asyncio.sleep(0.1)
        else:
            await self.stop()
            return False, "Video FIFOの作成がタイムアウト"

        # メインストリームループ
        asyncio.create_task(self._stream_loop())

        return True, "配信を開始しました"

    async def _stream_loop(self):
        """配信メインループ"""
        stable_seconds = 0  # 安定動作時間カウンター

        while self.is_streaming and not self._stop_requested:
            try:
                cmd = self._build_ffmpeg_command()
                print(f"FFmpeg起動", flush=True)

                self.process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE
                )
                print(f"FFmpegプロセス開始 PID: {self.process.pid}", flush=True)

                # プロセス監視
                while self.process.returncode is None:
                    if self._stop_requested:
                        self.process.terminate()
                        await self.process.wait()
                        break

                    # クラッシュ検出: AudioPlayerまたはVideoGeneratorが停止/クラッシュ
                    audio_crash = audio_player.is_ffmpeg_crash_detected() or not audio_player.is_playing
                    video_crash = video_generator.is_ffmpeg_crash_detected() or not video_generator.is_running()

                    if audio_crash or video_crash:
                        crash_source = []
                        if audio_crash:
                            crash_source.append("AudioPlayer")
                        if video_crash:
                            crash_source.append("VideoGenerator")
                        print(f"クラッシュ検出: {', '.join(crash_source)}", flush=True)

                        if self._can_recover():
                            self._increment_recovery()
                            print(f"FFmpegクラッシュ検出、復旧試行中...", flush=True)

                            # 全コンポーネントを再起動
                            recovery_success = True

                            if audio_crash:
                                audio_player.reset_crash_detection()
                                if not await self._restart_audio_player():
                                    recovery_success = False

                            if video_crash:
                                video_generator.reset_crash_detection()
                                if not await self._restart_video_generator():
                                    recovery_success = False

                            if recovery_success:
                                print("復旧成功", flush=True)
                                stable_seconds = 0
                                # FFmpegプロセスを終了して再起動
                                if self.process and self.process.returncode is None:
                                    self.process.terminate()
                                    await self.process.wait()
                                break  # 外側のループで再起動
                            else:
                                print("復旧失敗", flush=True)

                        # 復旧不可または復旧失敗
                        if self.process and self.process.returncode is None:
                            self.process.terminate()
                            await self.process.wait()

                        if not self._can_recover():
                            print(f"復旧試行回数上限（{self._max_recovery_retries}回）に達しました。配信を停止します。", flush=True)
                            self._stop_requested = True
                        break

                    # 安定動作カウンター（60秒安定動作で復旧カウンターリセット）
                    stable_seconds += 1
                    if stable_seconds >= 60 and self._recovery_count > 0:
                        self._reset_recovery_count()
                        stable_seconds = 0

                    await asyncio.sleep(1)

                if self._stop_requested:
                    break

                # エラー時の処理（FFmpegクラッシュ）
                if self.process.returncode != 0 and not self._stop_requested:
                    stderr = await self.process.stderr.read()
                    error_msg = stderr.decode()[-500:]
                    print(f"FFmpegエラー (code: {self.process.returncode})", flush=True)
                    print(f"  {error_msg}", flush=True)

                    if self._can_recover():
                        self._increment_recovery()
                        print(f"FFmpegクラッシュ検出、{self._recovery_delay}秒後に再起動...", flush=True)
                        await asyncio.sleep(self._recovery_delay)
                        continue
                    else:
                        print(f"復旧試行回数上限に達しました。配信を停止します。", flush=True)
                        self._stop_requested = True
                        break

            except Exception as e:
                print(f"ストリームエラー: {e}", flush=True)
                if self._can_recover():
                    self._increment_recovery()
                    await asyncio.sleep(self._recovery_delay)
                else:
                    print(f"復旧試行回数上限に達しました。配信を停止します。", flush=True)
                    self._stop_requested = True
                    break

        # クリーンアップ
        await video_generator.stop()
        await audio_player.stop()

        self.is_streaming = False
        print("配信終了", flush=True)

    async def stop(self) -> tuple[bool, str]:
        """配信を停止"""
        if not self.is_streaming:
            return False, "配信していません"

        print("配信停止リクエスト", flush=True)
        self._stop_requested = True
        self._save_state(False)  # 配信停止を保存

        await video_generator.stop()
        await audio_player.stop()

        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.process.kill()

        self.is_streaming = False
        return True, "配信を停止しました"

    def skip(self) -> bool:
        """現在の曲をスキップ"""
        return audio_player.skip()

    def shuffle(self) -> bool:
        """プレイリストを再シャッフル（後方互換用）"""
        return audio_player.shuffle()

    def toggle_playback_mode(self) -> str:
        """再生モードを切り替え"""
        return audio_player.toggle_playback_mode()

    def get_playback_mode(self) -> str:
        """現在の再生モードを取得"""
        return audio_player.get_playback_mode()

    def get_status(self) -> dict:
        """配信状態を取得"""
        uptime = None
        if self.start_time and self.is_streaming:
            delta = datetime.now() - self.start_time
            uptime = int(delta.total_seconds())

        current_track = audio_player.get_current_track()

        return {
            'is_streaming': self.is_streaming,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime_seconds': uptime,
            'uptime_formatted': self._format_uptime(uptime) if uptime else None,
            'current_track': current_track,
            'stream_url': config.get_stream_url()
        }

    def _format_uptime(self, seconds: int) -> str:
        """秒を時:分:秒形式に変換"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"


# シングルトン
stream_manager = StreamManager()
