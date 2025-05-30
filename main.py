import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import asyncio
import psycopg2
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
TOKEN = os.getenv("DISCORD_TOKEN")

DB_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DB_URL, sslmode="require")
cur = conn.cursor()

# --- Setup: Ensure tables exist
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT,
    guild_id BIGINT,
    balance INTEGER DEFAULT 0,
    inventory TEXT DEFAULT '[]',
    last_daily TIMESTAMP,
    PRIMARY KEY (user_id, guild_id)
)""")

cur.execute("""
CREATE TABLE IF NOT EXISTS shop (
    item TEXT PRIMARY KEY,
    price INTEGER,
    description TEXT
)""")

cur.execute("""
CREATE TABLE IF NOT EXISTS counting (
    guild_id BIGINT,
    channel_id BIGINT,
    last_number INTEGER DEFAULT 0,
    last_user BIGINT,
    PRIMARY KEY (guild_id, channel_id)
)""")

conn.commit()

# --- Counting
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild_id = message.guild.id
    channel_id = message.channel.id
    user_id = message.author.id

    try:
        cur.execute("SELECT last_number, last_user FROM counting WHERE guild_id=%s AND channel_id=%s",
                    (guild_id, channel_id))
        row = cur.fetchone()

        if not row:
            cur.execute("INSERT INTO counting (guild_id, channel_id, last_number, last_user) VALUES (%s, %s, %s, %s)",
                        (guild_id, channel_id, 0, 0))
            conn.commit()
            return  # wait for user to count 1

        last_number, last_user = row
        try:
            number = int(message.content)
        except ValueError:
            return

        expected = last_number + 1
        if user_id == last_user:
            return

        if number == expected and number % 2 == 1:
            cur.execute("UPDATE counting SET last_number=%s, last_user=%s WHERE guild_id=%s AND channel_id=%s",
                        (number, user_id, guild_id, channel_id))
            conn.commit()
            await message.channel.send(f"{number + 1}")
        else:
            await message.channel.send("❌ Wrong number! Restarting from 0.")
            cur.execute("UPDATE counting SET last_number=0, last_user=NULL WHERE guild_id=%s AND channel_id=%s",
                        (guild_id, channel_id))
            conn.commit()

    except Exception as e:
        print("Counting error:", e)
    await bot.process_commands(message)

# --- Shop Commands
@bot.tree.command(name="shop")
async def shop(interaction: discord.Interaction):
    cur.execute("SELECT item, price, description FROM shop")
    rows = cur.fetchall()
    embed = discord.Embed(title="🛒 Shop", color=0x00ff00)
    for item, price, desc in rows:
        embed.add_field(name=f"{item} - {price} coins", value=desc, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buy")
@app_commands.describe(item="Select an item to buy")
async def buy(interaction: discord.Interaction, item: str):
    user_id = interaction.user.id
    guild_id = interaction.guild.id

    cur.execute("SELECT price FROM shop WHERE item=%s", (item,))
    row = cur.fetchone()
    if not row:
        await interaction.response.send_message("❌ Item not found.")
        return

    price = row[0]
    cur.execute("SELECT balance, inventory FROM users WHERE user_id=%s AND guild_id=%s",
                (user_id, guild_id))
    user = cur.fetchone()
    if not user:
        cur.execute("INSERT INTO users (user_id, guild_id) VALUES (%s, %s)", (user_id, guild_id))
        conn.commit()
        balance = 0
        inventory = []
    else:
        balance, inv_json = user
        inventory = json.loads(inv_json or "[]")

    if balance < price:
        await interaction.response.send_message("❌ Not enough coins.")
        return

    inventory.append(item)
    cur.execute("UPDATE users SET balance=%s, inventory=%s WHERE user_id=%s AND guild_id=%s",
                (balance - price, json.dumps(inventory), user_id, guild_id))
    conn.commit()
    await interaction.response.send_message(f"✅ You bought **{item}**!")

@bot.tree.command(name="inventory")
async def inventory(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    cur.execute("SELECT inventory FROM users WHERE user_id=%s AND guild_id=%s", (user_id, guild_id))
    row = cur.fetchone()
    items = json.loads(row[0] if row else "[]")
    embed = discord.Embed(title="🎒 Inventory", description="\n".join(f"• {i}" for i in items) or "Empty", color=0x9999ff)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="use")
@app_commands.describe(item="Item to use from your inventory")
async def use(interaction: discord.Interaction, item: str):
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    cur.execute("SELECT inventory FROM users WHERE user_id=%s AND guild_id=%s", (user_id, guild_id))
    row = cur.fetchone()
    if not row:
        await interaction.response.send_message("You have no items.")
        return
    inventory = json.loads(row[0])
    if item not in inventory:
        await interaction.response.send_message("You don't own that item.")
        return
    inventory.remove(item)
    cur.execute("UPDATE users SET inventory=%s WHERE user_id=%s AND guild_id=%s",
                (json.dumps(inventory), user_id, guild_id))
    conn.commit()
    await interaction.response.send_message(f"🧪 You used **{item}**!")

# --- Daily Reward
@bot.tree.command(name="daily")
async def daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    now = datetime.utcnow()
    cur.execute("SELECT balance, last_daily FROM users WHERE user_id=%s AND guild_id=%s",
                (user_id, guild_id))
    row = cur.fetchone()
    if not row:
        balance, last_daily = 0, None
    else:
        balance, last_daily = row
    if last_daily and now - last_daily < timedelta(hours=24):
        await interaction.response.send_message("⏳ You already claimed your daily reward.")
        return
    reward = 100
    cur.execute("""
        INSERT INTO users (user_id, guild_id, balance, last_daily)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, guild_id) DO UPDATE
        SET balance = users.balance + %s, last_daily = %s
    """, (user_id, guild_id, reward, now, reward, now))
    conn.commit()
    await interaction.response.send_message(f"💰 You received {reward} coins!")

# --- Balance
@bot.tree.command(name="balance")
async def balance(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    cur.execute("SELECT balance FROM users WHERE user_id=%s AND guild_id=%s",
                (user_id, guild_id))
    row = cur.fetchone()
    balance = row[0] if row else 0
    await interaction.response.send_message(f"💰 Your balance is **{balance}** coins.")

# --- Ready Event
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)