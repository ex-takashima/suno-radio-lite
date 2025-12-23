"""
SUNO Radio Lite - Discord Bot
シンプルなコマンドセット
"""

import discord
from discord import app_commands
from discord.ext import commands
from config import config


class RadioBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        """Bot起動時の初期化"""
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
# 設定コマンド
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

    embed = discord.Embed(title="現在の設定", color=0x00ff00)
    embed.add_field(name="配信先URL", value=f"`{url}`", inline=False)
    embed.add_field(name="ストリームキー", value=f"`{masked}`", inline=False)
    embed.add_field(name="Google Drive", value=f"`{gdrive}`", inline=False)
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
    success, message = await gdrive_sync.sync(url)

    if success:
        await interaction.followup.send(f"✅ {message}")
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


@bot.tree.command(name="shuffle", description="プレイリストを再シャッフル")
@is_allowed_channel()
async def shuffle_command(interaction: discord.Interaction):
    """プレイリストを再シャッフル"""
    from core.stream_manager import stream_manager

    if stream_manager.shuffle():
        await interaction.response.send_message("🔀 シャッフル完了")
    else:
        await interaction.response.send_message("❌ シャッフルに失敗しました", ephemeral=True)


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
