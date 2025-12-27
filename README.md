# SUNO Radio Lite

Discord操作だけで24時間音楽配信を実現するシンプルな配信システム

## 特徴

- **簡単セットアップ**: `.env`にはDiscordトークンだけ
- **Discord完結**: 配信設定も楽曲管理もDiscordから
- **プラットフォーム自由**: YouTube, Twitch, X, Kick... どこでも配信可能
- **Google Drive連携**: 楽曲も背景画像もGoogle Driveから同期
- **ラウドネスノーマライズ**: 楽曲同期時に自動で音量を統一
- **自動復旧**: 配信中にコンテナが再起動しても自動で配信再開

---

## クイックスタート

### 1. 前提条件

- VPS (Ubuntu推奨)
- Docker & Docker Compose
- Discord Bot トークン

### 2. リポジトリ取得

```bash
git clone https://github.com/ex-takashima/suno-radio-lite.git
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
/sync (Google DriveのURLを入力)
/start
```

**以上！配信が始まります**

---

## UIパネル

`/panel` コマンドでボタン操作パネルを表示できます。

ボタンで配信をコントロールできます：
- **【配信】** 開始・停止・スキップ・再生モード
- **【情報】** 再生中・状態・プレイリスト
- **【設定】** 配信設定・楽曲同期・背景同期・設定確認
- **【システム】** システム負荷表示

---

## Discordコマンド

### 配信

| コマンド | 説明 |
|----------|------|
| `/start` | 配信開始 |
| `/stop` | 配信停止 |
| `/skip` | 次の曲へ |
| `/now` | 再生中の曲を表示 |
| `/mode` | 再生モード切替（ファイル名順 ↔ シャッフル） |
| `/status` | 配信状態を確認 |

### 楽曲・背景

| コマンド | 説明 |
|----------|------|
| `/sync` | Google Driveから楽曲を同期 |
| `/background` | Google Driveから背景画像を同期 |
| `/playlist` | 楽曲一覧表示 |

### 設定

| コマンド | 説明 |
|----------|------|
| `/config url <URL>` | 配信先URL設定 |
| `/config key <KEY>` | ストリームキー設定 |
| `/config show` | 現在の設定確認 |

### システム

| コマンド | 説明 |
|----------|------|
| `/system` | CPU/メモリ/ディスク使用状況を表示 |
| `/panel` | UIパネルを表示 |

---

## 楽曲の追加方法

1. Google Driveにフォルダを作成
2. 楽曲ファイル (mp3, wav, flac, m4a, ogg) をアップロード
3. フォルダを「リンクを知っている全員」で共有
4. Discord で `/sync` を実行し、共有URLを入力

同期完了後、自動でラウドネスノーマライズ（EBU R128: -14 LUFS）が行われます。

---

## 背景画像の変更

### Google Driveから同期（おすすめ）

1. Google Driveに背景画像をアップロード
2. ファイルを「リンクを知っている全員」で共有
3. Discord で `/background` を実行し、共有URLを入力

### 直接アップロード

```bash
scp background.jpg user@vps:/opt/suno-radio-lite/assets/
docker compose restart
```

---

## 再生モード

| モード | 説明 |
|--------|------|
| 📑 ファイル名順（デフォルト） | ファイル名でソートして再生、一周後も同じ順序 |
| 🔀 シャッフル | ランダム再生、一周後は再シャッフル |

`/mode` コマンドまたはUIパネルの「再生モード」ボタンで切り替えできます。
配信中でも切り替え可能（現在の曲がスキップされて次の曲から適用）。

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
| 音声サンプルレート | 48000Hz |
| 合計 | 約630kbps |

---

## 自動復旧機能

配信中にコンテナが再起動した場合、自動的に配信を再開します。

- 配信状態は `data/stream_state.json` に保存
- 起動時に前回配信中だったかをチェック
- 配信中だった場合は自動で `/start` を実行

※ `/stop` で正常停止した場合は再起動しても配信は開始しません

---

## システムの更新方法

```bash
cd /opt/suno-radio-lite
git pull
docker compose down
docker compose up -d --build
```

---

## トラブルシューティング

### 配信が始まらない

1. `/config show` で設定を確認
2. ストリームキーが正しいか確認
3. ログを確認: `docker compose logs -f`

### 楽曲が同期されない

1. Google Driveフォルダの共有設定を確認（「リンクを知っている全員」）
2. `/playlist` で楽曲一覧を確認

### 音が出ない

1. `music/` ディレクトリに楽曲があるか確認
2. `/playlist` で楽曲一覧を確認

### システム負荷を確認したい

`/system` コマンドでCPU、メモリ、ディスク使用状況を確認できます。

---

## ディレクトリ構成

```
.
├── app/                 # アプリケーション
├── assets/              # 背景画像
│   └── background.jpg
├── music/               # 楽曲 (同期先)
├── data/                # 設定・状態データ
│   ├── config.json      # 配信設定
│   └── stream_state.json # 配信状態
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
