import os
import json
import discord
import random
import asyncio
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DB_FILE = "db.json"
WAKE_UP_CHANNELS = [1368349957718802572, 1366574260554043503]

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"users": {}, "count_channel": None}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

db = load_db()

# ------------- ON READY -------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    for channel_id in WAKE_UP_CHANNELS:
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                await channel.send("🌞 Wake up! I'm online and ready!")
            except Exception as e:
                print(f"Failed to send message to {channel_id}: {e}")
    await tree.sync()

# ------------- COUNTING SYSTEM -------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    db = load_db()
    count_channel = db.get("count_channel")
    if str(message.channel.id) != str(count_channel):
        return

    user_id = str(message.author.id)
    user_data = db["users"].setdefault(user_id, {"count": 0, "balance": 0, "last_daily": None})

    try:
        user_input = message.content.lower().replace("π", str(3.14159))
        num = eval(user_input, {"__builtins__": {}})
        if not isinstance(num, (int, float)):
            return
    except:
        return

    if int(num) % 2 == 1:
        response = int(num) + 1
        await message.channel.send(embed=discord.Embed(
            title="🧮 Counting",
            description=f"{response}",
            color=discord.Color.orange()
        ))
        user_data["count"] += 1
        user_data["balance"] += 1
        db["users"][user_id] = user_data
        save_db(db)

# ------------- COMMANDS -------------
@tree.command(name="setchannel", description="Set the channel for counting")
async def setchannel(interaction: discord.Interaction):
    db = load_db()
    db["count_channel"] = str(interaction.channel.id)
    save_db(db)
    await interaction.response.send_message(embed=discord.Embed(
        title="🔧 Counting Channel Set",
        description=f"Counting will now happen in <#{interaction.channel.id}>.",
        color=discord.Color.green()
    ))

@tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    db = load_db()
    user = str(interaction.user.id)
    bal = db["users"].get(user, {}).get("balance", 0)
    await interaction.response.send_message(embed=discord.Embed(
        title="💰 Your Balance",
        description=f"You have {bal} coins.",
        color=discord.Color.gold()
    ))

@tree.command(name="daily", description="Get your daily reward")
async def daily(interaction: discord.Interaction):
    db = load_db()
    user_id = str(interaction.user.id)
    user_data = db["users"].setdefault(user_id, {"count": 0, "balance": 0, "last_daily": None})

    now = datetime.utcnow()
    last_claim = user_data.get("last_daily")
    if last_claim:
        last_claim = datetime.fromisoformat(last_claim)
        if now - last_claim < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_claim)
            await interaction.response.send_message(embed=discord.Embed(
                title="🕒 Too Soon!",
                description=f"Come back in {str(remaining).split('.')[0]}",
                color=discord.Color.red()
            ))
            return

    user_data["balance"] += 100
    user_data["last_daily"] = now.isoformat()
    db["users"][user_id] = user_data
    save_db(db)

    await interaction.response.send_message(embed=discord.Embed(
        title="🎉 Daily Claimed!",
        description="You received 100 coins!",
        color=discord.Color.green()
    ))

@tree.command(name="funny", description="Shows something funny")
async def funny(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(
        title="😂 Funny!",
        image=discord.Embed.Empty
    ).set_image(url="https://cdn.discordapp.com/attachments/1126690480594546708/1236033920730701854/emoji.png"))

@tree.command(name="meme", description="Sends a cryptic meme")
async def meme(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(
        title="🔺 Meme Transmission",
        description="𓂀⚙️⏳ 01101101 01100101 01101101 01100101",
        color=discord.Color.purple()
    ))

# You can re-add the trivia, shop, profile, leaderboard here if needed.

bot.run(TOKEN)
