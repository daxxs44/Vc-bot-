import discord
from discord.ext import commands
from discord import app_commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Track VC owners
vc_owners = {}  # {channel_id: user_id}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(e)

def is_vc_owner_or_admin(user: discord.Member, vc: discord.VoiceChannel):
    """Check if user is the VC owner or an admin"""
    if vc_owners.get(vc.id) == user.id:
        return True
    if user.guild_permissions.administrator:
        return True
    return False

# Create VC
@bot.tree.command(name="createvc", description="Create a temporary voice channel")
async def createvc(interaction: discord.Interaction, name: str, user_limit: int = 0):
    guild = interaction.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True)
    }
    vc = await guild.create_voice_channel(name, overwrites=overwrites, user_limit=user_limit)
    vc_owners[vc.id] = interaction.user.id
    await interaction.response.send_message(f"VC `{name}` created! You are the owner.", ephemeral=True)

# Delete VC
@bot.tree.command(name="deletevc", description="Delete a voice channel you created or if you are admin")
async def deletevc(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if not is_vc_owner_or_admin(interaction.user, channel):
        await interaction.response.send_message("You cannot manage this VC!", ephemeral=True)
        return
    await channel.delete()
    vc_owners.pop(channel.id, None)
    await interaction.response.send_message(f"VC `{channel.name}` deleted.", ephemeral=True)

# Rename VC
@bot.tree.command(name="renamevc", description="Rename your voice channel")
async def renamevc(interaction: discord.Interaction, channel: discord.VoiceChannel, new_name: str):
    if not is_vc_owner_or_admin(interaction.user, channel):
        await interaction.response.send_message("You cannot manage this VC!", ephemeral=True)
        return
    await channel.edit(name=new_name)
    await interaction.response.send_message(f"VC renamed to `{new_name}`.", ephemeral=True)

# Change user limit
@bot.tree.command(name="limitvc", description="Change the user limit of your VC")
async def limitvc(interaction: discord.Interaction, channel: discord.VoiceChannel, limit: int):
    if not is_vc_owner_or_admin(interaction.user, channel):
        await interaction.response.send_message("You cannot manage this VC!", ephemeral=True)
        return
    await channel.edit(user_limit=limit)
    await interaction.response.send_message(f"VC user limit set to {limit}.", ephemeral=True)

# Ping command
@bot.tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

bot.run(TOKEN)
