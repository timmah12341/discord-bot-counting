import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncpg
import json
import os
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATABASE_URL = os.environ["DATABASE_URL"]
pool = None
trivia_questions = []

# Load trivia.json
async def refresh_trivia():
    global trivia_questions
    with open("trivia.json", "r") as f:
        trivia_questions = json.load(f)
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS trivia_questions")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trivia_questions (
                id SERIAL PRIMARY KEY,
                question TEXT,
                choices JSONB,
                correct TEXT
            )
        """)
        for q in trivia_questions:
            await conn.execute("""
                INSERT INTO trivia_questions (question, choices, correct) VALUES ($1, $2, $3)
            """, q["question"], json.dumps(q["choices"]), q["correct"])

# Create per-server tables
async def init_guild_data(guild_id):
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS guild_{guild_id}_counting (
                channel_id BIGINT
            );
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS guild_{guild_id}_users (
                user_id BIGINT PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                last_daily TIMESTAMP
            );
        """)

# Database pool
@bot.event
async def on_ready():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    await refresh_trivia()
    for guild in bot.guilds:
        await init_guild_data(guild.id)
    await tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_guild_join(guild):
    await init_guild_data(guild.id)

# Counting message handler
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    async with pool.acquire() as conn:
        rows = await conn.fetch(f"SELECT channel_id FROM guild_{message.guild.id}_counting")
        if not rows:
            return
        channel_ids = [row["channel_id"] for row in rows]
        if message.channel.id not in channel_ids:
            return
        content = message.content.strip()
        try:
            user_number = eval(content, {"__builtins__": {}})
            if int(user_number) % 2 == 1:
                await message.channel.send(f"{int(user_number)+1}")
        except:
            pass

# /addchannel command
@tree.command(name="addchannel", description="Add a counting channel")
async def addchannel(interaction: discord.Interaction):
    async with pool.acquire() as conn:
        await conn.execute(f"INSERT INTO guild_{interaction.guild.id}_counting (channel_id) VALUES ($1) ON CONFLICT DO NOTHING", interaction.channel_id)
    await interaction.response.send_message("This channel is now a counting channel!", ephemeral=True)

# /removechannel command
@tree.command(name="removechannel", description="Remove this counting channel")
async def removechannel(interaction: discord.Interaction):
    async with pool.acquire() as conn:
        await conn.execute(f"DELETE FROM guild_{interaction.guild.id}_counting WHERE channel_id = $1", interaction.channel_id)
    await interaction.response.send_message("This channel is no longer a counting channel.", ephemeral=True)

# /daily command
@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    async with pool.acquire() as conn:
        now = datetime.utcnow()
        row = await conn.fetchrow(f"SELECT balance, last_daily FROM guild_{interaction.guild.id}_users WHERE user_id = $1", interaction.user.id)
        if row:
            if row["last_daily"] and now - row["last_daily"] < timedelta(hours=24):
                await interaction.response.send_message("You've already claimed your daily reward today!", ephemeral=True)
                return
            new_balance = row["balance"] + 100
            await conn.execute(f"""
                UPDATE guild_{interaction.guild.id}_users SET balance = $1, last_daily = $2 WHERE user_id = $3
            """, new_balance, now, interaction.user.id)
        else:
            await conn.execute(f"""
                INSERT INTO guild_{interaction.guild.id}_users (user_id, balance, last_daily) VALUES ($1, 100, $2)
            """, interaction.user.id, now)
        await interaction.response.send_message("You claimed 100 coins!", ephemeral=True)

# /balance command
@tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT balance FROM guild_{interaction.guild.id}_users WHERE user_id = $1", interaction.user.id)
        if row:
            await interaction.response.send_message(f"You have {row['balance']} coins.", ephemeral=True)
        else:
            await interaction.response.send_message("You have 0 coins.", ephemeral=True)

# /trivia command
@tree.command(name="trivia", description="Answer a trivia question!")
async def trivia(interaction: discord.Interaction):
    import random
    q = random.choice(trivia_questions)
    correct = q["correct"]
    view = discord.ui.View()
    for key, choice in q["choices"].items():
        async def callback(interaction_inner, k=key):
            if k == correct:
                await interaction_inner.response.send_message("Correct!", ephemeral=True)
            else:
                await interaction_inner.response.send_message(f"Wrong! The correct answer was {correct}", ephemeral=True)
        button = discord.ui.Button(label=choice, style=discord.ButtonStyle.blurple)
        button.callback = callback
        view.add_item(button)
    await interaction.response.send_message(embed=discord.Embed(title=q["question"]), view=view, ephemeral=True)

bot.run(os.environ["DISCORD_TOKEN"])
