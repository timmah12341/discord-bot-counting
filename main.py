import os
import discord
import asyncpg
import json
import random
import math
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Load trivia
with open("trivia.json") as f:
    trivia_data = json.load(f)

# Connect to PostgreSQL
async def get_db():
    return await asyncpg.connect(DB_URL)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        await tree.sync()
    except Exception as e:
        print("Sync error:", e)

# ========================
# COUNTING EVENT HANDLER
# ========================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    conn = await get_db()
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS guild_{message.guild.id}_counting (
            channel_id BIGINT PRIMARY KEY,
            last_number DOUBLE PRECISION,
            last_user_id BIGINT
        )
    """)
    data = await conn.fetchrow(f"SELECT * FROM guild_{message.guild.id}_counting WHERE channel_id = $1", message.channel.id)

    if data is None:
        await conn.execute(f"INSERT INTO guild_{message.guild.id}_counting (channel_id, last_number, last_user_id) VALUES ($1, 0, 0)", message.channel.id)
        await conn.close()
        return

    try:
        expression = message.content.replace("^", "**")
        number = eval(expression, {"__builtins__": None, "pi": math.pi, "e": math.e, "sqrt": math.sqrt})
    except:
        await conn.close()
        return

    if not isinstance(number, (int, float)):
        await conn.close()
        return

    expected = data["last_number"] + 1
    if number == expected and message.author.id != data["last_user_id"]:
        await conn.execute(f"""
            UPDATE guild_{message.guild.id}_counting
            SET last_number = $1, last_user_id = $2
            WHERE channel_id = $3
        """, number, message.author.id, message.channel.id)
        await conn.execute("""
            INSERT INTO users (user_id, balance)
            VALUES ($1, 1)
            ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + 1
        """, message.author.id)
        await message.channel.send(embed=discord.Embed(
            description=f"✅ {message.author.mention} counted **{number}**!",
            color=discord.Color.green()
        ))
    else:
        await message.channel.send(embed=discord.Embed(
            description=f"❌ Wrong number, {message.author.mention}! Expected **{expected}**.",
            color=discord.Color.red()
        ))

    await conn.close()

# ========================
# POSTGRES SETUP
# ========================
@bot.event
async def on_connect():
    conn = await get_db()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            last_daily TIMESTAMP
        )
    """)
    await conn.close()

# ========================
# SLASH COMMANDS
# ========================
@tree.command(name="addchannel", description="Add a counting channel")
async def addchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conn = await get_db()
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS guild_{interaction.guild.id}_counting (
            channel_id BIGINT PRIMARY KEY,
            last_number DOUBLE PRECISION,
            last_user_id BIGINT
        )
    """)
    await conn.execute(f"""
        INSERT INTO guild_{interaction.guild.id}_counting (channel_id, last_number, last_user_id)
        VALUES ($1, 0, 0)
        ON CONFLICT (channel_id) DO NOTHING
    """, channel.id)
    await conn.close()
    await interaction.response.send_message(f"✅ {channel.mention} added as a counting channel!", ephemeral=True)

@tree.command(name="removechannel", description="Remove a counting channel")
async def removechannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conn = await get_db()
    await conn.execute(f"""
        DELETE FROM guild_{interaction.guild.id}_counting WHERE channel_id = $1
    """, channel.id)
    await conn.close()
    await interaction.response.send_message(f"❌ {channel.mention} removed from counting channels.", ephemeral=True)

@tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    conn = await get_db()
    row = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", interaction.user.id)
    bal = row["balance"] if row else 0
    await interaction.response.send_message(embed=discord.Embed(
        title="💰 Balance",
        description=f"{interaction.user.mention}, you have **{bal} coins**.",
        color=discord.Color.gold()
    ), ephemeral=True)
    await conn.close()

@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    conn = await get_db()
    user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", interaction.user.id)
    now = datetime.utcnow()

    if user and user["last_daily"]:
        last_claim = user["last_daily"]
        if now - last_claim < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_claim)
            await interaction.response.send_message(f"🕒 Come back in {str(remaining).split('.')[0]}!", ephemeral=True)
            await conn.close()
            return

    await conn.execute("""
        INSERT INTO users (user_id, balance, last_daily)
        VALUES ($1, 500, $2)
        ON CONFLICT (user_id)
        DO UPDATE SET balance = users.balance + 500, last_daily = $2
    """, interaction.user.id, now)

    await interaction.response.send_message(embed=discord.Embed(
        title="🎁 Daily Reward",
        description=f"{interaction.user.mention}, you received **500 coins**!",
        color=discord.Color.blue()
    ), ephemeral=True)
    await conn.close()

@tree.command(name="leaderboard", description="Top balances")
async def leaderboard(interaction: discord.Interaction):
    conn = await get_db()
    rows = await conn.fetch("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
    embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.purple())
    for i, row in enumerate(rows, start=1):
        user = await bot.fetch_user(row["user_id"])
        embed.add_field(name=f"{i}. {user}", value=f"{row['balance']} coins", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await conn.close()

@tree.command(name="profile", description="View your profile")
async def profile(interaction: discord.Interaction):
    conn = await get_db()
    row = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", interaction.user.id)
    bal = row["balance"] if row else 0
    embed = discord.Embed(
        title="📄 Profile",
        description=f"**User:** {interaction.user.mention}\n**Balance:** {bal} coins",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await conn.close()

@tree.command(name="trivia", description="Answer a trivia question!")
async def trivia(interaction: discord.Interaction):
    question = random.choice(trivia_data)
    choices = question["choices"]
    correct_key = question["correct"]
    correct_answer = choices[correct_key]

    buttons = []
    for key, value in choices.items():
        buttons.append(discord.ui.Button(label=value, style=discord.ButtonStyle.secondary, custom_id=key))

    view = discord.ui.View()
    for button in buttons:
        view.add_item(button)

    async def button_callback(interact: discord.Interaction):
        if interact.user.id != interaction.user.id:
            await interact.response.send_message("This isn't your trivia question!", ephemeral=True)
            return
        if interact.data["custom_id"] == correct_key:
            await interact.response.edit_message(embed=discord.Embed(
                description=f"✅ Correct! **{choices[correct_key]}** is right.",
                color=discord.Color.green()
            ), view=None)
            conn = await get_db()
            await conn.execute("""
                INSERT INTO users (user_id, balance)
                VALUES ($1, 100)
                ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + 100
            """, interaction.user.id)
            await conn.close()
        else:
            await interact.response.edit_message(embed=discord.Embed(
                description=f"❌ Wrong! Correct answer was **{choices[correct_key]}**.",
                color=discord.Color.red()
            ), view=None)

    for button in view.children:
        button.callback = button_callback

    embed = discord.Embed(title="🧠 Trivia Time!", description=question["question"], color=discord.Color.orange())
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

bot.run(TOKEN)
