"""
SUNO Radio Lite - Google Drive同期
共有フォルダから楽曲をダウンロード
"""

import os
import asyncio
from datetime import datetime
from config import config


class GDriveSync:
    """Google Drive同期管理"""

    def __init__(self):
        self.is_syncing = False
        self.last_error = None
        self.progress = ""

    async def sync(self, url: str = None) -> tuple[bool, str]:
        """
        Google Driveフォルダから楽曲を同期

        Args:
            url: Google Drive共有フォルダURL (省略時は保存済みURLを使用)

        Returns:
            (success, message)
        """
        if self.is_syncing:
            return False, "同期中です。しばらくお待ちください。"

        # URLの決定
        if url:
            config.set_gdrive_url(url)
            await config.save()
        else:
            url = config.get_gdrive_url()

        if not url:
            return False, "Google DriveのURLが設定されていません。\n`/sync <URL>` でURLを指定してください。"

        self.is_syncing = True
        self.progress = "同期を開始..."

        try:
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

            self.progress = ""
            self.is_syncing = False

            return True, f"同期完了: {count}曲"

        except Exception as e:
            self.last_error = str(e)
            self.progress = ""
            self.is_syncing = False
            return False, f"同期エラー: {e}"

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
