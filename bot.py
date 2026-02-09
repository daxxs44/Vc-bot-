import discord
from discord.ext import commands
from discord.ui import View, Button
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
TRIGGER_VC_ID = int(os.getenv("TRIGGER_VC_ID"))
DYNAMIC_VC_CATEGORY_ID = int(os.getenv("DYNAMIC_VC_CATEGORY_ID"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))

# Store VC data
vc_data = {}

# ---------------- Dynamic VC Creation ----------------
@bot.event
async def on_voice_state_update(member, before, after):
    # User joins the "trigger" VC
    if after.channel and after.channel.id == TRIGGER_VC_ID:
        category = member.guild.get_channel(DYNAMIC_VC_CATEGORY_ID)
        new_vc = await member.guild.create_voice_channel(
            name=f"{member.name}'s VC",
            category=category,
            user_limit=5  # default
        )
        vc_data[new_vc.id] = {
            "owner": member.id,
            "limit": 5,
            "blacklist": set()
        }
        await member.move_to(new_vc)

        # Send admin panel
        text_channel = member.guild.text_channels[0]  # Change as needed
        await text_channel.send(
            f"Admin panel for {new_vc.name}",
            view=AdminView(new_vc.id)
        )

    # Delete empty dynamic VCs
    if before.channel and before.channel.id in vc_data:
        if len(before.channel.members) == 0:
            await before.channel.delete()
            vc_data.pop(before.channel.id, None)

# ---------------- Admin Buttons ----------------
class AdminView(View):
    def __init__(self, vc_id):
        super().__init__(timeout=None)
        self.vc_id = vc_id

    @discord.ui.button(label="Increase Limit", style=discord.ButtonStyle.green)
    async def increase(self, button: Button, interaction: discord.Interaction):
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message("Not allowed", ephemeral=True)
        vc_info = vc_data.get(self.vc_id)
        if vc_info:
            vc_info["limit"] += 1
            vc = interaction.guild.get_channel(self.vc_id)
            await vc.edit(user_limit=vc_info["limit"])
            await interaction.response.send_message(f"Limit: {vc_info['limit']}", ephemeral=True)

    @discord.ui.button(label="Decrease Limit", style=discord.ButtonStyle.red)
    async def decrease(self, button: Button, interaction: discord.Interaction):
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message("Not allowed", ephemeral=True)
        vc_info = vc_data.get(self.vc_id)
        if vc_info:
            vc_info["limit"] = max(vc_info["limit"] - 1, 0)
            vc = interaction.guild.get_channel(self.vc_id)
            await vc.edit(user_limit=vc_info["limit"])
            await interaction.response.send_message(f"Limit: {vc_info['limit']}", ephemeral=True)

# ---------------- Run Bot ----------------
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not set in .env")

bot.run(TOKEN)
