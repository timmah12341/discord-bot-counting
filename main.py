import discord
from discord.ext import commands, tasks
import asyncpg
import os
from dotenv import load_dotenv
from discord import app_commands

# Load environment variables from .env file
load_dotenv()

# Get the DATABASE_URL from the environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in environment variables!")

# Initialize the bot
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Create a global pool variable for database connection
pool = None

async def create_db_pool():
    """Create a database connection pool."""
    global pool
    pool = await asyncpg.create_pool(dsn=DATABASE_URL)
    print("Connected to the database")

@bot.event
async def on_ready():
    """Bot is ready."""
    print(f'Logged in as {bot.user}')
    await create_db_pool()

# Command to check if the bot is connected to the database
@bot.command()
async def check_db(ctx):
    """Check if the bot is connected to the database."""
    if pool is not None:
        await ctx.send("Database connection is active!")
    else:
        await ctx.send("Database connection is not established.")

# Example of a command to store and retrieve user data from the database
@bot.command()
async def set_balance(ctx, balance: int):
    """Set the balance for a user."""
    user_id = ctx.author.id
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = $2", user_id, balance)
    await ctx.send(f"Your balance has been set to {balance}.")

@bot.command()
async def get_balance(ctx):
    """Get the balance for a user."""
    user_id = ctx.author.id
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)
        if row:
            await ctx.send(f"Your balance is {row['balance']}.")
        else:
            await ctx.send("You don't have a balance set yet.")

# Trivia command example
@bot.command()
async def trivia(ctx, question: str, answer: str):
    """Ask a trivia question and store the answer."""
    user_id = ctx.author.id
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO trivia (user_id, question, answer) VALUES ($1, $2, $3)", user_id, question, answer)
    await ctx.send(f"Question: {question}\nAnswer: {answer}")

# Command to set the counting channel
@bot.command()
async def setchannel(ctx):
    """Set the channel for counting."""
    channel_id = ctx.channel.id
    # Save the channel ID for counting purposes (to database or in-memory)
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO settings (setting_key, setting_value) VALUES ($1, $2) ON CONFLICT (setting_key) DO UPDATE SET setting_value = $2", 'counting_channel', str(channel_id))
    await ctx.send(f"This channel has been set as the counting channel.")

# Command to get the counting channel
@bot.command()
async def getchannel(ctx):
    """Get the currently set counting channel."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT setting_value FROM settings WHERE setting_key = $1", 'counting_channel')
        if row:
            channel = bot.get_channel(int(row['setting_value']))
            await ctx.send(f"The counting channel is {channel.mention}.")
        else:
            await ctx.send("No counting channel has been set yet.")

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
