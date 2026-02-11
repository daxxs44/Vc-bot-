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
INTERFACE_CHANNEL_ID = 1470952162539606067

# ----- Bot Setup -----
intents = discord.Intents.all()  # full permissions for admin checks and voice state updates
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ----- Tracking -----
user_vcs = {}    # user_id -> dynamic VC id
vc_blacklists = {}  # vc_id -> set of blacklisted user IDs
vc_owners = {}  # vc_id -> owner user_id (for tracking ownership)
dynamic_vcs = set()  # set of all dynamic VC IDs for easy checking
vc_limits = {}  # vc_id -> user limit (for custom enforcement)

# ----- Events -----
@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    guild = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild)
    print("Slash commands synced.")
    
    # Send interface message with all commands
    try:
        interface_channel = bot.get_channel(INTERFACE_CHANNEL_ID)
        if interface_channel:
            # Create embed
            embed = discord.Embed(
                title="🎙️ Voice Channel Commands",
                description="Here are all available commands for managing your voice channel:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📋 Available Commands",
                value=(
                    "`/lock` - Lock your VC so others cannot join\n"
                    "`/unlock` - Unlock your VC so others can join\n"
                    "`/limit <number>` - Set the user limit for your VC (0-99)\n"
                    "`/blacklist <user>` - Ban a user from joining your VC\n"
                    "`/unblacklist <user>` - Unban a user from your VC\n"
                    "`/claim` - Claim ownership of the VC when the owner leaves"
                ),
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ How It Works",
                value=(
                    "• Join the trigger voice channel to create your own VC\n"
                    "• You automatically become the owner of your VC\n"
                    "• Admins can manage any VC they're in\n"
                    "• Your VC is deleted when everyone leaves"
                ),
                inline=False
            )
            
            embed.set_footer(text="Use these commands to control your voice channel!")
            
            await interface_channel.send(embed=embed)
            print("Interface message sent!")
    except Exception as e:
        print(f"Error sending interface: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    # User joined trigger VC → create dynamic VC
    if after.channel and after.channel.id == TRIGGER_VC_ID:
        category = discord.utils.get(member.guild.categories, id=DYNAMIC_VC_CATEGORY_ID)
        vc = await member.guild.create_voice_channel(
            name=f"{member.name}'s VC",
            category=category,
            reason="Dynamic VC"
        )
        user_vcs[member.id] = vc.id
        vc_owners[vc.id] = member.id  # Track the owner
        vc_blacklists[vc.id] = set()  # Initialize empty blacklist for this VC
        dynamic_vcs.add(vc.id)  # Mark as dynamic VC
        vc_limits[vc.id] = 0  # 0 = no limit by default
        await member.move_to(vc)

    # Enforce user limit (kick users over the limit, excluding admins)
    if after.channel and after.channel.id in vc_limits:
        limit = vc_limits[after.channel.id]
        if limit > 0 and not member.guild_permissions.administrator:
            current_members = len(after.channel.members)
            if current_members > limit:
                try:
                    await member.move_to(None)
                except:
                    pass

    # Kick blacklisted users from specific VCs they're banned from
    if after.channel and after.channel.id in vc_blacklists:
        if member.id in vc_blacklists[after.channel.id]:
            try:
                await member.move_to(None)
            except:
                pass

    # User left a dynamic VC → delete if empty
    if before.channel and before.channel.id in dynamic_vcs:
        if len(before.channel.members) == 0:
            try:
                await before.channel.delete()
            except:
                pass
            # Clean up all tracking for this VC
            to_remove = [k for k, v in user_vcs.items() if v == before.channel.id]
            for k in to_remove:
                user_vcs.pop(k)
            # Remove owner tracking
            if before.channel.id in vc_owners:
                vc_owners.pop(before.channel.id)
            # Remove blacklist for this VC
            if before.channel.id in vc_blacklists:
                vc_blacklists.pop(before.channel.id)
            # Remove from dynamic VCs set
            dynamic_vcs.discard(before.channel.id)
            # Remove limit tracking
            if before.channel.id in vc_limits:
                vc_limits.pop(before.channel.id)

# ----- Helper Function -----
def can_manage_vc(interaction: discord.Interaction):
    """User can manage VC if they are admin or own it"""
    if interaction.user.guild_permissions.administrator:
        return True
    # Check if user is in a dynamic VC and owns it
    if interaction.user.voice and interaction.user.voice.channel:
        vc_id = interaction.user.voice.channel.id
        if vc_id in vc_owners and vc_owners[vc_id] == interaction.user.id:
            return True
    # Check if user owns a VC (even if not currently in it)
    return user_vcs.get(interaction.user.id) is not None

def get_user_vc(interaction: discord.Interaction):
    """Get the VC channel the user should manage"""
    # If admin, get the VC they're currently in (if it's a dynamic one)
    if interaction.user.guild_permissions.administrator:
        if interaction.user.voice and interaction.user.voice.channel:
            if interaction.user.voice.channel.id in dynamic_vcs:
                return interaction.user.voice.channel
    # Check if they're in a VC they own
    if interaction.user.voice and interaction.user.voice.channel:
        vc_id = interaction.user.voice.channel.id
        if vc_id in vc_owners and vc_owners[vc_id] == interaction.user.id:
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
    
    # Set both Discord's native limit and our custom tracking
    await vc.edit(user_limit=number)
    vc_limits[vc.id] = number
    
    # Kick users over the limit (excluding admins)
    if number > 0:
        current_members = [m for m in vc.members if not m.guild_permissions.administrator]
        if len(current_members) > number:
            # Kick the extra members (keep the first 'number' of members)
            to_kick = current_members[number:]
            for member in to_kick:
                try:
                    await member.move_to(None)
                except:
                    pass
    
    if number == 0:
        await interaction.response.send_message(f"👥 {vc.name} now has no user limit!")
    else:
        await interaction.response.send_message(f"👥 {vc.name} user limit set to {number}!")

@tree.command(name="blacklist", description="Ban a user from joining your VC", guild=discord.Object(id=GUILD_ID))
async def blacklist_user(interaction: discord.Interaction, member: discord.Member):
    if not can_manage_vc(interaction):
        await interaction.response.send_message("You cannot manage this VC.", ephemeral=True)
        return
    
    vc = get_user_vc(interaction)
    if not vc:
        await interaction.response.send_message("Could not find your VC.", ephemeral=True)
        return
    
    if vc.id not in vc_blacklists:
        vc_blacklists[vc.id] = set()
    
    if member.id in vc_blacklists[vc.id]:
        await interaction.response.send_message(f"{member.name} is already banned from your VC.", ephemeral=True)
        return
    
    vc_blacklists[vc.id].add(member.id)
    
    # Kick user if they're currently in this VC
    if member.voice and member.voice.channel and member.voice.channel.id == vc.id:
        try:
            await member.move_to(None)
        except:
            pass
    
    await interaction.response.send_message(f"🚫 {member.mention} has been banned from {vc.name}.")

@tree.command(name="unblacklist", description="Unban a user from your VC", guild=discord.Object(id=GUILD_ID))
async def unblacklist_user(interaction: discord.Interaction, member: discord.Member):
    if not can_manage_vc(interaction):
        await interaction.response.send_message("You cannot manage this VC.", ephemeral=True)
        return
    
    vc = get_user_vc(interaction)
    if not vc:
        await interaction.response.send_message("Could not find your VC.", ephemeral=True)
        return
    
    if vc.id not in vc_blacklists or member.id not in vc_blacklists[vc.id]:
        await interaction.response.send_message(f"{member.name} is not banned from your VC.", ephemeral=True)
        return
    
    vc_blacklists[vc.id].discard(member.id)
    await interaction.response.send_message(f"✅ {member.mention} has been unbanned from {vc.name}.")

@tree.command(name="claim", description="Claim ownership of the VC when the owner leaves", guild=discord.Object(id=GUILD_ID))
async def claim(interaction: discord.Interaction):
    # Check if user is in a voice channel
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You must be in a voice channel to claim it.", ephemeral=True)
        return
    
    vc = interaction.user.voice.channel
    
    # Check if this is a dynamic VC
    if vc.id not in dynamic_vcs:
        await interaction.response.send_message("This is not a dynamic VC.", ephemeral=True)
        return
    
    # Check if there's an owner tracked for this VC
    if vc.id not in vc_owners:
        await interaction.response.send_message("This VC has no owner to claim from.", ephemeral=True)
        return
    
    current_owner_id = vc_owners[vc.id]
    
    # Check if current owner is still in the VC
    owner_in_vc = any(member.id == current_owner_id for member in vc.members)
    
    if owner_in_vc:
        await interaction.response.send_message("The owner is still in the VC. You cannot claim it yet.", ephemeral=True)
        return
    
    # Transfer ownership
    old_owner_id = current_owner_id
    vc_owners[vc.id] = interaction.user.id
    
    # Update user_vcs tracking
    if old_owner_id in user_vcs and user_vcs[old_owner_id] == vc.id:
        user_vcs.pop(old_owner_id)
    user_vcs[interaction.user.id] = vc.id
    
    # Rename the VC to the new owner's name
    await vc.edit(name=f"{interaction.user.name}'s VC")
    
    await interaction.response.send_message(f"👑 You are now the owner of {vc.name}!")

# ----- Run Bot -----
bot.run(TOKEN)
