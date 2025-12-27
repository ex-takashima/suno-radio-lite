"""
SUNO Radio Lite 設定管理
環境変数 + Discord経由設定 (data/config.json)
"""

import os
import json
import aiofiles
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Discord (環境変数から - 必須)
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', 0))

    # Paths
    MUSIC_DIR = os.getenv('MUSIC_DIR', '/app/music')
    ASSETS_DIR = os.getenv('ASSETS_DIR', '/app/assets')
    DATA_DIR = os.getenv('DATA_DIR', '/app/data')

    # Stream Settings (固定値 - シンプル化)
    STREAM_VIDEO_BITRATE = '500k'
    STREAM_AUDIO_BITRATE = '128k'
    STREAM_RESOLUTION = '854x480'
    STREAM_FPS = 15

    # Audio Settings
    SAMPLE_RATE = 48000
    CHANNELS = 2

    # Gap between tracks
    TRACK_GAP_SECONDS = 2.0

    # Config file path
    CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')

    # Runtime config (loaded from config.json)
    _runtime_config = {}

    @classmethod
    async def load(cls):
        """Load runtime config from config.json"""
        if os.path.exists(cls.CONFIG_FILE):
            try:
                async with aiofiles.open(cls.CONFIG_FILE, 'r') as f:
                    content = await f.read()
                    cls._runtime_config = json.loads(content)
                    print(f"設定を読み込みました: {cls.CONFIG_FILE}", flush=True)
            except Exception as e:
                print(f"設定読み込みエラー: {e}", flush=True)
                cls._runtime_config = {}
        else:
            cls._runtime_config = {}

    @classmethod
    async def save(cls):
        """Save runtime config to config.json"""
        try:
            os.makedirs(os.path.dirname(cls.CONFIG_FILE), exist_ok=True)
            async with aiofiles.open(cls.CONFIG_FILE, 'w') as f:
                await f.write(json.dumps(cls._runtime_config, indent=2, ensure_ascii=False))
            print(f"設定を保存しました: {cls.CONFIG_FILE}", flush=True)
        except Exception as e:
            print(f"設定保存エラー: {e}", flush=True)

    @classmethod
    def get_stream_url(cls) -> str:
        """Get stream URL from runtime config"""
        return cls._runtime_config.get('stream_url', '')

    @classmethod
    def set_stream_url(cls, url: str):
        """Set stream URL"""
        cls._runtime_config['stream_url'] = url

    @classmethod
    def get_stream_key(cls) -> str:
        """Get stream key from runtime config"""
        return cls._runtime_config.get('stream_key', '')

    @classmethod
    def set_stream_key(cls, key: str):
        """Set stream key"""
        cls._runtime_config['stream_key'] = key

    @classmethod
    def get_gdrive_url(cls) -> str:
        """Get Google Drive URL from runtime config"""
        return cls._runtime_config.get('gdrive_url', '')

    @classmethod
    def set_gdrive_url(cls, url: str):
        """Set Google Drive URL"""
        cls._runtime_config['gdrive_url'] = url

    @classmethod
    def get_last_sync(cls) -> str:
        """Get last sync timestamp"""
        return cls._runtime_config.get('last_sync', '')

    @classmethod
    def set_last_sync(cls, timestamp: str):
        """Set last sync timestamp"""
        cls._runtime_config['last_sync'] = timestamp

    @classmethod
    def get_background_url(cls) -> str:
        """Get background image Google Drive URL"""
        return cls._runtime_config.get('background_url', '')

    @classmethod
    def set_background_url(cls, url: str):
        """Set background image Google Drive URL"""
        cls._runtime_config['background_url'] = url

    @classmethod
    def get_rtmp_output_url(cls) -> str:
        """Get full RTMP output URL"""
        url = cls.get_stream_url()
        key = cls.get_stream_key()
        if url and key:
            # Remove trailing slash if present
            url = url.rstrip('/')
            return f"{url}/{key}"
        return ''

    @classmethod
    def is_configured(cls) -> bool:
        """Check if stream is configured"""
        return bool(cls.get_stream_url() and cls.get_stream_key())

    @classmethod
    def get_background_path(cls) -> str:
        """Get background image path"""
        # Try common image extensions
        for ext in ['jpg', 'jpeg', 'png']:
            path = os.path.join(cls.ASSETS_DIR, f'background.{ext}')
            if os.path.exists(path):
                return path
        return os.path.join(cls.ASSETS_DIR, 'background.jpg')


config = Config()
