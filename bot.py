import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ["DISCORD_TOKEN"]

# --- CONFIGURATION ---
TRIGGER_VC_ID = 1470292572248342558  # The VC that triggers dynamic VC creation
DYNAMIC_CATEGORY_ID = 1470292466715328726  # Category where dynamic VCs will be created
ADMIN_ROLE_ID = 1470291414733819946  # Role ID of admins

# Intents
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- STORAGE ---
dynamic_vcs = {}  # {user_id: channel_id}
blacklist = set()
vc_limit = 5  # Default member limit

# --- EVENTS ---
@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    # User joins trigger VC
    if after.channel and after.channel.id == TRIGGER_VC_ID:
        if member.id in blacklist:
            await member.move_to(None)  # Kick them out
            return

        # Create new VC for user
        category = discord.utils.get(member.guild.categories, id=DYNAMIC_CATEGORY_ID)
        new_vc = await member.guild.create_voice_channel(
            name=f"{member.name}'s VC",
            category=category,
            user_limit=vc_limit
        )
        dynamic_vcs[member.id] = new_vc.id
        await member.move_to(new_vc)

    # User leaves dynamic VC
    if before.channel and before.channel.id in dynamic_vcs.values():
        channel = before.channel
        if len(channel.members) == 0:
            await channel.delete()
            # Remove from tracking
            for user_id, vc_id in list(dynamic_vcs.items()):
                if vc_id == channel.id:
                    del dynamic_vcs[user_id]

# --- COMMANDS (ADMIN ONLY) ---
def is_admin():
    async def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, id=ADMIN_ROLE_ID)
        return role is not None
    return commands.check(predicate)

@bot.command()
@is_admin()
async def set_limit(ctx, limit: int):
    global vc_limit
    vc_limit = limit
    await ctx.send(f"VC member limit set to {limit}")

@bot.command()
@is_admin()
async def blacklist_user(ctx, user: discord.Member):
    blacklist.add(user.id)
    await ctx.send(f"{user.name} has been blacklisted from creating VCs.")

@bot.command()
@is_admin()
async def unblacklist_user(ctx, user: discord.Member):
    blacklist.discard(user.id)
    await ctx.send(f"{user.name} has been removed from the blacklist.")

# Run the bot
bot.run(TOKEN)
