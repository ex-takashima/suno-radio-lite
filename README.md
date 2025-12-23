# SUNO Radio Lite

Discord操作だけで24時間音楽配信を実現するシンプルな配信システム

## 特徴

- **簡単セットアップ**: `.env`にはDiscordトークンだけ
- **Discord完結**: 配信設定も楽曲管理もDiscordから
- **プラットフォーム自由**: YouTube, Twitch, X, Kick... どこでも配信可能
- **Google Drive連携**: ブラウザで楽曲アップロード → `/sync` で同期

---

## クイックスタート

### 1. 前提条件

- VPS (Ubuntu推奨)
- Docker & Docker Compose
- Discord Bot トークン

### 2. リポジトリ取得

```bash
git clone https://github.com/yourname/suno-radio-lite.git
cd suno-radio-lite
```

### 3. 環境変数設定

```bash
cp .env.example .env
nano .env
```

```env
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id
```

### 4. 起動

```bash
docker compose up -d
```

### 5. Discordで設定

```
/config url rtmp://a.rtmp.youtube.com/live2
/config key your-stream-key
/sync https://drive.google.com/drive/folders/xxxxx
/start
```

**以上！配信が始まります**

---

## Discordコマンド

### 設定

| コマンド | 説明 |
|----------|------|
| `/config url <URL>` | 配信先URL設定 |
| `/config key <KEY>` | ストリームキー設定 |
| `/config show` | 現在の設定確認 |

### 楽曲

| コマンド | 説明 |
|----------|------|
| `/sync <URL>` | Google Driveから楽曲同期 |
| `/sync status` | 同期状態確認 |
| `/playlist` | 楽曲一覧表示 |

### 配信

| コマンド | 説明 |
|----------|------|
| `/start` | 配信開始 |
| `/stop` | 配信停止 |
| `/skip` | 次の曲へ |
| `/now` | 再生中の曲を表示 |

---

## 楽曲の追加方法

1. Google Driveにフォルダを作成
2. 楽曲ファイル (mp3, wav, flac, m4a) をアップロード
3. フォルダを「リンクを知っている全員」で共有
4. Discord で `/sync <共有URL>` を実行

---

## 配信先の設定例

### YouTube

```
/config url rtmp://a.rtmp.youtube.com/live2
/config key xxxx-xxxx-xxxx-xxxx
```

ストリームキーは [YouTube Studio](https://studio.youtube.com/) → ライブ配信 → ストリームキー からコピー

### Twitch

```
/config url rtmp://live.twitch.tv/app
/config key live_xxxxxxxxxx
```

ストリームキーは [Twitch Creator Dashboard](https://dashboard.twitch.tv/) → 設定 → 配信 からコピー

### Kick

```
/config url rtmps://fa723fc1b171.global-contribute.live-video.net:443/app
/config key your_kick_stream_key
```

※ KickはRTMPS（SSL）を使用

---

## 配信スペック

| 項目 | 値 |
|------|-----|
| 解像度 | 480p (854x480) |
| フレームレート | 15fps |
| 映像ビットレート | 500kbps |
| 音声ビットレート | 128kbps |
| 合計 | 約630kbps |

---

## 背景画像の変更

`assets/background.jpg` を差し替えて再起動

```bash
# 画像を差し替え後
docker compose restart
```

---

## トラブルシューティング

### 配信が始まらない

1. `/config show` で設定を確認
2. ストリームキーが正しいか確認
3. ログを確認: `docker compose logs -f`

### 楽曲が同期されない

1. Google Driveフォルダの共有設定を確認（「リンクを知っている全員」）
2. `/sync status` で状態確認

### 音が出ない

1. `music/` ディレクトリに楽曲があるか確認
2. `/playlist` で楽曲一覧を確認

---

## ディレクトリ構成

```
.
├── app/                 # アプリケーション
├── assets/              # 背景画像
│   └── background.jpg
├── music/               # 楽曲 (同期先)
├── data/                # 設定データ
├── docker-compose.yml
├── Dockerfile
├── .env                 # 環境変数
└── README.md
```

---

## フル機能版

より高度な機能が必要な場合は **SUNO Radio フル機能版** をご検討ください。

- マルチプラットフォーム同時配信 (YouTube + Twitch + X + Kick...)
- ジャンル別プレイリスト
- 時間帯スケジュール配信
- 背景動画・ホットスワップ
- YouTubeタイトル自動更新

---

## ライセンス

MIT License
