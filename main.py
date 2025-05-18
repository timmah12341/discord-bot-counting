import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncpg
import os
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
TOKEN = os.getenv("DISCORD_TOKEN")

# --- DATABASE ---
async def create_db_pool():
    bot.db = await asyncpg.create_pool(dsn=os.getenv("DATABASE_URL"))
    await bot.db.execute("""
        CREATE TABLE IF NOT EXISTS counting_channels (
            guild_id BIGINT,
            channel_id BIGINT PRIMARY KEY
        );
    """)
    await bot.db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            last_daily TIMESTAMP DEFAULT now()
        );
    """)

# --- ON READY ---
@bot.event
async def on_ready():
    await create_db_pool()
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

# --- /addchannel ---
@bot.tree.command(name="addchannel", description="Add this channel to counting")
async def addchannel(interaction: discord.Interaction):
    await bot.db.execute(
        "INSERT INTO counting_channels (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT (channel_id) DO NOTHING",
        interaction.guild.id, interaction.channel.id
    )
    await interaction.response.send_message("✅ This channel is now a counting channel.", ephemeral=True)

# --- /removechannel ---
@bot.tree.command(name="removechannel", description="Remove this channel from counting")
async def removechannel(interaction: discord.Interaction):
    await bot.db.execute(
        "DELETE FROM counting_channels WHERE channel_id = $1",
        interaction.channel.id
    )
    await interaction.response.send_message("🗑️ Channel removed from counting.", ephemeral=True)

# --- /daily ---
@bot.tree.command(name="daily", description="Claim your daily coins")
async def daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    now = datetime.utcnow()
    user = await bot.db.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)

    if user is None:
        await bot.db.execute("INSERT INTO users (user_id, balance, last_daily) VALUES ($1, 100, $2)", user_id, now)
        await interaction.response.send_message("🌞 You claimed your first daily 100 coins!")
        return

    last_claim = user["last_daily"]
    if now - last_claim < timedelta(hours=24):
        next_time = last_claim + timedelta(hours=24)
        await interaction.response.send_message(f"🕒 Come back <t:{int(next_time.timestamp())}:R>.")
    else:
        await bot.db.execute(
            "UPDATE users SET balance = balance + 100, last_daily = $1 WHERE user_id = $2",
            now, user_id
        )
        await interaction.response.send_message("💰 You claimed your 100 daily coins!")

# --- /balance ---
@bot.tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    user_id = interaction.user.id
    user = await bot.db.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)
    bal = user["balance"] if user else 0
    await interaction.response.send_message(f"💸 Your balance: **{bal}** coins")

# --- COUNTING SYSTEM ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Check if channel is a counting channel
    result = await bot.db.fetchval("SELECT 1 FROM counting_channels WHERE channel_id = $1", message.channel.id)
    if not result:
        return

    # Handle counting logic (replace this with your own)
    try:
        number = int(message.content.strip())
        await message.channel.send(str(number + 1))
    except ValueError:
        await message.channel.send("❌ Please send a number.")

# --- RUN BOT ---
bot.run(TOKEN)
