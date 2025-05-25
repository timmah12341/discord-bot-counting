import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

# === DATABASE SETUP ===
def setup_db():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guild_channels (
        guild_id BIGINT,
        channel_id BIGINT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_data (
        user_id BIGINT,
        guild_id BIGINT,
        balance INTEGER DEFAULT 0,
        last_daily TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS counting (
        guild_id BIGINT,
        channel_id BIGINT,
        current_number INTEGER DEFAULT 0
    );
    """)
    conn.commit()

@bot.event
async def on_ready():
    setup_db()
    await tree.sync()
    print(f"Logged in as {bot.user}")

# === COUNTING ===

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    cur.execute("SELECT * FROM guild_channels WHERE guild_id = %s AND channel_id = %s",
                (message.guild.id, message.channel.id))
    if not cur.fetchone():
        return

    cur.execute("SELECT * FROM counting WHERE guild_id = %s AND channel_id = %s",
                (message.guild.id, message.channel.id))
    data = cur.fetchone()
    if not data:
        cur.execute("INSERT INTO counting (guild_id, channel_id, current_number) VALUES (%s, %s, 0)",
                    (message.guild.id, message.channel.id))
        conn.commit()
        expected = 0
    else:
        expected = data["current_number"]

    try:
        num = int(message.content)
    except ValueError:
        return

    if num != expected:
        cur.execute("UPDATE counting SET current_number = 0 WHERE guild_id = %s AND channel_id = %s",
                    (message.guild.id, message.channel.id))
        conn.commit()
        return

    next_number = expected + 2
    await message.channel.send(str(next_number))
    cur.execute("UPDATE counting SET current_number = %s WHERE guild_id = %s AND channel_id = %s",
                (next_number, message.guild.id, message.channel.id))
    conn.commit()

# === SHOP ===

SHOP_ITEMS = {
    "🍪 Cookie": {"price": 10, "desc": "nom nom!"},
    "❓ Mystery": {"price": 0, "desc": "A mysterious item..."}
}

@tree.command(name="shop", description="View the shop")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 Shop", color=discord.Color.gold())
    for name, item in SHOP_ITEMS.items():
        embed.add_field(name=f"{name} - {item['price']} 🪙", value=item['desc'], inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="buy", description="Buy an item from the shop")
@app_commands.describe(item="The item name to buy")
async def buy(interaction: discord.Interaction, item: str):
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    item = item.strip()

    if item not in SHOP_ITEMS:
        await interaction.response.send_message("Item not found.")
        return

    cur.execute("SELECT * FROM user_data WHERE user_id = %s AND guild_id = %s", (user_id, guild_id))
    user = cur.fetchone()
    if not user:
        cur.execute("INSERT INTO user_data (user_id, guild_id, balance) VALUES (%s, %s, 0)", (user_id, guild_id))
        conn.commit()
        user = {"balance": 0}

    if user["balance"] < SHOP_ITEMS[item]["price"]:
        await interaction.response.send_message("Not enough coins!")
        return

    new_balance = user["balance"] - SHOP_ITEMS[item]["price"]
    cur.execute("UPDATE user_data SET balance = %s WHERE user_id = %s AND guild_id = %s",
                (new_balance, user_id, guild_id))
    conn.commit()
    await interaction.response.send_message(f"You bought **{item}**!")

# === PROFILE ===

@tree.command(name="profile", description="View your profile")
async def profile(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id

    cur.execute("SELECT * FROM user_data WHERE user_id = %s AND guild_id = %s", (user_id, guild_id))
    user = cur.fetchone()
    balance = user["balance"] if user else 0

    embed = discord.Embed(title=f"{interaction.user.name}'s Profile", color=discord.Color.blue())
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="Balance", value=f"{balance} 🪙", inline=False)
    await interaction.response.send_message(embed=embed)

# === BALANCE ===

@tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id

    cur.execute("SELECT * FROM user_data WHERE user_id = %s AND guild_id = %s", (user_id, guild_id))
    user = cur.fetchone()
    balance = user["balance"] if user else 0
    await interaction.response.send_message(f"Your balance: **{balance} 🪙**")

# === DAILY ===

@tree.command(name="daily", description="Claim daily coins")
async def daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id

    cur.execute("SELECT * FROM user_data WHERE user_id = %s AND guild_id = %s", (user_id, guild_id))
    user = cur.fetchone()
    now = datetime.utcnow()

    if user and user["last_daily"]:
        next_claim = user["last_daily"] + timedelta(hours=24)
        if now < next_claim:
            delta = next_claim - now
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes = remainder // 60
            await interaction.response.send_message(f"Come back in {hours}h {minutes}m for your next reward.")
            return

    if not user:
        cur.execute("INSERT INTO user_data (user_id, guild_id, balance, last_daily) VALUES (%s, %s, %s, %s)",
                    (user_id, guild_id, 100, now))
    else:
        cur.execute("UPDATE user_data SET balance = balance + 100, last_daily = %s WHERE user_id = %s AND guild_id = %s",
                    (now, user_id, guild_id))
    conn.commit()
    await interaction.response.send_message("You claimed **100 🪙**!")

# === LEADERBOARD ===

@tree.command(name="leaderboard", description="View top balances")
async def leaderboard(interaction: discord.Interaction):
    cur.execute("SELECT user_id, balance FROM user_data WHERE guild_id = %s ORDER BY balance DESC LIMIT 10",
                (interaction.guild.id,))
    top = cur.fetchall()
    embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.green())
    for i, entry in enumerate(top, 1):
        user = await bot.fetch_user(entry["user_id"])
        embed.add_field(name=f"{i}. {user.name}", value=f"{entry['balance']} 🪙", inline=False)
    await interaction.response.send_message(embed=embed)

# === CHANNEL SETUP ===

@tree.command(name="addchannel", description="Add a counting channel")
async def addchannel(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id

    cur.execute("SELECT * FROM guild_channels WHERE guild_id = %s AND channel_id = %s", (guild_id, channel_id))
    if cur.fetchone():
        await interaction.response.send_message("This channel is already set for counting.")
        return

    cur.execute("INSERT INTO guild_channels (guild_id, channel_id) VALUES (%s, %s)", (guild_id, channel_id))
    conn.commit()
    await interaction.response.send_message("Channel added for counting!")

bot.run(TOKEN)
