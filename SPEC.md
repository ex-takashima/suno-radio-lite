# SUNO Radio Lite - 仕様書

## 概要

SUNO Radio Liteは、Discord操作だけで24時間音楽配信を実現するシンプルな配信システムです。
技術的な知識がなくても、VPS + Docker + Discord Botだけで配信を始められます。

## コンセプト

**「.envにはDISCORD_TOKENだけ。あとはDiscordから全部設定」**

- 配信設定（URL/キー）: `/config` コマンド
- 楽曲管理: Google Drive + `/sync` コマンド
- 配信操作: `/start`, `/stop`, `/skip`

---

## 機能仕様

### 1. 配信機能

| 項目 | 仕様 |
|------|------|
| プロトコル | RTMP / RTMPS |
| 配信先 | 任意（YouTube, Twitch, X, Kick等） |
| 映像 | 静止画1枚 (H.264) |
| 音声 | 楽曲シャッフル再生 (AAC) |
| 解像度 | 480p (854x480) |
| 映像ビットレート | 500kbps |
| 音声ビットレート | 128kbps |
| フレームレート | 15fps |

### 2. 設定管理

Discord `/config` コマンドで設定を管理。設定は `data/config.json` に永続化。

```json
{
  "stream_url": "rtmp://a.rtmp.youtube.com/live2",
  "stream_key": "xxxx-xxxx-xxxx-xxxx",
  "gdrive_url": "https://drive.google.com/drive/folders/xxxxx"
}
```

### 3. 楽曲同期

Google Drive共有フォルダからの同期機能。

- `/sync <URL>` で同期実行
- `gdown` ライブラリ使用（認証不要）
- 対応形式: mp3, wav, flac, m4a
- 同期先: `music/` ディレクトリ

### 4. 背景画像

- `assets/background.jpg` を使用
- 静止画をH.264エンコードして配信
- ホットスワップ非対応（シンプル化のため）

---

## Discordコマンド一覧

### 設定コマンド

| コマンド | 説明 | 例 |
|----------|------|-----|
| `/config url <URL>` | 配信先URL設定 | `/config url rtmp://a.rtmp.youtube.com/live2` |
| `/config key <KEY>` | ストリームキー設定 | `/config key xxxx-xxxx-xxxx` |
| `/config show` | 現在の設定表示 | キーは一部マスク表示 |

### 楽曲コマンド

| コマンド | 説明 | 例 |
|----------|------|-----|
| `/sync <URL>` | Google Driveから同期 | `/sync https://drive.google.com/drive/folders/xxx` |
| `/sync status` | 同期状態・楽曲数表示 | |
| `/playlist` | 楽曲一覧表示 | |

### 配信コマンド

| コマンド | 説明 |
|----------|------|
| `/start` | 配信開始 |
| `/stop` | 配信停止 |
| `/skip` | 次の曲へスキップ |
| `/now` | 現在再生中の曲を表示 |
| `/status` | 配信状態表示 |

---

## アーキテクチャ

### 配信フロー

```
┌─────────────────────────────────────────────────────────────┐
│                        VPS (Docker)                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│  │ Discord Bot │───→│ Core Engine │───→│     ffmpeg      │ │
│  │ (commands)  │    │ (Python)    │    │ (H.264 + AAC)   │ │
│  └─────────────┘    └─────────────┘    └────────┬────────┘ │
│         ↑                  ↑                     │          │
│         │                  │                     ↓          │
│  ┌──────┴──────┐    ┌──────┴──────┐    ┌─────────────────┐ │
│  │   Discord   │    │   assets/   │    │  RTMP/RTMPS     │ │
│  │   Server    │    │   music/    │    │  配信プラットフォーム │ │
│  └─────────────┘    └─────────────┘    └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### コンポーネント

| コンポーネント | 役割 |
|----------------|------|
| `main.py` | エントリーポイント、初期化 |
| `config.py` | 環境変数・設定管理 |
| `discord_bot.py` | Discordコマンド処理 |
| `stream_manager.py` | ffmpegプロセス管理、配信制御 |
| `audio_player.py` | 楽曲デコード、PCM出力 |
| `video_generator.py` | 静止画→映像ストリーム生成 |
| `gdrive_sync.py` | Google Drive同期処理 |

---

## 設定ファイル

### .env（必須）

```env
# Discord Bot トークン（必須）
DISCORD_TOKEN=your_discord_bot_token

