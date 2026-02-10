import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True  # needed for privileged member intents

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
TRIGGER_VC_ID = int(os.getenv("TRIGGER_VC_ID"))
DYNAMIC_VC_CATEGORY_ID = int(os.getenv("DYNAMIC_VC_CATEGORY_ID"))

bot = commands.Bot(command_prefix="/", intents=intents)


# Helper to check if user is VC owner or admin
def can_manage_vc(ctx, vc):
    return ctx.author.guild_permissions.administrator or vc.owner_id == ctx.author.id


@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")


# Example: delete VC
@bot.command()
async def deletevc(ctx):
    if ctx.author.voice and ctx.author.voice.channel:
        vc = ctx.author.voice.channel
        if can_manage_vc(ctx, vc):
            await vc.delete()
            await ctx.send(f"{vc.name} deleted successfully!")
        else:
            await ctx.send("You are not allowed to delete this VC.")
    else:
        await ctx.send("You are not in a VC.")


# Example: rename VC
@bot.command()
async def renamevc(ctx, *, new_name):
    if ctx.author.voice and ctx.author.voice.channel:
        vc = ctx.author.voice.channel
        if can_manage_vc(ctx, vc):
            await vc.edit(name=new_name)
            await ctx.send(f"VC renamed to {new_name}")
        else:
            await ctx.send("You are not allowed to rename this VC.")
    else:
        await ctx.send("You are not in a VC.")


bot.run(TOKEN)
