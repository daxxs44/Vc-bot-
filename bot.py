import discord
from discord.ext import commands
import os

# Load token
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
TRIGGER_VC_ID = 1470292572248342558  # Replace with your trigger VC ID
VC_CATEGORY_ID = 1470292466715328726  # Replace with your category ID
MAX_USERS = 5  # Default limit
blacklist = set()  # Store user IDs here

# Track created VCs
temp_vcs = {}

# -------------------
# Voice state listener
# -------------------
@bot.event
async def on_voice_state_update(member, before, after):
    # If member joined trigger VC
    if after.channel and after.channel.id == TRIGGER_VC_ID:
        if member.id in blacklist:
            await member.move_to(None)  # Kick from VC
            return

        # Create a new VC
        category = discord.utils.get(member.guild.categories, id=VC_CATEGORY_ID)
        new_vc = await member.guild.create_voice_channel(
            name=f"{member.name}'s VC",
            category=category,
            user_limit=MAX_USERS
        )
        temp_vcs[new_vc.id] = new_vc
        await member.move_to(new_vc)

    # If member leaves a temp VC
    if before.channel and before.channel.id in temp_vcs:
        vc = temp_vcs[before.channel.id]
        if len(vc.members) == 0:
            await vc.delete()
            temp_vcs.pop(vc.id, None)

# -------------------
# Admin commands
# -------------------
def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.command()
@is_admin()
async def set_max(ctx, number: int):
    global MAX_USERS
    MAX_USERS = number
    await ctx.send(f"Max users set to {MAX_USERS}")

@bot.command()
@is_admin()
async def blacklist_add(ctx, member: discord.Member):
    blacklist.add(member.id)
    await ctx.send(f"{member.name} added to blacklist")

@bot.command()
@is_admin()
async def blacklist_remove(ctx, member: discord.Member):
    blacklist.discard(member.id)
    await ctx.send(f"{member.name} removed from blacklist")

@bot.command()
@is_admin()
async def show_blacklist(ctx):
    if not blacklist:
        await ctx.send("Blacklist is empty")
    else:
        names = []
        for uid in blacklist:
            m = ctx.guild.get_member(uid)
            if m:
                names.append(m.name)
        await ctx.send("Blacklisted users: " + ", ".join(names))

# -------------------
# Run the bot
# -------------------
bot.run(TOKEN)