# 操作を許可するチャンネルID（必須）
DISCORD_CHANNEL_ID=123456789012345678
```

### data/config.json（Discord経由で自動生成）

```json
{
  "stream_url": "rtmp://a.rtmp.youtube.com/live2",
  "stream_key": "xxxx-xxxx-xxxx-xxxx",
  "gdrive_url": "https://drive.google.com/drive/folders/xxxxx",
  "last_sync": "2024-01-15T10:30:00Z"
}
```

---

## ディレクトリ構成

```
minimal/
├── app/
│   ├── main.py              # エントリーポイント
│   ├── config.py            # 設定管理
│   ├── bot/
│   │   ├── __init__.py
│   │   └── discord_bot.py   # Discordコマンド
│   └── core/
│       ├── __init__.py
│       ├── stream_manager.py    # 配信制御
│       ├── audio_player.py      # 音声再生
│       ├── video_generator.py   # 映像生成
│       └── gdrive_sync.py       # Google Drive同期
├── assets/
│   └── background.jpg       # 背景画像
├── music/                   # 楽曲ディレクトリ
│   └── .gitkeep
├── data/                    # 設定・データ保存
│   └── .gitkeep
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── SPEC.md                  # この仕様書
└── README.md                # セットアップガイド
```

---

## 対応プラットフォーム

URLとストリームキーを設定するだけで対応可能。

| プラットフォーム | プロトコル | URL例 |
|------------------|------------|-------|
| YouTube | RTMP | `rtmp://a.rtmp.youtube.com/live2` |
| Twitch | RTMP | `rtmp://live.twitch.tv/app` |
| X (Twitter) | RTMP | `rtmp://x.rtmp.x.com/app` |
| Kick | RTMPS | `rtmps://fa723fc1b171.global-contribute.live-video.net:443/app` |
| Instagram | RTMPS | `rtmps://live-upload.instagram.com:443/rtmp` |
| Facebook | RTMPS | `rtmps://live-api-s.facebook.com:443/rtmp` |

---

## 制限事項

- 配信先は1つのみ（同時マルチプラットフォーム非対応）
- ジャンル分け機能なし
- 背景ホットスワップ非対応
- 配信タイトル動的更新非対応

→ これらの機能が必要な場合は **フル機能版** をご利用ください

---

## フル機能版との比較

| 機能 | Lite版 | フル機能版 |
|------|--------|------------|
| 配信先数 | 1 | 6 (同時配信) |
| 設定方法 | Discord | Discord + .env |
| 楽曲管理 | Google Drive同期 | rclone + ジャンル分け |
| 背景 | 静止画1枚 | 動画対応 + ホットスワップ |
| スケジュール | なし | あり |
| タイトル更新 | なし | YouTube API連携 |

---

## 技術仕様

### 依存ライブラリ

```
discord.py>=2.0
python-dotenv
aiofiles
gdown
```

### ffmpegパラメータ

```bash
ffmpeg \
  -loop 1 -i background.jpg \          # 静止画入力
  -f s16le -ar 48000 -ac 2 -i pipe:0 \ # PCM音声入力
  -c:v libx264 -preset ultrafast \      # 映像エンコード
  -tune stillimage \                    # 静止画最適化
  -r 15 -g 30 \                         # 15fps, GOP=30
  -b:v 500k \                           # 映像500kbps
  -c:a aac -b:a 128k \                  # 音声128kbps
  -f flv "rtmp://..."                   # FLV出力
```

---

## 更新履歴

| バージョン | 日付 | 内容 |
|------------|------|------|
| 0.1.0 | 2024-12-23 | 初版仕様策定 |
