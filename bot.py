import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
TRIGGER_VC_ID = int(os.getenv("TRIGGER_VC_ID"))
DYNAMIC_VC_CATEGORY_ID = int(os.getenv("DYNAMIC_VC_CATEGORY_ID"))

intents = discord.Intents.all()  # full permissions for admin checks
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Dictionary to track which user created which VC
user_vcs = {}
# Set for blacklisted users
blacklist = set()


@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    # Sync commands with the server
    guild = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild)
    print("Slash commands synced.")


# Create VC when someone joins the trigger VC
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id in blacklist:
        # Kick the user from the trigger VC immediately
        if after.channel and after.channel.id == TRIGGER_VC_ID:
            await member.move_to(None)
        return

    # User joined the trigger VC
    if after.channel and after.channel.id == TRIGGER_VC_ID:
        category = discord.utils.get(member.guild.categories, id=DYNAMIC_VC_CATEGORY_ID)
        vc = await member.guild.create_voice_channel(
            name=f"{member.name}'s VC",
            category=category,
            reason="Dynamic VC"
        )
        user_vcs[member.id] = vc.id
        await member.move_to(vc)

    # User left their VC and it was dynamically created, delete it
    if before.channel and before.channel.id in user_vcs.values():
        if before.channel.members == []:
            await before.channel.delete()
            # Remove from tracking
            to_remove = [k for k, v in user_vcs.items() if v == before.channel.id]
            for k in to_remove:
                user_vcs.pop(k)


# ----- Slash Commands -----

def can_manage_vc(interaction: discord.Interaction):
    """Check if user is the VC creator or admin"""
    user_id = interaction.user.id
    if interaction.user.guild_permissions.administrator:
        return True
    return user_vcs.get(user_id) is not None


@tree.command(name="lock", description="Lock your VC so others can't join", guild=discord.Object(id=GUILD_ID))
async def lock(interaction: discord.Interaction):
    if not can_manage_vc(interaction):
        await interaction.response.send_message("You cannot manage this VC.", ephemeral=True)
        return
    vc_id = user_vcs.get(interaction.user.id)
    vc = interaction.guild.get_channel(vc_id)
    await vc.set_permissions(interaction.guild.default_role, connect=False)
    await interaction.response.send_message("VC locked!")


@tree.command(name="unlock", description="Unlock your VC so others can join", guild=discord.Object(id=GUILD_ID))
async def unlock(interaction: discord.Interaction):
    if not can_manage_vc(interaction):
        await interaction.response.send_message("You cannot manage this VC.", ephemeral=True)
        return
    vc_id = user_vcs.get(interaction.user.id)
    vc = interaction.guild.get_channel(vc_id)
    await vc.set_permissions(interaction.guild.default_role, connect=True)
    await interaction.response.send_message("VC unlocked!")


@tree.command(name="blacklist", description="Blacklist a user from joining VC", guild=discord.Object(id=GUILD_ID))
async def blacklist_user(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only admins can blacklist users.", ephemeral=True)
        return
    blacklist.add(member.id)
    # Kick user from trigger VC if already there
    if member.voice and member.voice.channel and member.voice.channel.id == TRIGGER_VC_ID:
        await member.move_to(None)
    await interaction.response.send_message(f"{member.name} has been blacklisted from joining VC.")


@tree.command(name="unblacklist", description="Remove a user from the blacklist", guild=discord.Object(id=GUILD_ID))
async def unblacklist_user(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only admins can unblacklist users.", ephemeral=True)
        return
    blacklist.discard(member.id)
    await interaction.response.send_message(f"{member.name} has been removed from the blacklist.")


bot.run(TOKEN)
