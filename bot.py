import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_OPTIONS = {
    'options': '-vn'
}
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch1:',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔧 Slash commands synchronisées ({len(synced)})")
    except Exception as e:
        print(f"Erreur lors de la sync : {e}")

@bot.tree.command(name="join", description="Fait rejoindre le salon vocal")
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        await channel.connect()
        await interaction.response.send_message(f"🔊 Rejoint le salon : {channel.name}", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Tu dois être dans un salon vocal !", ephemeral=True)

@bot.tree.command(name="play", description="Joue une musique à partir d’un lien ou d’un mot-clé")
@app_commands.describe(query="Lien YouTube ou mot-clé")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    voice_client = interaction.guild.voice_client
    if not voice_client:
        if interaction.user.voice:
            voice_client = await interaction.user.voice.channel.connect()
        else:
            await interaction.followup.send("❌ Tu dois être dans un salon vocal !")
            return

    try:
        info = ytdl.extract_info(query, download=False)
        url = info['url'] if 'url' in info else info['entries'][0]['url']
        title = info['title'] if 'title' in info else info['entries'][0]['title']
    except Exception as e:
        await interaction.followup.send(f"Erreur lors de la recherche : {str(e)}")
        return

    source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
    voice_client.stop()
    voice_client.play(source)
    await interaction.followup.send(f"🎵 Lecture de : **{title}**")

# Démarrage sécurisé
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN is None:
        print("❌ ERREUR : variable d’environnement DISCORD_TOKEN manquante.")
    else:
        bot.run(TOKEN)
