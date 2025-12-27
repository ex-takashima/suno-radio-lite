# SUNO Radio Lite - 仕様書

## 概要

SUNO Radio Liteは、Discord操作だけで24時間音楽配信を実現するシンプルな配信システムです。
技術的な知識がなくても、VPS + Docker + Discord Botだけで配信を始められます。

## コンセプト

**「.envにはDISCORD_TOKENだけ。あとはDiscordから全部設定」**

- 配信設定（URL/キー）: `/config` コマンド
- 楽曲管理: Google Drive + `/sync` コマンド
- 背景画像: Google Drive + `/background` コマンド
- 配信操作: `/start`, `/stop`, `/skip`, `/mode`

---

## 機能仕様

### 1. 配信機能

| 項目 | 仕様 |
|------|------|
| プロトコル | RTMP / RTMPS |
| 配信先 | 任意（YouTube, Twitch, X, Kick等） |
| 映像 | 静止画1枚 (H.264) |
| 音声 | 楽曲再生 (AAC) |
| 解像度 | 480p (854x480) |
| 映像ビットレート | 500kbps |
| 音声ビットレート | 128kbps |
| 音声サンプルレート | 48000Hz |
| フレームレート | 15fps |

### 2. 再生モード

| モード | 説明 |
|--------|------|
| ファイル名順（デフォルト） | ファイル名でソートして再生、一周後も同じ順序 |
| シャッフル | ランダム再生、一周後は再シャッフル |

`/mode` コマンドまたはUIパネルで切り替え可能。配信中でも切り替え可能。

### 3. 設定管理

Discord `/config` コマンドで設定を管理。設定は `data/config.json` に永続化。

```json
{
  "stream_url": "rtmp://a.rtmp.youtube.com/live2",
  "stream_key": "xxxx-xxxx-xxxx-xxxx",
  "gdrive_url": "https://drive.google.com/drive/folders/xxxxx",
  "background_url": "https://drive.google.com/file/d/xxxxx"
}
```

### 4. 楽曲同期

Google Drive共有フォルダからの同期機能。

- `/sync` でモーダル表示、URLを入力して同期実行
- `gdown` ライブラリ使用（認証不要）
- 対応形式: mp3, wav, flac, m4a, ogg
- 同期先: `music/` ディレクトリ
- 同期完了後、自動でラウドネスノーマライズ（EBU R128: -14 LUFS）

### 5. 背景画像

- `/background` でGoogle Driveから同期可能
- 静止画をH.264エンコードして配信
- 同期先: `assets/background.jpg`

### 6. 自動復旧機能

配信中にコンテナが再起動した場合、自動で配信を再開。

- 配信状態は `data/stream_state.json` に保存
- 起動時に前回配信中だったかをチェック
- `/stop` で正常停止した場合は再起動しても配信開始しない

### 7. システム監視

`/system` コマンドでシステム負荷を確認可能。

- CPU負荷（Load Average）
- メモリ使用量
- ディスク使用量
- 楽曲フォルダサイズ

---

## UIパネル

`/panel` コマンドでボタン操作パネルを表示。

| カテゴリ | ボタン |
|----------|--------|
| 配信 | 開始・停止・スキップ・再生モード |
| 情報 | 再生中・状態・プレイリスト |
| 設定 | 配信設定・楽曲同期・背景同期・設定確認 |
| システム | システム負荷表示 |

---

## Discordコマンド一覧

### 設定コマンド

| コマンド | 説明 | 例 |
|----------|------|-----|
| `/config url <URL>` | 配信先URL設定 | `/config url rtmp://a.rtmp.youtube.com/live2` |
| `/config key <KEY>` | ストリームキー設定 | `/config key xxxx-xxxx-xxxx` |
| `/config show` | 現在の設定表示 | キーは一部マスク表示 |

### 楽曲・背景コマンド

| コマンド | 説明 |
|----------|------|
| `/sync` | Google Driveから楽曲を同期（モーダル表示） |
| `/background` | Google Driveから背景画像を同期（モーダル表示） |
| `/playlist` | 楽曲一覧表示 |

### 配信コマンド

| コマンド | 説明 |
|----------|------|
| `/start` | 配信開始 |
| `/stop` | 配信停止 |
| `/skip` | 次の曲へスキップ |
| `/now` | 現在再生中の曲を表示 |
| `/mode` | 再生モード切替（ファイル名順 ↔ シャッフル） |
| `/status` | 配信状態表示 |

### システムコマンド

| コマンド | 説明 |
|----------|------|
| `/panel` | UIパネル表示 |
| `/system` | システム負荷表示 |

---

## アーキテクチャ

### 配信フロー（Lite版：直接配信）

