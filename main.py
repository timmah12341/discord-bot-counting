import os
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import asyncpg
import json
from datetime import datetime, timedelta
import random

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Global database pool
db = None

# Load trivia questions
with open("trivia.json") as f:
    TRIVIA_QUESTIONS = json.load(f)

@bot.event
async def on_ready():
    global db
    db = await asyncpg.create_pool(DATABASE_URL)
    await setup_db()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Sync error: {e}")
    print(f"Bot ready as {bot.user}")

async def setup_db():
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT,
            guild_id BIGINT,
            balance INTEGER DEFAULT 0,
            last_daily TIMESTAMP,
            PRIMARY KEY (user_id, guild_id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS counting_channels (
            guild_id BIGINT,
            channel_id BIGINT,
            PRIMARY KEY (guild_id, channel_id)
        )
    """)

# --- COMMANDS ---

@bot.tree.command()
async def balance(interaction: Interaction):
    """Show your coin balance."""
    user = interaction.user
    await ensure_user(user.id, interaction.guild_id)
    row = await db.fetchrow("SELECT balance FROM users WHERE user_id = $1 AND guild_id = $2", user.id, interaction.guild_id)
    embed = discord.Embed(title="💰 Your Balance", description=f"You have **{row['balance']}** coins!", color=0xFFD700)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command()
async def daily(interaction: Interaction):
    """Claim your daily reward."""
    user = interaction.user
    await ensure_user(user.id, interaction.guild_id)
    row = await db.fetchrow("SELECT last_daily FROM users WHERE user_id = $1 AND guild_id = $2", user.id, interaction.guild_id)
    now = datetime.utcnow()

    if row["last_daily"] and now - row["last_daily"] < timedelta(hours=24):
        remaining = timedelta(hours=24) - (now - row["last_daily"])
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes = remainder // 60
        await interaction.response.send_message(f"🕒 Come back in {hours}h {minutes}m to claim again!", ephemeral=True)
        return

    await db.execute("UPDATE users SET balance = balance + 100, last_daily = $1 WHERE user_id = $2 AND guild_id = $3", now, user.id, interaction.guild_id)
    await interaction.response.send_message("✅ You claimed your **100** daily coins!", ephemeral=True)

@bot.tree.command()
async def shop(interaction: Interaction):
    """Browse and buy items."""
    options = [
        discord.SelectOption(label="🍪 cookie - 10 coins", value="cookie", description="Gives you a tasty message!"),
        discord.SelectOption(label="❓ a mystery ❓ - 0 coins", value="mystery", description="Gives you a custom role!")
    ]
    select = discord.ui.Select(placeholder="Choose an item...", options=options)

    async def select_callback(interact: Interaction):
        item = select.values[0]
        if item == "cookie":
            await db.execute("UPDATE users SET balance = balance - 10 WHERE user_id = $1 AND guild_id = $2", interact.user.id, interact.guild_id)
            await interact.response.send_message("🍪 nom nom... delicious!", ephemeral=True)
        elif item == "mystery":
            modal = discord.ui.Modal(title="Enter Role Name")
            role_input = discord.ui.TextInput(label="Role Name", placeholder="Enter the role name to receive", required=True)
            modal.add_item(role_input)

            async def modal_callback(modal_interaction: Interaction):
                role_name = role_input.value
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role:
                    await interaction.user.add_roles(role)
                    await modal_interaction.response.send_message(f"✅ You got the **{role.name}** role!", ephemeral=True)
                else:
                    await modal_interaction.response.send_message("❌ Role not found!", ephemeral=True)

            modal.callback = modal_callback
            await interact.response.send_modal(modal)

    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)
    embed = discord.Embed(title="🛒 Shop", description="Select an item to buy!", color=0x00FFAA)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command()
async def profile(interaction: Interaction):
    """View your profile."""
    user = interaction.user
    await ensure_user(user.id, interaction.guild_id)
    row = await db.fetchrow("SELECT balance FROM users WHERE user_id = $1 AND guild_id = $2", user.id, interaction.guild_id)
    embed = discord.Embed(title="📋 Your Profile", color=0x87CEEB)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Balance", value=f"💰 {row['balance']} coins")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command()
async def addchannel(interaction: Interaction):
    """Add this channel to counting."""
    await db.execute("INSERT INTO counting_channels (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", interaction.guild_id, interaction.channel_id)
    await interaction.response.send_message("✅ Counting enabled in this channel!", ephemeral=True)

@bot.tree.command()
async def removechannel(interaction: Interaction):
    """Remove this channel from counting."""
    await db.execute("DELETE FROM counting_channels WHERE guild_id = $1 AND channel_id = $2", interaction.guild_id, interaction.channel_id)
    await interaction.response.send_message("✅ Counting disabled in this channel.", ephemeral=True)

@bot.tree.command()
async def trivia(interaction: Interaction):
    """Start a trivia question!"""
    question = random.choice(TRIVIA_QUESTIONS)
    correct_key = question["correct"]
    choices = question["choices"]

    class TriviaView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            for key, text in choices.items():
                self.add_item(discord.ui.Button(label=f"{key}: {text}", custom_id=key, style=discord.ButtonStyle.primary))

        async def on_timeout(self):
            await interaction.followup.send("⏰ Time's up! The correct answer was: " + correct_key, ephemeral=True)

        async def interaction_check(self, i: Interaction) -> bool:
            return True

        async def on_error(self, interaction, error, item):
            await interaction.followup.send(f"❌ Something went wrong: {error}", ephemeral=True)

    embed = discord.Embed(title="🧠 Trivia", description=question["question"], color=0x9370DB)
    await interaction.response.send_message(embed=embed, view=TriviaView(), ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    channels = await db.fetch("SELECT channel_id FROM counting_channels WHERE guild_id = $1", message.guild.id)
    if any(str(message.channel.id) == str(row['channel_id']) for row in channels):
        # Handle only even numbers in counting channels
        if message.content.isdigit():
            count = int(message.content)
            if count % 2 == 0:  # If the number is even
                await message.channel.send(str(count + 2))  # Send the next even number
            else:
                await message.channel.send(str(count + 1))  # If odd, correct to next even number
        else:
            pass  # Ignore non-numeric messages

    await bot.process_commands(message)

# --- Utility ---
async def ensure_user(user_id, guild_id):
    await db.execute("INSERT INTO users (user_id, guild_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user_id, guild_id)

# Run the bot
bot.run(TOKEN)