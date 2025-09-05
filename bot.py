import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import random
import asyncio
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# -------- MUSIC SYSTEM -------- #
music_queues = {}

def get_music_queue(guild_id):
    if guild_id not in music_queues:
        music_queues[guild_id] = []
    return music_queues[guild_id]

async def play_next(ctx):
    queue = get_music_queue(ctx.guild.id)
    if len(queue) > 0:
        url = queue.pop(0)
        await play_music(ctx, url)
    else:
        await ctx.voice_client.disconnect()

async def play_music(ctx, url):
    ydl_opts = {"format": "bestaudio", "quiet": True}
    vc = ctx.voice_client

    if not vc:
        vc = await ctx.author.voice.channel.connect()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info["url"]
        title = info["title"]

    vc.play(discord.FFmpegPCMAudio(audio_url, executable="ffmpeg", options="-vn"),
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
    await ctx.send(f"🎶 **Now Playing:** {title}")

# /play command
@bot.tree.command(name="play", description="Play a song from YouTube or Spotify")
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You must join a voice channel first!")
        return

    ctx = await bot.get_context(interaction)
    queue = get_music_queue(interaction.guild.id)

    if ctx.voice_client and ctx.voice_client.is_playing():
        queue.append(url)
        await interaction.response.send_message(f"➕ Added to queue: **{url}**")
    else:
        await interaction.response.defer()
        await play_music(ctx, url)
        await interaction.followup.send(f"🎶 Playing: **{url}**")

# /pause command
@bot.tree.command(name="pause", description="Pause the current song")
async def pause(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        await interaction.response.send_message("⏸️ Music paused.")
    else:
        await interaction.response.send_message("❌ Nothing is playing.")

# /resume command
@bot.tree.command(name="resume", description="Resume the paused song")
async def resume(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        await interaction.response.send_message("▶️ Music resumed.")
    else:
        await interaction.response.send_message("❌ No music to resume.")

# /skip command
@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("⏭️ Skipped the song.")
    else:
        await interaction.response.send_message("❌ Nothing to skip.")

# /stop command
@bot.tree.command(name="stop", description="Stop music and clear the queue")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        music_queues[interaction.guild.id] = []
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("🛑 Music stopped & queue cleared.")
    else:
        await interaction.response.send_message("❌ Bot is not connected to a voice channel.")

# /queue command
@bot.tree.command(name="queue", description="Show the current music queue")
async def queue(interaction: discord.Interaction):
    queue = get_music_queue(interaction.guild.id)
    if len(queue) == 0:
        await interaction.response.send_message("📭 The music queue is empty.")
    else:
        queue_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(queue)])
        await interaction.response.send_message(f"🎵 **Music Queue:**\n{queue_list}")

# -------- BOT EVENTS -------- #
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Slash sync failed: {e}")

# -------- XP SYSTEM -------- #
user_xp = {}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    xp_gain = random.randint(5, 15)
    user_xp[message.author.id] = user_xp.get(message.author.id, 0) + xp_gain

    xp = user_xp[message.author.id]
    level = xp // 100
    if xp % 100 < xp_gain and level > 0:
        await message.channel.send(f"🎉 {message.author.mention} leveled up to **Level {level}**!")
    await bot.process_commands(message)

# -------- ECONOMY SYSTEM -------- #
user_balance = {}

@bot.tree.command(name="balance", description="Check your wallet balance")
async def balance(interaction: discord.Interaction):
    bal = user_balance.get(interaction.user.id, 0)
    await interaction.response.send_message(f"💰 {interaction.user.mention}, your balance is **${bal}**.")

@bot.tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    reward = random.randint(50, 200)
    user_balance[interaction.user.id] = user_balance.get(interaction.user.id, 0) + reward
    await interaction.response.send_message(f"🎁 {interaction.user.mention}, you claimed **${reward}**!")

# -------- START BOT -------- #
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ Missing DISCORD_TOKEN in .env")
else:
    bot.run(TOKEN)

