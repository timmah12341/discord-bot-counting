import discord
from discord.ext import commands
from discord import app_commands
import asyncpg
import json
import os
import math
import random
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATABASE_URL = os.environ["DATABASE_URL"]
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
pool = None
trivia_questions = []

safe_globals = {
    "__builtins__": {},
    "math": math,
    "pi": math.pi,
    "e": math.e,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "abs": abs,
    "pow": pow,
    "round": round
}

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

async def init_guild_data(guild_id):
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS guild_{guild_id}_counting (
                channel_id BIGINT PRIMARY KEY,
                last_number DOUBLE PRECISION DEFAULT 0
            )
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS guild_{guild_id}_users (
                user_id BIGINT PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                last_daily TIMESTAMP
            )
        """)

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

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    try:
        expr = message.content.strip()
        result = eval(expr, safe_globals)
        if not isinstance(result, (int, float)):
            return
        result = round(result, 6)
    except:
        return

    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM guild_{message.guild.id}_counting WHERE channel_id = $1", message.channel.id)
        last = row["last_number"] if row else 0

        if (result == last + 1) or (last == 0 and result == 1):
            if row:
                await conn.execute(f"UPDATE guild_{message.guild.id}_counting SET last_number = $1 WHERE channel_id = $2", result, message.channel.id)
            else:
                await conn.execute(f"INSERT INTO guild_{message.guild.id}_counting (channel_id, last_number) VALUES ($1, $2)", message.channel.id, result)
        else:
            await conn.execute(f"UPDATE guild_{message.guild.id}_counting SET last_number = 0 WHERE channel_id = $1", message.channel.id)
            await message.channel.send(f"Wrong number or math! `{expr}` is not next. Restarting from 1.")

@tree.command(name="addchannel", description="Add this channel as a counting channel")
async def addchannel(interaction: discord.Interaction):
    await init_guild_data(interaction.guild.id)
    async with pool.acquire() as conn:
        await conn.execute(f"""
            INSERT INTO guild_{interaction.guild.id}_counting (channel_id, last_number)
            VALUES ($1, 0)
            ON CONFLICT (channel_id) DO NOTHING
        """, interaction.channel.id)
    await interaction.response.send_message("This channel is now a counting channel!", ephemeral=True)

@tree.command(name="removechannel", description="Remove this counting channel")
async def removechannel(interaction: discord.Interaction):
    async with pool.acquire() as conn:
        await conn.execute(f"""
            DELETE FROM guild_{interaction.guild.id}_counting WHERE channel_id = $1
        """, interaction.channel.id)
    await interaction.response.send_message("This channel is no longer a counting channel.", ephemeral=True)

@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    async with pool.acquire() as conn:
        now = datetime.utcnow()
        row = await conn.fetchrow(f"""
            SELECT balance, last_daily FROM guild_{interaction.guild.id}_users WHERE user_id = $1
        """, interaction.user.id)

        if row:
            if row["last_daily"] and now - row["last_daily"] < timedelta(hours=24):
                await interaction.response.send_message("You've already claimed your daily reward today!", ephemeral=True)
                return
            new_balance = row["balance"] + 100
            await conn.execute(f"""
                UPDATE guild_{interaction.guild.id}_users
                SET balance = $1, last_daily = $2
                WHERE user_id = $3
            """, new_balance, now, interaction.user.id)
        else:
            await conn.execute(f"""
                INSERT INTO guild_{interaction.guild.id}_users (user_id, balance, last_daily)
                VALUES ($1, 100, $2)
            """, interaction.user.id, now)

        await interaction.response.send_message("You claimed 100 coins!", ephemeral=True)

@tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"""
            SELECT balance FROM guild_{interaction.guild.id}_users WHERE user_id = $1
        """, interaction.user.id)
        amount = row["balance"] if row else 0
        await interaction.response.send_message(f"You have {amount} coins.", ephemeral=True)

@tree.command(name="trivia", description="Answer a trivia question!")
async def trivia(interaction: discord.Interaction):
    q = random.choice(trivia_questions)
    correct = q["correct"]

    class TriviaView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            for key, value in q["choices"].items():
                self.add_item(discord.ui.Button(label=value, custom_id=key))

        async def interaction_check(self, i: discord.Interaction) -> bool:
            chosen = i.data['custom_id']
            if chosen == correct:
                await i.response.send_message("Correct!", ephemeral=True)
            else:
                await i.response.send_message(f"Wrong! The correct answer was: {correct}", ephemeral=True)
            self.stop()
            return True

    embed = discord.Embed(title=q["question"])
    await interaction.response.send_message(embed=embed, view=TriviaView(), ephemeral=True)

bot.run(DISCORD_TOKEN)
