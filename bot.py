import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TRIGGER_VC_ID = int(os.getenv("TRIGGER_VC_ID"))
DYNAMIC_VC_CATEGORY_ID = int(os.getenv("DYNAMIC_VC_CATEGORY_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# channel_id -> owner_id
created_vcs = {}


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    guild = discord.Object(id=GUILD_ID)
    await bot.sync_commands(guild_ids=[GUILD_ID])
    print("✅ Slash commands synced")


def can_control_vc(interaction: discord.Interaction):
    if not interaction.user.voice:
        return False, "You must be in a voice channel."

    vc = interaction.user.voice.channel

    if interaction.user.guild_permissions.administrator:
        return True, vc

    if vc.id in created_vcs and created_vcs[vc.id] == interaction.user.id:
        return True, vc

    return False, "You do not own this voice channel."


@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == TRIGGER_VC_ID:
        guild = member.guild
        category = guild.get_channel(DYNAMIC_VC_CATEGORY_ID)

        vc = await guild.create_voice_channel(
            name=f"{member.name}'s VC",
            category=category
        )

        created_vcs[vc.id] = member.id
        await member.move_to(vc)

    if before.channel and before.channel.id in created_vcs:
        if len(before.channel.members) == 0:
            del created_vcs[before.channel.id]
            await before.channel.delete()


@bot.slash_command(
    name="blacklist",
    description="Block a user from joining your voice channel",
    guild_ids=[GUILD_ID]
)
async def blacklist(interaction: discord.Interaction, user: discord.Member):
    allowed, result = can_control_vc(interaction)

    if not allowed:
        await interaction.respond(result, ephemeral=True)
        return

    vc = result

    await vc.set_permissions(user, connect=False)

    await interaction.respond(
        f"🚫 **{user.display_name}** is now blacklisted from this VC.",
        ephemeral=True
    )


bot.run(TOKEN)
