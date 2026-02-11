import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# Load environment variables (only needed for local dev)
load_dotenv()

# ----- Environment Variables -----
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
TRIGGER_VC_ID = int(os.getenv("TRIGGER_VC_ID"))
DYNAMIC_VC_CATEGORY_ID = int(os.getenv("DYNAMIC_VC_CATEGORY_ID"))

# ----- Bot Setup -----
intents = discord.Intents.all()  # full permissions for admin checks and voice state updates
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ----- Tracking -----
user_vcs = {}    # user_id -> dynamic VC id
blacklist = set()  # set of user IDs

# ----- Events -----
@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    guild = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild)
    print("Slash commands synced.")

@bot.event
async def on_voice_state_update(member, before, after):
    # Kick blacklisted users from trigger VC
    if member.id in blacklist:
        if after.channel and after.channel.id == TRIGGER_VC_ID:
            await member.move_to(None)
        return

    # User joined trigger VC → create dynamic VC
    if after.channel and after.channel.id == TRIGGER_VC_ID:
        category = discord.utils.get(member.guild.categories, id=DYNAMIC_VC_CATEGORY_ID)
        vc = await member.guild.create_voice_channel(
            name=f"{member.name}'s VC",
            category=category,
            reason="Dynamic VC"
        )
        user_vcs[member.id] = vc.id
        await member.move_to(vc)

    # User left their dynamic VC → delete if empty
    if before.channel and before.channel.id in user_vcs.values():
        if len(before.channel.members) == 0:
            await before.channel.delete()
            to_remove = [k for k, v in user_vcs.items() if v == before.channel.id]
            for k in to_remove:
                user_vcs.pop(k)

# ----- Helper Function -----
def can_manage_vc(interaction: discord.Interaction):
    """User can manage VC if they are admin or created it"""
    if interaction.user.guild_permissions.administrator:
        return True
    # Check if user is in a dynamic VC
    if interaction.user.voice and interaction.user.voice.channel:
        return interaction.user.voice.channel.id in user_vcs.values()
    return user_vcs.get(interaction.user.id) is not None

def get_user_vc(interaction: discord.Interaction):
    """Get the VC channel the user should manage"""
    # If admin, get the VC they're currently in (if it's a dynamic one)
    if interaction.user.guild_permissions.administrator:
        if interaction.user.voice and interaction.user.voice.channel:
            if interaction.user.voice.channel.id in user_vcs.values():
                return interaction.user.voice.channel
    # Otherwise get their created VC
    vc_id = user_vcs.get(interaction.user.id)
    if vc_id:
        return interaction.guild.get_channel(vc_id)
    return None

# ----- Slash Commands -----
@tree.command(name="lock", description="Lock your VC so others cannot join", guild=discord.Object(id=GUILD_ID))
async def lock(interaction: discord.Interaction):
    if not can_manage_vc(interaction):
        await interaction.response.send_message("You cannot manage this VC.", ephemeral=True)
        return
    vc = get_user_vc(interaction)
    if not vc:
        await interaction.response.send_message("Could not find your VC.", ephemeral=True)
        return
    await vc.set_permissions(interaction.guild.default_role, connect=False)
    await interaction.response.send_message(f"🔒 {vc.name} is now locked!")

@tree.command(name="unlock", description="Unlock your VC so others can join", guild=discord.Object(id=GUILD_ID))
async def unlock(interaction: discord.Interaction):
    if not can_manage_vc(interaction):
        await interaction.response.send_message("You cannot manage this VC.", ephemeral=True)
        return
    vc = get_user_vc(interaction)
    if not vc:
        await interaction.response.send_message("Could not find your VC.", ephemeral=True)
        return
    await vc.set_permissions(interaction.guild.default_role, connect=True)
    await interaction.response.send_message(f"🔓 {vc.name} is now unlocked!")

@tree.command(name="limit", description="Set the user limit for your VC", guild=discord.Object(id=GUILD_ID))
async def limit(interaction: discord.Interaction, number: int):
    if not can_manage_vc(interaction):
        await interaction.response.send_message("You cannot manage this VC.", ephemeral=True)
        return
    
    if number < 0 or number > 99:
        await interaction.response.send_message("Limit must be between 0 and 99. Use 0 for no limit.", ephemeral=True)
        return
    
    vc = get_user_vc(interaction)
    if not vc:
        await interaction.response.send_message("Could not find your VC.", ephemeral=True)
        return
    
    await vc.edit(user_limit=number)
    if number == 0:
        await interaction.response.send_message(f"👥 {vc.name} now has no user limit!")
    else:
        await interaction.response.send_message(f"👥 {vc.name} user limit set to {number}!")

@tree.command(name="blacklist", description="Blacklist a user from creating VCs", guild=discord.Object(id=GUILD_ID))
async def blacklist_user(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only admins can blacklist users.", ephemeral=True)
        return
    
    if member.id in blacklist:
        await interaction.response.send_message(f"{member.name} is already blacklisted.", ephemeral=True)
        return
    
    blacklist.add(member.id)
    
    # Kick user if in trigger VC or their own VC
    if member.voice and member.voice.channel:
        if member.voice.channel.id == TRIGGER_VC_ID or member.voice.channel.id in user_vcs.values():
            try:
                await member.move_to(None)
            except:
                pass
    
    await interaction.response.send_message(f"🚫 {member.mention} has been blacklisted from creating VCs.")

@tree.command(name="unblacklist", description="Remove a user from the blacklist", guild=discord.Object(id=GUILD_ID))
async def unblacklist_user(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only admins can unblacklist users.", ephemeral=True)
        return
    
    if member.id not in blacklist:
        await interaction.response.send_message(f"{member.name} is not blacklisted.", ephemeral=True)
        return
    
    blacklist.discard(member.id)
    await interaction.response.send_message(f"✅ {member.mention} has been removed from the blacklist.")

# ----- Run Bot -----
bot.run(TOKEN)
