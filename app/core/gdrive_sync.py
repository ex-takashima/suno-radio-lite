"""
SUNO Radio Lite - Google Drive同期
共有フォルダから楽曲をダウンロード + ラウドネスノーマライズ
"""

import os
import asyncio
import subprocess
from datetime import datetime
from config import config


class GDriveSync:
    """Google Drive同期管理"""

    # ラウドネスノーマライズ設定（EBU R128準拠）
    TARGET_LUFS = "-14"
    TRUE_PEAK = "-1"

    def __init__(self):
        self.is_syncing = False
        self.last_error = None
        self.progress = ""
        self.normalized_list_path = os.path.join(config.DATA_DIR, 'normalized_files.txt')
        self._load_normalized_list()

    def _load_normalized_list(self):
        """ノーマライズ済みファイルリストを読み込み"""
        self.normalized_files = set()
        if os.path.exists(self.normalized_list_path):
            try:
                with open(self.normalized_list_path, 'r') as f:
                    self.normalized_files = set(line.strip() for line in f if line.strip())
            except Exception:
                pass

    def _save_normalized_list(self):
        """ノーマライズ済みファイルリストを保存"""
        try:
            os.makedirs(os.path.dirname(self.normalized_list_path), exist_ok=True)
            with open(self.normalized_list_path, 'w') as f:
                for filepath in sorted(self.normalized_files):
                    f.write(filepath + '\n')
        except Exception:
            pass

    def _is_normalized(self, filepath: str) -> bool:
        """ファイルがノーマライズ済みかチェック"""
        return filepath in self.normalized_files

    def _mark_normalized(self, filepath: str):
        """ファイルをノーマライズ済みとしてマーク"""
        self.normalized_files.add(filepath)

    async def _normalize_file(self, filepath: str) -> bool:
        """
        ファイルをラウドネスノーマライズ

        Args:
            filepath: 音声ファイルのパス

        Returns:
            成功したかどうか
        """
        if self._is_normalized(filepath):
            return True

        filename = os.path.basename(filepath)
        temp_path = filepath + '.tmp'

        try:
            # ffmpegでラウドネスノーマライズ
            cmd = [
                'ffmpeg', '-y', '-i', filepath, '-vn',
                '-af', f'loudnorm=I={self.TARGET_LUFS}:TP={self.TRUE_PEAK}:LRA=11',
                '-f', 'mp3', '-ar', '44100', '-b:a', '320k', temp_path
            ]

            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True)
            )

            if process.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                os.replace(temp_path, filepath)
                self._mark_normalized(filepath)
                print(f"✅ ノーマライズ完了: {filename}", flush=True)
                return True
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                print(f"❌ ノーマライズ失敗: {filename}", flush=True)
                return False

        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            print(f"❌ ノーマライズエラー: {filename} - {e}", flush=True)
            return False

    async def _normalize_all(self) -> tuple[int, int]:
        """
        全楽曲をノーマライズ

        Returns:
            (処理数, 成功数)
        """
        supported_ext = {'.mp3', '.wav', '.flac', '.m4a'}
        files_to_normalize = []

        if os.path.exists(config.MUSIC_DIR):
            for file in os.listdir(config.MUSIC_DIR):
                filepath = os.path.join(config.MUSIC_DIR, file)
                if os.path.splitext(file)[1].lower() in supported_ext:
                    if not self._is_normalized(filepath):
                        files_to_normalize.append(filepath)

        if not files_to_normalize:
            return 0, 0

        total = len(files_to_normalize)
        success = 0

        for i, filepath in enumerate(files_to_normalize, 1):
            self.progress = f"ノーマライズ中... ({i}/{total})"
            if await self._normalize_file(filepath):
                success += 1

        self._save_normalized_list()
        return total, success

    def _clear_music_dir(self):
        """楽曲ディレクトリをクリア"""
        supported_ext = {'.mp3', '.wav', '.flac', '.m4a', '.ogg'}
        if os.path.exists(config.MUSIC_DIR):
            for file in os.listdir(config.MUSIC_DIR):
                if os.path.splitext(file)[1].lower() in supported_ext:
                    filepath = os.path.join(config.MUSIC_DIR, file)
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
        # ノーマライズ済みリストもクリア
        self.normalized_files.clear()
        self._save_normalized_list()

    async def sync(self, url: str = None, normalize: bool = True, replace: bool = False) -> tuple[bool, str, dict]:
        """
        Google Driveフォルダから楽曲を同期

        Args:
            url: Google Drive共有フォルダURL (省略時は保存済みURLを使用)
            normalize: ダウンロード後にラウドネスノーマライズを実行するか
            replace: 既存の楽曲を削除して入れ替えるか（配信中は不可）

        Returns:
            (success, message, details)
        """
        if self.is_syncing:
            return False, "同期中です。しばらくお待ちください。", {}

        # 入れ替えモードの場合、配信中かチェック
        if replace:
            from core.stream_manager import stream_manager
            if stream_manager.is_streaming:
                return False, "配信中は楽曲の入れ替えができません。\n配信を停止してから再度お試しください。", {}

        # URLの決定
        if url:
            config.set_gdrive_url(url)
            await config.save()
        else:
            url = config.get_gdrive_url()

        if not url:
            return False, "Google DriveのURLが設定されていません。\n`/sync <URL>` でURLを指定してください。", {}

        self.is_syncing = True
        self.progress = "同期を開始..."

        details = {'track_count': 0, 'normalized_count': 0, 'normalized_success': 0, 'replaced': replace}

        try:
            # 入れ替えモードの場合、既存の楽曲を削除
            if replace:
                self.progress = "既存の楽曲を削除中..."
                self._clear_music_dir()

            # gdownでフォルダをダウンロード
            import gdown

            self.progress = "ダウンロード中..."

            # 非同期でgdownを実行
            loop = asyncio.get_event_loop()

            # 既存ファイルをクリアするかどうかはオプション
            # ここでは上書きモードで実行
            await loop.run_in_executor(
                None,
                lambda: gdown.download_folder(
                    url,
                    output=config.MUSIC_DIR,
                    quiet=False,
                    use_cookies=False
                )
            )

            # 同期完了時刻を記録
            timestamp = datetime.now().isoformat()
            config.set_last_sync(timestamp)
            await config.save()

            # 楽曲数をカウント
            count = self._count_tracks()
            details['track_count'] = count

            # ラウドネスノーマライズ
            if normalize:
                self.progress = "ラウドネスノーマライズ中..."
                normalized_count, normalized_success = await self._normalize_all()
                details['normalized_count'] = normalized_count
                details['normalized_success'] = normalized_success

            self.progress = ""
            self.is_syncing = False

            # プレイリストを再読み込み（配信中でも反映）
            from core.audio_player import audio_player
            audio_player.reload_playlist()

            # メッセージ作成
            message = f"同期完了: {count}曲"
            if normalize and details['normalized_count'] > 0:
                message += f" (ノーマライズ: {details['normalized_success']}/{details['normalized_count']})"

            return True, message, details

        except Exception as e:
            self.last_error = str(e)
            self.progress = ""
            self.is_syncing = False
            return False, f"同期エラー: {e}", details

    def _count_tracks(self) -> int:
        """楽曲ファイル数をカウント"""
        count = 0
        supported_ext = {'.mp3', '.wav', '.flac', '.m4a', '.ogg'}

        if os.path.exists(config.MUSIC_DIR):
            for file in os.listdir(config.MUSIC_DIR):
                if os.path.splitext(file)[1].lower() in supported_ext:
                    count += 1
        return count

    def get_status(self) -> dict:
        """同期状態を取得"""
        return {
            'is_syncing': self.is_syncing,
            'progress': self.progress,
            'last_sync': config.get_last_sync(),
            'gdrive_url': config.get_gdrive_url(),
            'track_count': self._count_tracks(),
            'last_error': self.last_error
        }

    def has_unnormalized_tracks(self) -> bool:
        """未ノーマライズの楽曲があるかチェック"""
        supported_ext = {'.mp3', '.wav', '.flac', '.m4a'}
        if os.path.exists(config.MUSIC_DIR):
            for file in os.listdir(config.MUSIC_DIR):
                if os.path.splitext(file)[1].lower() in supported_ext:
                    filepath = os.path.join(config.MUSIC_DIR, file)
                    if not self._is_normalized(filepath):
                        return True
        return False

    def get_unnormalized_count(self) -> int:
        """未ノーマライズの楽曲数を取得"""
        count = 0
        supported_ext = {'.mp3', '.wav', '.flac', '.m4a'}
        if os.path.exists(config.MUSIC_DIR):
            for file in os.listdir(config.MUSIC_DIR):
                if os.path.splitext(file)[1].lower() in supported_ext:
                    filepath = os.path.join(config.MUSIC_DIR, file)
                    if not self._is_normalized(filepath):
                        count += 1
        return count

    def get_tracks(self) -> list[str]:
        """楽曲ファイル一覧を取得"""
        tracks = []
        supported_ext = {'.mp3', '.wav', '.flac', '.m4a', '.ogg'}

        if os.path.exists(config.MUSIC_DIR):
            for file in sorted(os.listdir(config.MUSIC_DIR)):
                if os.path.splitext(file)[1].lower() in supported_ext:
                    tracks.append(file)
        return tracks

    async def sync_background(self, url: str = None) -> tuple[bool, str]:
        """
        Google Driveから背景画像をダウンロード

        Args:
            url: Google Drive共有ファイルURL (省略時は保存済みURLを使用)

        Returns:
            (success, message)
        """
        if self.is_syncing:
            return False, "同期中です。しばらくお待ちください。"

        # URLの決定
        if url:
            config.set_background_url(url)
            await config.save()
        else:
            url = config.get_background_url()

        if not url:
            return False, "背景画像のURLが設定されていません。\n`/background sync <URL>` でURLを指定してください。"

        self.is_syncing = True
        self.progress = "背景画像をダウンロード中..."

        try:
            import gdown

            # アセットディレクトリを作成
            os.makedirs(config.ASSETS_DIR, exist_ok=True)

            # 一時ファイルパス
            temp_path = os.path.join(config.ASSETS_DIR, 'background_temp')

            # 非同期でgdownを実行
            loop = asyncio.get_event_loop()
            downloaded_path = await loop.run_in_executor(
                None,
                lambda: gdown.download(url, temp_path, quiet=False, fuzzy=True)
            )

            if not downloaded_path or not os.path.exists(temp_path):
                self.is_syncing = False
                self.progress = ""
                return False, "ダウンロードに失敗しました。URLを確認してください。"

            # ファイル形式を判定して適切な拡張子でリネーム
            import imghdr
            img_type = imghdr.what(temp_path)

            if img_type in ['jpeg', 'jpg']:
                ext = 'jpg'
            elif img_type == 'png':
                ext = 'png'
            else:
                # 拡張子が不明でも画像として扱う
                ext = 'jpg'

            # 既存の背景画像を削除
            for old_ext in ['jpg', 'jpeg', 'png']:
                old_path = os.path.join(config.ASSETS_DIR, f'background.{old_ext}')
                if os.path.exists(old_path):
                    os.remove(old_path)

            # 最終的なファイル名でリネーム
            final_path = os.path.join(config.ASSETS_DIR, f'background.{ext}')
            os.rename(temp_path, final_path)

            self.progress = ""
            self.is_syncing = False

            return True, f"背景画像を保存しました: background.{ext}"

        except Exception as e:
            self.last_error = str(e)
            self.progress = ""
            self.is_syncing = False
            # 一時ファイルを削除
            temp_path = os.path.join(config.ASSETS_DIR, 'background_temp')
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False, f"エラー: {e}"


# シングルトン
gdrive_sync = GDriveSync()
