import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
TRIGGER_VC_ID = int(os.getenv("TRIGGER_VC_ID"))
DYNAMIC_VC_CATEGORY_ID = int(os.getenv("DYNAMIC_VC_CATEGORY_ID"))

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Keep track of dynamic VCs and blacklisted users
dynamic_vcs = {}  # {vc_id: creator_id}
blacklist = set()  # user IDs

GUILD = None

@bot.event
async def on_ready():
    global GUILD
    GUILD = bot.get_guild(GUILD_ID)
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"{bot.user} is online!")

# Handle dynamic VC creation
@bot.event
async def on_voice_state_update(member, before, after):
    # User joined the trigger VC
    if after.channel and after.channel.id == TRIGGER_VC_ID:
        if member.id in blacklist:
            # Kick user from trigger VC if blacklisted
            await member.move_to(None)
            return

        category = discord.utils.get(GUILD.categories, id=DYNAMIC_VC_CATEGORY_ID)
        if not category:
            return
        # Create new VC
        new_vc = await GUILD.create_voice_channel(
            name=f"{member.display_name}'s VC",
            category=category,
            reason="Dynamic VC created"
        )
        dynamic_vcs[new_vc.id] = member.id
        await member.move_to(new_vc)

    # Clean up empty dynamic VCs
    if before.channel and before.channel.id in dynamic_vcs:
        if len(before.channel.members) == 0:
            del dynamic_vcs[before.channel.id]
            await before.channel.delete(reason="Dynamic VC empty")

# Slash command: blacklist
@bot.tree.command(name="vc_blacklist", description="Blacklist a user from dynamic VCs")
@app_commands.describe(user="User to blacklist")
async def vc_blacklist(interaction: discord.Interaction, user: discord.Member):
    # Only VC creator or admin
    if interaction.user.guild_permissions.administrator or interaction.user.id in dynamic_vcs.values():
        blacklist.add(user.id)
        await interaction.response.send_message(f"{user.mention} has been blacklisted.", ephemeral=True)
    else:
        await interaction.response.send_message("You can't run this command.", ephemeral=True)

# Slash command: unblacklist
@bot.tree.command(name="vc_unblacklist", description="Remove a user from the blacklist")
@app_commands.describe(user="User to unblacklist")
async def vc_unblacklist(interaction: discord.Interaction, user: discord.Member):
    if interaction.user.guild_permissions.administrator or interaction.user.id in dynamic_vcs.values():
        blacklist.discard(user.id)
        await interaction.response.send_message(f"{user.mention} has been unblacklisted.", ephemeral=True)
    else:
        await interaction.response.send_message("You can't run this command.", ephemeral=True)

# Slash command: list blacklist
@bot.tree.command(name="vc_blacklist_list", description="Show all blacklisted users")
async def vc_blacklist_list(interaction: discord.Interaction):
    if not blacklist:
        await interaction.response.send_message("Blacklist is empty.", ephemeral=True)
        return
    members = [GUILD.get_member(user_id).mention for user_id in blacklist if GUILD.get_member(user_id)]
    await interaction.response.send_message("Blacklisted users: " + ", ".join(members), ephemeral=True)

bot.run(TOKEN)
