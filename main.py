import discord
from discord.ext import commands, tasks
import asyncpg
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables from .env file
load_dotenv()

# Get the Discord token and PostgreSQL URL from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

# Global variable for PostgreSQL connection pool
pool = None

# Create the bot instance
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# Function to initialize the PostgreSQL connection pool
async def create_db_pool():
    global pool
    pool = await asyncpg.create_pool(dsn=DATABASE_URL)

# Bot event: on_ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # Initialize the database pool when the bot is ready
    await create_db_pool()

# Example of the /setchannel command to set the channel for counting
@bot.command()
async def setchannel(ctx):
    """Sets the channel to send counting messages."""
    # Set the counting channel in the database
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO settings (guild_id, counting_channel) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET counting_channel = $2", ctx.guild.id, str(ctx.channel.id))
    await ctx.send(f"Counting channel set to {ctx.channel.name}.")

# Example of the /shop command
@bot.command()
async def shop(ctx):
    """Displays the shop options."""
    embed = discord.Embed(title="Shop", description="Buy items with points!")
    embed.add_field(name="Item 1", value="A fun item!", inline=False)
    embed.add_field(name="Item 2", value="Another fun item!", inline=False)
    await ctx.send(embed=embed)

# Example of the /balance command to check a user's balance
@bot.command()
async def balance(ctx):
    """Shows the user's balance."""
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT balance FROM user_balances WHERE user_id = $1", ctx.author.id)
        balance = result['balance'] if result else 0
    await ctx.send(f"Your balance is {balance} points.")

# Example of the /daily command to give a daily reward
@bot.command()
async def daily(ctx):
    """Gives the user their daily reward."""
    async with pool.acquire() as conn:
        # Assuming there's a `user_balances` table with `user_id` and `balance`
        await conn.execute("INSERT INTO user_balances (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = balance + $2", ctx.author.id, 10)
    await ctx.send(f"You've received your daily reward of 10 points!")

# Example of the /meme command to send a cryptic meme
@bot.command()
async def meme(ctx):
    """Sends a cryptic meme."""
    await ctx.send("ün ün ün 𓀂𓀇𓀉𓀍𓀠𓁀𓁂𓀱𓁉𓀿𓀪𓁶𓂧𓂮𓂫𓃹𓃳𓄜𓄲𓄓𓅆𓅢𓅼𓆀𓆾𓈙𓉒𓉼𓊪𓋜𓋒𓍲𓎳𓁀𓄲𓅢 ün ün ün ün ün ün AAAAAAAAAAAAAOOOOOOOOORRRRXT 01001000 0110101 01101000 01100101 0010000 01001001 0010000 01101000 01100001 01110110 01100101 00100000 01110011 01100101 01111000 00100000 01110111 01101001 01110100 01101000 00100000 01101101 00100000 01110000 01101111 01101111 01110000 01101111 01101111 00100000 01110000 01110000")

# Example of the /funny command to show an image
@bot.command()
async def funny(ctx):
    """Sends a funny image."""
    image_url = "https://cdn.discordapp.com/attachments/1368349957718802572/1368357820507885618/image.png?ex=6817ee07&is=68169c87&hm=537c1b38a8525ba52acb5e2a3c6b36796bb3ae85e9a72124162e7011b0d68aa3&"
    await ctx.send(image_url)

# Example of the /trivia command to ask a trivia question
@bot.command()
async def trivia(ctx):
    """Asks a trivia question."""
    question = "What is the capital of France?"
    choices = {"A": "Paris", "B": "London", "C": "Berlin"}
    correct = "A"
    
    # Send the trivia question with options
    embed = discord.Embed(title=question)
    for key, value in choices.items():
        embed.add_field(name=key, value=value, inline=False)
    
    await ctx.send(embed=embed)

    # Simulate the answer (you'd normally check the user's answer here)
    await asyncio.sleep(5)  # Wait for a few seconds before revealing the answer
    await ctx.send(f"The correct answer was {correct}: {choices[correct]}")

# Example of the /leaderboard command to display a leaderboard
@bot.command()
async def leaderboard(ctx):
    """Shows the leaderboard."""
    async with pool.acquire() as conn:
        results = await conn.fetch("SELECT user_id, balance FROM user_balances ORDER BY balance DESC LIMIT 10")
        leaderboard = "\n".join([f"{i+1}. <@{row['user_id']}>: {row['balance']} points" for i, row in enumerate(results)])
    await ctx.send(f"Leaderboard:\n{leaderboard}")

# Running the bot
bot.run(TOKEN)
