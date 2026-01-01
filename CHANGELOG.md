# Changelog

All notable changes to SUNO Radio Lite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 状態表示に同期/ノーマライズ進捗を表示
- 2パスラウドネスノーマライズ（より正確な音量調整）
- 同期後プレイリスト自動更新
- 楽曲入れ替え機能（`/sync replace:True`）

### Changed
- ノーマライズ処理を1パスから2パスに変更

## [v0.2.0] - 2024-12-27

### Added
- UIパネル機能（`/panel` コマンド）
  - 配信制御ボタン（開始/停止/スキップ/再生モード）
  - 情報表示ボタン（再生中/状態/プレイリスト）
  - 設定ボタン（配信設定/楽曲同期/背景同期/設定確認）
  - システム状態表示
- `/system` コマンド（CPU・メモリ・ディスク使用状況）
- 再生モード切替機能（ファイル名順 ↔ シャッフル）
- 自動復旧機能（コンテナ再起動時に配信自動再開）
- 背景画像のGoogle Drive同期（`/background` コマンド）
- ラウドネスノーマライズ機能（EBU R128: -14 LUFS）
- 同期完了通知
- GitHub Issue テンプレート

### Changed
- デフォルト再生順序をファイル名順に変更

### Fixed
- ffmpegノーマライズの出力フォーマット指定

## [v0.1.0] - 2024-12-25

### Added
- 初期リリース
- Discord Bot による配信制御
- Google Drive 楽曲同期
- RTMP/RTMPS 配信対応
- 基本コマンド（/start, /stop, /skip, /now, /status, /config, /sync, /playlist）
