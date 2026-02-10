import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("1449258112966983834"))  # replace with your server ID

intents = discord.Intents.default()
intents.members = True  # needed to see members

bot = commands.Bot(command_prefix="/", intents=intents)

# Keep track of dynamic VC owners
vc_owners = {}  # {channel_id: owner_id}

# ---------------------- EVENTS ----------------------
@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    # If user joins a "Create VC" channel
    create_channel_name = "🎮 Create VC"
    if after.channel and after.channel.name == create_channel_name:
        # Create a new temporary VC
        guild = after.channel.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True, speak=True),
        }
        new_channel = await guild.create_voice_channel(
            f"{member.name}'s VC", overwrites=overwrites, category=after.channel.category
        )
        vc_owners[new_channel.id] = member.id
        await member.move_to(new_channel)

    # Delete empty temporary channels
    if before.channel:
        if before.channel.id in vc_owners and len(before.channel.members) == 0:
            vc_owners.pop(before.channel.id)
            await before.channel.delete()

# ---------------------- SLASH COMMANDS ----------------------
@bot.tree.command(name="rename", description="Rename your VC")
async def rename(interaction: discord.Interaction, new_name: str):
    channel = interaction.user.voice.channel
    if channel and (vc_owners.get(channel.id) == interaction.user.id or interaction.user.guild_permissions.administrator):
        await channel.edit(name=new_name)
        await interaction.response.send_message(f"Channel renamed to: {new_name}", ephemeral=True)
    else:
        await interaction.response.send_message("You can't rename this VC!", ephemeral=True)

@bot.tree.command(name="limit", description="Set user limit for your VC")
async def limit(interaction: discord.Interaction, limit: int):
    channel = interaction.user.voice.channel
    if channel and (vc_owners.get(channel.id) == interaction.user.id or interaction.user.guild_permissions.administrator):
        await channel.edit(user_limit=limit)
        await interaction.response.send_message(f"User limit set to: {limit}", ephemeral=True)
    else:
        await interaction.response.send_message("You can't set limit for this VC!", ephemeral=True)

@bot.tree.command(name="lock", description="Lock your VC")
async def lock(interaction: discord.Interaction):
    channel = interaction.user.voice.channel
    if channel and (vc_owners.get(channel.id) == interaction.user.id or interaction.user.guild_permissions.administrator):
        await channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("Channel locked!", ephemeral=True)
    else:
        await interaction.response.send_message("You can't lock this VC!", ephemeral=True)

@bot.tree.command(name="unlock", description="Unlock your VC")
async def unlock(interaction: discord.Interaction):
    channel = interaction.user.voice.channel
    if channel and (vc_owners.get(channel.id) == interaction.user.id or interaction.user.guild_permissions.administrator):
        await channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("Channel unlocked!", ephemeral=True)
    else:
        await interaction.response.send_message("You can't unlock this VC!", ephemeral=True)

# ---------------------- SYNC COMMANDS ----------------------
@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Bot is online as {bot.user} and slash commands are synced!")

# ---------------------- RUN BOT ----------------------
bot.run(TOKEN)
