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

# --- Contrôles musique (boutons) ---
class MusicControls(discord.ui.View):
    def __init__(self, voice_client: discord.VoiceClient):
        super().__init__(timeout=None)
        self.voice_client = voice_client
        self.looping = False
        self.current_source = None

    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.secondary, custom_id="pause_resume")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.voice_client.is_playing():
            self.voice_client.pause()
            button.label = "▶️ Reprendre"
        elif self.voice_client.is_paused():
            self.voice_client.resume()
            button.label = "⏸️ Pause"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="⏮️ Rejouer", style=discord.ButtonStyle.secondary, custom_id="back")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_source:
            self.voice_client.stop()
            self.voice_client.play(self.current_source)
            await interaction.response.send_message("🔁 Relecture depuis le début", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Aucune musique en cours.", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.danger, custom_id="skip")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.voice_client.stop()
            await interaction.response.send_message("⏭️ Musique arrêtée", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Aucune musique en cours.", ephemeral=True)

    @discord.ui.button(label="🔁 Loop: OFF", style=discord.ButtonStyle.primary, custom_id="loop")
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.looping = not self.looping
        button.label = f"🔁 Loop: {'ON' if self.looping else 'OFF'}"
        await interaction.response.edit_message(view=self)


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
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ Tu dois être dans un salon vocal pour que je te rejoigne.", ephemeral=True)
        return

    try:
        channel = interaction.user.voice.channel
        await channel.connect()
        await interaction.response.send_message(f"🔊 Je t’ai rejoint dans **{channel.name}** !", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur en rejoignant le vocal : {e}", ephemeral=True)


@bot.tree.command(name="play", description="Joue une musique à partir d’un lien ou d’un mot-clé")
@app_commands.describe(query="Lien YouTube ou mot-clé")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    print(f"[DEBUG] /play reçu avec query : {query}")

    voice_client = interaction.guild.voice_client
    if not voice_client:
        if interaction.user.voice:
            voice_client = await interaction.user.voice.channel.connect()
            print(f"[DEBUG] Bot connecté au vocal : {interaction.user.voice.channel.name}")
        else:
            await interaction.followup.send("❌ Tu dois être dans un salon vocal !")
            return

    try:
        info = ytdl.extract_info(query, download=False)
        print(f"[DEBUG] Info extraite : {info}")
        url = info['url'] if 'url' in info else info['entries'][0]['url']
        title = info['title'] if 'title' in info else info['entries'][0]['title']
    except Exception as e:
        print(f"[ERREUR yt-dlp] {e}")
        await interaction.followup.send(f"Erreur lors de la recherche : {str(e)}")
        return

    try:
        source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
        print("[DEBUG] Source audio chargée")
    except Exception as e:
        print(f"[ERREUR FFmpeg] {e}")
        await interaction.followup.send(f"Erreur lors de la lecture audio : {str(e)}")
        return

    voice_client.stop()
    voice_client.play(source)

    view = MusicControls(voice_client)
    view.current_source = source

    async def check_loop():
        while True:
            await asyncio.sleep(1)
            if not voice_client.is_playing() and view.looping and view.current_source:
                print("[DEBUG] Relance de la musique en boucle")
                voice_client.play(view.current_source)

    bot.loop.create_task(check_loop())

    await interaction.followup.send(
        f"🎵 Lecture de : **{title}**",
        view=view
    )


if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN is None:
        print("❌ Variable DISCORD_TOKEN manquante.")
    else:
        bot.run(TOKEN)