```
┌─────────────────────────────────────────────────────────────┐
│                        VPS (Docker)                         │
│                                                             │
│  ┌─────────────┐                                            │
│  │ Discord Bot │ ←────── Discord Server                     │
│  │ (commands)  │                                            │
│  └──────┬──────┘                                            │
│         │                                                   │
│         ↓                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Core Engine (Python)                    │   │
│  │  ┌───────────────┐    ┌───────────────┐             │   │
│  │  │ VideoGenerator│    │  AudioPlayer  │             │   │
│  │  │  (背景画像)    │    │  (楽曲再生)   │             │   │
│  │  └───────┬───────┘    └───────┬───────┘             │   │
│  │          │ rawvideo           │ PCM                  │   │
│  │          ↓                    ↓                      │   │
│  │       Video FIFO          Audio FIFO                 │   │
│  │          │                    │                      │   │
│  │          └────────┬───────────┘                      │   │
│  │                   ↓                                  │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │     FFmpeg (H.264 + AAC → FLV)              │    │   │
│  │  └─────────────────────┬───────────────────────┘    │   │
│  └────────────────────────│────────────────────────────┘   │
│                           │                                 │
│                           ↓ RTMP/RTMPS                      │
└───────────────────────────│─────────────────────────────────┘
                            ↓
              ┌─────────────────────────────┐
              │   配信プラットフォーム        │
              │  (YouTube/Twitch/Kick等)    │
              └─────────────────────────────┘
```

※ Lite版はnginx-rtmpを使用せず、FFmpegから直接配信先に送信

### コンポーネント

| コンポーネント | 役割 |
|----------------|------|
| `main.py` | エントリーポイント、初期化 |
| `config.py` | 環境変数・設定管理 |
| `discord_bot.py` | Discordコマンド・UIパネル処理 |
| `stream_manager.py` | ffmpegプロセス管理、配信制御、自動復旧 |
| `audio_player.py` | 楽曲デコード、PCM出力、再生モード管理 |
| `video_generator.py` | 静止画→映像ストリーム生成 |
| `gdrive_sync.py` | Google Drive同期、ラウドネスノーマライズ |

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
  "background_url": "https://drive.google.com/file/d/xxxxx"
}
```

### data/stream_state.json（自動生成）

```json
{
  "streaming": true,
  "timestamp": "2024-12-28T10:30:00"
}
```

---

## ディレクトリ構成

```
suno-radio-lite/
├── app/
│   ├── main.py              # エントリーポイント
│   ├── config.py            # 設定管理
│   ├── bot/
│   │   ├── __init__.py
│   │   └── discord_bot.py   # Discordコマンド・UIパネル
│   └── core/
│       ├── __init__.py
│       ├── stream_manager.py    # 配信制御・自動復旧
│       ├── audio_player.py      # 音声再生・再生モード
│       ├── video_generator.py   # 映像生成
│       └── gdrive_sync.py       # Google Drive同期・ノーマライズ
├── assets/
│   └── background.jpg       # 背景画像
├── music/                   # 楽曲ディレクトリ
│   └── .gitkeep
├── data/                    # 設定・状態データ
│   ├── config.json          # 配信設定
│   └── stream_state.json    # 配信状態
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
- 背景ホットスワップ非対応（配信中の背景変更は次回起動時に反映）
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
| 再生モード | ファイル名順/シャッフル | ジャンル別 + シャッフル |
| 自動復旧 | あり | あり |

---

## 技術仕様

### 依存ライブラリ

```
discord.py>=2.0
python-dotenv
aiofiles
gdown
```

### ffmpegパラメータ（StreamManager）

```bash
ffmpeg \
  -thread_queue_size 512 \
  -f rawvideo -pix_fmt yuv420p -s 854x480 -r 15 \
  -i video_fifo \                              # 映像FIFO入力
  -thread_queue_size 512 \
  -f s16le -ar 48000 -ac 2 \
  -i audio_fifo \                              # 音声FIFO入力
  -c:v libx264 -preset ultrafast -tune stillimage \
  -b:v 500k -maxrate 500k -bufsize 1000k \
  -r 15 -g 30 -keyint_min 30 -sc_threshold 0 \
  -c:a aac -b:a 128k -ar 48000 -ac 2 \
  -f flv -flvflags no_duration_filesize \
  "rtmp://..."
```

### ラウドネスノーマライズ

```bash
ffmpeg -i input.mp3 \
  -af loudnorm=I=-14:TP=-1:LRA=11 \
  -ar 48000 -c:a libmp3lame -q:a 2 \
  output.mp3
```

- 目標ラウドネス: -14 LUFS（EBU R128準拠）
- True Peak: -1 dB

---

## 更新履歴

| バージョン | 日付 | 内容 |
|------------|------|------|
| 0.1.0 | 2024-12-23 | 初版仕様策定 |
| 0.2.0 | 2024-12-28 | 背景同期、再生モード、自動復旧、システム監視追加 |
