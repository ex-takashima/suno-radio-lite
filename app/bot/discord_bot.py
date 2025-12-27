"""
SUNO Radio Lite - Discord Bot
シンプルなコマンドセット + UIボタン操作
"""

import asyncio
import discord
from discord import app_commands, ui
from discord.ext import commands
from config import config


class RadioBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        """Bot起動時の初期化"""
        # 永続的なViewを登録
        self.add_view(ControlPanelView())
        await self.tree.sync()
        print("Discordコマンド同期完了", flush=True)

    async def on_ready(self):
        print(f"Discord Bot起動: {self.user}", flush=True)


bot = RadioBot()


def is_allowed_channel():
    """許可されたチャンネルかチェック"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if config.DISCORD_CHANNEL_ID == 0:
            return True
        return interaction.channel_id == config.DISCORD_CHANNEL_ID
    return app_commands.check(predicate)


# =============================================================================
# UIコンポーネント - Modal（入力フォーム）
# =============================================================================

class ConfigModal(ui.Modal, title="⚙️ 配信設定"):
    """配信設定用のModal"""

    url_input = ui.TextInput(
        label="配信先URL",
        placeholder="rtmp://a.rtmp.youtube.com/live2",
        required=False,
        max_length=200
    )

    key_input = ui.TextInput(
        label="ストリームキー",
        placeholder="xxxx-xxxx-xxxx-xxxx-xxxx",
        required=False,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        messages = []

        if self.url_input.value:
            config.set_stream_url(self.url_input.value)
            messages.append(f"配信先URL: `{self.url_input.value}`")

        if self.key_input.value:
            config.set_stream_key(self.key_input.value)
            key = self.key_input.value
            masked = key[:4] + "*" * (len(key) - 8) + key[-4:] if len(key) > 8 else "****"
            messages.append(f"ストリームキー: `{masked}`")

        if messages:
            await config.save()
            await interaction.response.send_message(
                "✅ 設定を保存しました\n" + "\n".join(messages),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "変更はありませんでした",
                ephemeral=True
            )


class SyncModal(ui.Modal, title="📁 楽曲同期"):
    """Google Drive同期用のModal"""

    url_input = ui.TextInput(
        label="Google Drive共有フォルダURL",
        placeholder="https://drive.google.com/drive/folders/...",
        required=False,
        max_length=300,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        from core.gdrive_sync import gdrive_sync
        url = self.url_input.value if self.url_input.value else None
        success, message, details = await gdrive_sync.sync(url)

        if success:
            await interaction.followup.send(f"✅ {message}", ephemeral=True)
            # チャンネルに通知（詳細メッセージ）
            notify_msg = f"📁 楽曲同期が完了しました\n"
            notify_msg += f"　　曲数: {details.get('track_count', 0)}曲"
            if details.get('normalized_count', 0) > 0:
                notify_msg += f"\n　　ノーマライズ: {details.get('normalized_success', 0)}/{details.get('normalized_count', 0)}曲"
            await interaction.channel.send(notify_msg)
        else:
            await interaction.followup.send(f"❌ {message}", ephemeral=True)


class BackgroundModal(ui.Modal, title="🖼️ 背景画像同期"):
    """背景画像同期用のModal"""

    url_input = ui.TextInput(
        label="Google Drive共有ファイルURL",
        placeholder="https://drive.google.com/file/d/...",
        required=False,
        max_length=300,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        from core.gdrive_sync import gdrive_sync
        url = self.url_input.value if self.url_input.value else None
        success, message = await gdrive_sync.sync_background(url)

        if success:
            await interaction.followup.send(f"🖼️ {message}", ephemeral=True)
            # チャンネルに通知
            await interaction.channel.send(f"🖼️ 背景画像の同期が完了しました")
        else:
            await interaction.followup.send(f"❌ {message}", ephemeral=True)


# =============================================================================
# UIコンポーネント - View（ボタンパネル）
# =============================================================================

class ControlPanelView(ui.View):
    """コントロールパネルのボタン群"""

    def __init__(self):
        super().__init__(timeout=None)  # 永続化

    # --- 配信制御 ---

    @ui.button(label="開始", emoji="▶️", style=discord.ButtonStyle.green, custom_id="panel:start", row=0)
    async def start_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        from core.stream_manager import stream_manager
        success, message = await stream_manager.start()
        emoji = "🎬" if success else "❌"
        await interaction.followup.send(f"{emoji} {message}", ephemeral=True)

    @ui.button(label="停止", emoji="⏹️", style=discord.ButtonStyle.red, custom_id="panel:stop", row=0)
    async def stop_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        from core.stream_manager import stream_manager
        success, message = await stream_manager.stop()
        emoji = "🛑" if success else "❌"
        await interaction.followup.send(f"{emoji} {message}", ephemeral=True)

    @ui.button(label="スキップ", emoji="⏭️", style=discord.ButtonStyle.primary, custom_id="panel:skip", row=0)
    async def skip_button(self, interaction: discord.Interaction, button: ui.Button):
        from core.stream_manager import stream_manager
        if stream_manager.skip():
            await interaction.response.send_message("⏭️ スキップしました", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 配信中ではありません", ephemeral=True)

    @ui.button(label="再生モード", emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="panel:mode", row=0)
    async def mode_button(self, interaction: discord.Interaction, button: ui.Button):
        from core.audio_player import audio_player
        new_mode = audio_player.toggle_playback_mode()
        emoji = "🔀" if audio_player.shuffle_mode else "📑"
        await interaction.response.send_message(f"{emoji} 再生モード: {new_mode}", ephemeral=True)

    # --- 情報表示 ---

    @ui.button(label="再生中", emoji="🎵", style=discord.ButtonStyle.secondary, custom_id="panel:now", row=1)
    async def now_button(self, interaction: discord.Interaction, button: ui.Button):
        from core.stream_manager import stream_manager
        status = stream_manager.get_status()

        if not status['is_streaming']:
            await interaction.response.send_message("配信していません", ephemeral=True)
            return

        track = status['current_track']
        if track:
            embed = discord.Embed(title="🎵 Now Playing", color=0x00ff00)
            embed.add_field(name="曲名", value=track['title'], inline=False)
            if 'elapsed_formatted' in track:
                embed.add_field(name="再生時間", value=track['elapsed_formatted'], inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("再生中の曲がありません", ephemeral=True)

    @ui.button(label="状態", emoji="📊", style=discord.ButtonStyle.secondary, custom_id="panel:status", row=1)
    async def status_button(self, interaction: discord.Interaction, button: ui.Button):
        from core.stream_manager import stream_manager
        from core.gdrive_sync import gdrive_sync
        from core.audio_player import audio_player

        stream_status = stream_manager.get_status()
        sync_status = gdrive_sync.get_status()

        embed = discord.Embed(
            title="SUNO Radio Lite",
            color=0x00ff00 if stream_status['is_streaming'] else 0x808080
        )

        if stream_status['is_streaming']:
            embed.add_field(name="状態", value="🟢 配信中", inline=True)
            if stream_status['uptime_formatted']:
                embed.add_field(name="配信時間", value=stream_status['uptime_formatted'], inline=True)
        else:
            embed.add_field(name="状態", value="⚫ 停止中", inline=True)

        if stream_status['current_track']:
            embed.add_field(name="再生中", value=stream_status['current_track']['title'], inline=False)

        embed.add_field(name="楽曲数", value=f"{sync_status['track_count']}曲", inline=True)
        mode_emoji = "🔀" if audio_player.shuffle_mode else "📑"
        embed.add_field(name="再生モード", value=f"{mode_emoji} {audio_player.get_playback_mode()}", inline=True)
        embed.add_field(name="設定", value="✅ 完了" if config.is_configured() else "❌ 未完了", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="プレイリスト", emoji="📋", style=discord.ButtonStyle.secondary, custom_id="panel:playlist", row=1)
    async def playlist_button(self, interaction: discord.Interaction, button: ui.Button):
        from core.gdrive_sync import gdrive_sync

        tracks = gdrive_sync.get_tracks()
        if not tracks:
            await interaction.response.send_message("楽曲がありません", ephemeral=True)
            return

        display_tracks = tracks[:20]
        track_list = "\n".join([f"{i+1}. {t}" for i, t in enumerate(display_tracks)])

        if len(tracks) > 20:
            track_list += f"\n... 他 {len(tracks) - 20} 曲"

        embed = discord.Embed(title=f"楽曲一覧 ({len(tracks)}曲)", description=track_list, color=0x00ff00)

        status = gdrive_sync.get_status()
        if status['last_sync']:
            embed.set_footer(text=f"最終同期: {status['last_sync']}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- 設定 ---

    @ui.button(label="配信設定", emoji="⚙️", style=discord.ButtonStyle.secondary, custom_id="panel:config", row=2)
    async def config_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ConfigModal())

    @ui.button(label="楽曲同期", emoji="📁", style=discord.ButtonStyle.secondary, custom_id="panel:sync", row=2)
    async def sync_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SyncModal())

    @ui.button(label="背景同期", emoji="🖼️", style=discord.ButtonStyle.secondary, custom_id="panel:background", row=2)
    async def background_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(BackgroundModal())

    @ui.button(label="設定確認", emoji="👁️", style=discord.ButtonStyle.secondary, custom_id="panel:showconfig", row=2)
    async def showconfig_button(self, interaction: discord.Interaction, button: ui.Button):
        url = config.get_stream_url() or "(未設定)"
        key = config.get_stream_key()
        if key:
            masked = key[:4] + "*" * (len(key) - 8) + key[-4:] if len(key) > 8 else "****"
        else:
            masked = "(未設定)"

        gdrive = config.get_gdrive_url() or "(未設定)"
        bg_url = config.get_background_url() or "(未設定)"

        embed = discord.Embed(title="現在の設定", color=0x00ff00)
        embed.add_field(name="配信先URL", value=f"`{url}`", inline=False)
        embed.add_field(name="ストリームキー", value=f"`{masked}`", inline=False)
        embed.add_field(name="楽曲フォルダ", value=f"`{gdrive}`", inline=False)
        embed.add_field(name="背景画像", value=f"`{bg_url}`", inline=False)
        embed.add_field(name="設定状態", value="✅ OK" if config.is_configured() else "❌ 未完了", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="システム", emoji="💻", style=discord.ButtonStyle.secondary, custom_id="panel:system", row=3)
    async def system_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)

        try:
            # CPU負荷
            cpu_proc = await asyncio.create_subprocess_shell(
                "cat /proc/loadavg | awk '{print $1, $2, $3}'",
                stdout=asyncio.subprocess.PIPE
            )
            cpu_out, _ = await cpu_proc.communicate()
            load_avg = cpu_out.decode().strip()

            # メモリ使用量
            mem_proc = await asyncio.create_subprocess_shell(
                "free -h | awk 'NR==2{print $3\"/\"$2\" (\"int($3/$2*100)\"%)\"}' ",
                stdout=asyncio.subprocess.PIPE
            )
            mem_out, _ = await mem_proc.communicate()
            memory = mem_out.decode().strip()

            # ディスク使用量
            disk_proc = await asyncio.create_subprocess_shell(
                "df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}'",
                stdout=asyncio.subprocess.PIPE
            )
            disk_out, _ = await disk_proc.communicate()
            disk = disk_out.decode().strip()

            # 楽曲フォルダのサイズ
            music_proc = await asyncio.create_subprocess_shell(
                f"du -sh {config.MUSIC_DIR} 2>/dev/null | awk '{{print $1}}'",
                stdout=asyncio.subprocess.PIPE
            )
            music_out, _ = await music_proc.communicate()
            music_size = music_out.decode().strip() or "N/A"

            embed = discord.Embed(
                title="💻 システム状態",
                color=0x2ECC71
            )
            embed.add_field(name="CPU負荷", value=load_avg, inline=True)
            embed.add_field(name="メモリ", value=memory, inline=True)
            embed.add_field(name="ディスク", value=disk, inline=True)
            embed.add_field(name="楽曲フォルダ", value=music_size, inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ エラー: {str(e)}", ephemeral=True)


# =============================================================================
# パネルコマンド
# =============================================================================

@bot.tree.command(name="panel", description="コントロールパネルを表示")
@is_allowed_channel()
async def panel_command(interaction: discord.Interaction):
    """コントロールパネルを表示"""
    embed = discord.Embed(
        title="🎵 SUNO Radio Lite",
        description="ボタンで配信をコントロールできます",
        color=0x5865F2
    )
    embed.add_field(
        name="【配信】",
        value="開始・停止・スキップ・再生モード",
        inline=False
    )
    embed.add_field(
        name="【情報】",
        value="再生中・状態・プレイリスト",
        inline=False
    )
    embed.add_field(
        name="【設定】",
        value="配信設定・楽曲同期・背景同期・設定確認",
        inline=False
    )
    embed.add_field(
        name="【システム】",
        value="システム負荷表示",
        inline=False
    )

    await interaction.response.send_message(embed=embed, view=ControlPanelView())


# =============================================================================
# 設定コマンド（スラッシュコマンド版 - 従来互換）
# =============================================================================

config_group = app_commands.Group(name="config", description="配信設定")


@config_group.command(name="url", description="配信先URLを設定")
@is_allowed_channel()
async def config_url(interaction: discord.Interaction, url: str):
    """配信先URLを設定"""
    config.set_stream_url(url)
    await config.save()
    await interaction.response.send_message(f"配信先URL設定: `{url}`", ephemeral=True)


@config_group.command(name="key", description="ストリームキーを設定")
@is_allowed_channel()
async def config_key(interaction: discord.Interaction, key: str):
    """ストリームキーを設定"""
    config.set_stream_key(key)
    await config.save()
    # キーは一部マスク
    masked = key[:4] + "*" * (len(key) - 8) + key[-4:] if len(key) > 8 else "****"
    await interaction.response.send_message(f"ストリームキー設定: `{masked}`", ephemeral=True)


@config_group.command(name="show", description="現在の設定を表示")
@is_allowed_channel()
async def config_show(interaction: discord.Interaction):
    """現在の設定を表示"""
    url = config.get_stream_url() or "(未設定)"
    key = config.get_stream_key()
    if key:
        masked = key[:4] + "*" * (len(key) - 8) + key[-4:] if len(key) > 8 else "****"
    else:
        masked = "(未設定)"

    gdrive = config.get_gdrive_url() or "(未設定)"
    bg_url = config.get_background_url() or "(未設定)"

    embed = discord.Embed(title="現在の設定", color=0x00ff00)
    embed.add_field(name="配信先URL", value=f"`{url}`", inline=False)
    embed.add_field(name="ストリームキー", value=f"`{masked}`", inline=False)
    embed.add_field(name="楽曲フォルダ", value=f"`{gdrive}`", inline=False)
    embed.add_field(name="背景画像", value=f"`{bg_url}`", inline=False)
    embed.add_field(name="設定状態", value="OK" if config.is_configured() else "未完了", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.tree.add_command(config_group)


# =============================================================================
# 同期コマンド
# =============================================================================

@bot.tree.command(name="sync", description="Google Driveから楽曲を同期")
@is_allowed_channel()
@app_commands.describe(url="Google Drive共有フォルダURL（省略時は保存済みURLを使用）")
async def sync_command(interaction: discord.Interaction, url: str = None):
    """Google Driveから楽曲を同期"""
    await interaction.response.defer()

    from core.gdrive_sync import gdrive_sync
    success, message, details = await gdrive_sync.sync(url)

    if success:
        # 詳細メッセージを作成
        embed = discord.Embed(title="📁 楽曲同期完了", color=0x00ff00)
        embed.add_field(name="曲数", value=f"{details.get('track_count', 0)}曲", inline=True)
        if details.get('normalized_count', 0) > 0:
            embed.add_field(
                name="ノーマライズ",
                value=f"{details.get('normalized_success', 0)}/{details.get('normalized_count', 0)}曲",
                inline=True
            )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ {message}")


@bot.tree.command(name="playlist", description="楽曲一覧を表示")
@is_allowed_channel()
async def playlist_command(interaction: discord.Interaction):
    """楽曲一覧を表示"""
    from core.gdrive_sync import gdrive_sync

    tracks = gdrive_sync.get_tracks()
    if not tracks:
        await interaction.response.send_message("楽曲がありません", ephemeral=True)
        return

    # 最大20曲表示
    display_tracks = tracks[:20]
    track_list = "\n".join([f"{i+1}. {t}" for i, t in enumerate(display_tracks)])

    if len(tracks) > 20:
        track_list += f"\n... 他 {len(tracks) - 20} 曲"

    embed = discord.Embed(title=f"楽曲一覧 ({len(tracks)}曲)", description=track_list, color=0x00ff00)

    status = gdrive_sync.get_status()
    if status['last_sync']:
        embed.set_footer(text=f"最終同期: {status['last_sync']}")

    await interaction.response.send_message(embed=embed)


# =============================================================================
# 配信コマンド
# =============================================================================

@bot.tree.command(name="start", description="配信を開始")
@is_allowed_channel()
async def start_command(interaction: discord.Interaction):
    """配信を開始"""
    await interaction.response.defer()

    from core.stream_manager import stream_manager
    success, message = await stream_manager.start()

    if success:
        await interaction.followup.send(f"🎬 {message}")
    else:
        await interaction.followup.send(f"❌ {message}")


@bot.tree.command(name="stop", description="配信を停止")
@is_allowed_channel()
async def stop_command(interaction: discord.Interaction):
    """配信を停止"""
    await interaction.response.defer()

    from core.stream_manager import stream_manager
    success, message = await stream_manager.stop()

    if success:
        await interaction.followup.send(f"🛑 {message}")
    else:
        await interaction.followup.send(f"❌ {message}")


@bot.tree.command(name="skip", description="次の曲へスキップ")
@is_allowed_channel()
async def skip_command(interaction: discord.Interaction):
    """次の曲へスキップ"""
    from core.stream_manager import stream_manager

    if stream_manager.skip():
        await interaction.response.send_message("⏭️ スキップ")
    else:
        await interaction.response.send_message("❌ 配信中ではありません", ephemeral=True)


@bot.tree.command(name="now", description="現在再生中の曲を表示")
@is_allowed_channel()
async def now_command(interaction: discord.Interaction):
    """現在再生中の曲を表示"""
    from core.stream_manager import stream_manager

    status = stream_manager.get_status()

    if not status['is_streaming']:
        await interaction.response.send_message("配信していません", ephemeral=True)
        return

    track = status['current_track']
    if track:
        embed = discord.Embed(title="🎵 Now Playing", color=0x00ff00)
        embed.add_field(name="曲名", value=track['title'], inline=False)
        if 'elapsed_formatted' in track:
            embed.add_field(name="再生時間", value=track['elapsed_formatted'], inline=True)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("再生中の曲がありません")


@bot.tree.command(name="status", description="配信状態を表示")
@is_allowed_channel()
async def status_command(interaction: discord.Interaction):
    """配信状態を表示"""
    from core.stream_manager import stream_manager
    from core.gdrive_sync import gdrive_sync

    stream_status = stream_manager.get_status()
    sync_status = gdrive_sync.get_status()

    embed = discord.Embed(
        title="SUNO Radio Lite",
        color=0x00ff00 if stream_status['is_streaming'] else 0x808080
    )

    # 配信状態
    if stream_status['is_streaming']:
        embed.add_field(name="状態", value="🟢 配信中", inline=True)
        if stream_status['uptime_formatted']:
            embed.add_field(name="配信時間", value=stream_status['uptime_formatted'], inline=True)
    else:
        embed.add_field(name="状態", value="⚫ 停止中", inline=True)

    # 現在の曲
    if stream_status['current_track']:
        embed.add_field(
            name="再生中",
            value=stream_status['current_track']['title'],
            inline=False
        )

    # 楽曲数
    embed.add_field(name="楽曲数", value=f"{sync_status['track_count']}曲", inline=True)

    # 設定状態
    embed.add_field(
        name="設定",
        value="✅ 完了" if config.is_configured() else "❌ 未完了",
        inline=True
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="mode", description="再生モードを切り替え（ファイル名順 ↔ シャッフル）")
@is_allowed_channel()
async def mode_command(interaction: discord.Interaction):
    """再生モードを切り替え"""
    from core.audio_player import audio_player

    new_mode = audio_player.toggle_playback_mode()
    emoji = "🔀" if audio_player.shuffle_mode else "📑"
    await interaction.response.send_message(f"{emoji} 再生モード: {new_mode}")


# =============================================================================
# 背景画像コマンド
# =============================================================================

@bot.tree.command(name="background", description="Google Driveから背景画像を同期")
@is_allowed_channel()
@app_commands.describe(url="Google Drive共有ファイルURL（省略時は保存済みURLを使用）")
async def background_command(interaction: discord.Interaction, url: str = None):
    """Google Driveから背景画像を同期"""
    await interaction.response.defer()

    from core.gdrive_sync import gdrive_sync
    success, message = await gdrive_sync.sync_background(url)

    if success:
        await interaction.followup.send(f"🖼️ {message}")
    else:
        await interaction.followup.send(f"❌ {message}")


# =============================================================================
# システムコマンド
# =============================================================================

@bot.tree.command(name="system", description="システム状態を表示（CPU・メモリ・ディスク）")
@is_allowed_channel()
async def system_command(interaction: discord.Interaction):
    """システム状態を表示"""
    await interaction.response.defer()

    try:
        # CPU負荷
        cpu_proc = await asyncio.create_subprocess_shell(
            "cat /proc/loadavg | awk '{print $1, $2, $3}'",
            stdout=asyncio.subprocess.PIPE
        )
        cpu_out, _ = await cpu_proc.communicate()
        load_avg = cpu_out.decode().strip()

        # メモリ使用量
        mem_proc = await asyncio.create_subprocess_shell(
            "free -h | awk 'NR==2{print $3\"/\"$2\" (\"int($3/$2*100)\"%)\"}' ",
            stdout=asyncio.subprocess.PIPE
        )
        mem_out, _ = await mem_proc.communicate()
        memory = mem_out.decode().strip()

        # ディスク使用量
        disk_proc = await asyncio.create_subprocess_shell(
            "df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}'",
            stdout=asyncio.subprocess.PIPE
        )
        disk_out, _ = await disk_proc.communicate()
        disk = disk_out.decode().strip()

        # 楽曲フォルダのサイズ
        music_proc = await asyncio.create_subprocess_shell(
            f"du -sh {config.MUSIC_DIR} 2>/dev/null | awk '{{print $1}}'",
            stdout=asyncio.subprocess.PIPE
        )
        music_out, _ = await music_proc.communicate()
        music_size = music_out.decode().strip() or "N/A"

        embed = discord.Embed(
            title="💻 システム状態",
            color=0x2ECC71
        )
        embed.add_field(name="CPU負荷", value=load_avg, inline=True)
        embed.add_field(name="メモリ", value=memory, inline=True)
        embed.add_field(name="ディスク", value=disk, inline=True)
        embed.add_field(name="楽曲フォルダ", value=music_size, inline=True)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ エラー: {str(e)}")


# =============================================================================
# エラーハンドリング
# =============================================================================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "このチャンネルではコマンドを使用できません",
            ephemeral=True
        )
    else:
        print(f"コマンドエラー: {error}", flush=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"エラーが発生しました: {str(error)[:100]}",
                ephemeral=True
            )
