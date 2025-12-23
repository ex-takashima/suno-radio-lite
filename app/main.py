"""
SUNO Radio Lite - メインエントリーポイント
"""

import asyncio
import os
import sys

# パスを通す
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from bot.discord_bot import bot


async def main():
    """メイン処理"""
    print("=" * 50, flush=True)
    print("SUNO Radio Lite", flush=True)
    print("=" * 50, flush=True)

    # 必須設定チェック
    if not config.DISCORD_TOKEN:
        print("エラー: DISCORD_TOKEN が設定されていません", flush=True)
        print(".env ファイルを確認してください", flush=True)
        return

    # ディレクトリ確認
    for dir_path in [config.MUSIC_DIR, config.ASSETS_DIR, config.DATA_DIR]:
        os.makedirs(dir_path, exist_ok=True)

    # 設定読み込み
    await config.load()

    print(f"Music: {config.MUSIC_DIR}", flush=True)
    print(f"Assets: {config.ASSETS_DIR}", flush=True)
    print(f"Data: {config.DATA_DIR}", flush=True)

    # 設定状態を表示
    if config.is_configured():
        print(f"配信先: {config.get_stream_url()}", flush=True)
    else:
        print("配信設定: 未完了 (Discordで /config コマンドを使用)", flush=True)

    print("=" * 50, flush=True)

    # Discord Bot起動
    print("Discord Bot起動中...", flush=True)
    await bot.start(config.DISCORD_TOKEN)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n終了", flush=True)
