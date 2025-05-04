import discord
from discord.ext import commands, tasks
import asyncpg
import json
import os
from dotenv import load_dotenv
import random
import asyncio

# Load environment variables from .env file
load_dotenv()

# Define bot and set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='/', intents=intents)

# PostgreSQL connection pool
DATABASE_URL = os.getenv("DATABASE_URL")

# Create a connection pool
async def create_db_pool():
    global pool
    pool = await asyncpg.create_pool(dsn=DATABASE_URL)

# Trivia refresh function
async def refresh_trivia():
    with open('trivia.json') as f:
        trivia_data = json.load(f)

    async with pool.acquire() as conn:
        # Delete existing trivia questions to refresh them
        await conn.execute('DELETE FROM trivia_questions')

        # Insert new trivia questions from trivia.json
        for entry in trivia_data:
            await conn.execute('''
                INSERT INTO trivia_questions (question, choice_a, choice_b, choice_c, correct)
                VALUES ($1, $2, $3, $4, $5)
            ''', entry['question'], entry['choices']['A'], entry['choices']['B'], entry['choices']['C'], entry['correct'])

# On bot ready, connect to the DB and refresh trivia questions
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await create_db_pool()
    await refresh_trivia()

# Commands

# Set the counting channel
@bot.command()
async def setchannel(ctx):
    # Save the counting channel per guild
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO counting_channels (guild_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2
        ''', ctx.guild.id, ctx.channel.id)
    await ctx.send(f'Counting channel set to {ctx.channel.name}.')

# Add a counting channel
@bot.command()
async def addchannel(ctx):
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO counting_channels (guild_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO NOTHING
        ''', ctx.guild.id, ctx.channel.id)
    await ctx.send(f'Counting channel added: {ctx.channel.name}')

# Remove a counting channel
@bot.command()
async def removechannel(ctx):
    async with pool.acquire() as conn:
        await conn.execute('''
            DELETE FROM counting_channels WHERE guild_id = $1 AND channel_id = $2
        ''', ctx.guild.id, ctx.channel.id)
    await ctx.send(f'Counting channel removed: {ctx.channel.name}')

# Trivia question command
@bot.command()
async def trivia(ctx):
    async with pool.acquire() as conn:
        # Fetch a random trivia question
        question_row = await conn.fetchrow('SELECT * FROM trivia_questions ORDER BY RANDOM() LIMIT 1')

    question = question_row['question']
    choices = {
        'A': question_row['choice_a'],
        'B': question_row['choice_b'],
        'C': question_row['choice_c']
    }
    correct_answer = question_row['correct']

    # Create a trivia message with buttons for answers
    embed = discord.Embed(title="Trivia Time!", description=question)
    for choice, answer in choices.items():
        embed.add_field(name=choice, value=answer, inline=False)

    message = await ctx.send(embed=embed)

    # Add buttons for answering
    await message.add_reaction("🇦")
    await message.add_reaction("🇧")
    await message.add_reaction("🇨")

    # Check answer reactions
    def check(reaction, user):
        return user != bot.user and reaction.message.id == message.id

    try:
        reaction, user = await bot.wait_for('reaction_add', check=check, timeout=30)
        if reaction.emoji == "🇦" and correct_answer == 'A':
            await ctx.send(f'Correct! {user.mention} chose {reaction.emoji}')
        elif reaction.emoji == "🇧" and correct_answer == 'B':
            await ctx.send(f'Correct! {user.mention} chose {reaction.emoji}')
        elif reaction.emoji == "🇨" and correct_answer == 'C':
            await ctx.send(f'Correct! {user.mention} chose {reaction.emoji}')
        else:
            await ctx.send(f'Incorrect. The correct answer was {correct_answer}.')
    except asyncio.TimeoutError:
        await ctx.send('Time is up! No one answered in time.')

# Balance command
@bot.command()
async def balance(ctx):
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM balances WHERE user_id = $1', ctx.author.id)
        if row:
            balance = row['balance']
            await ctx.send(f'{ctx.author.mention}, your balance is {balance} coins.')
        else:
            await ctx.send(f'{ctx.author.mention}, you have no balance yet.')

# Daily reward command
@bot.command()
async def daily(ctx):
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM last_daily WHERE user_id = $1', ctx.author.id)
        if row and row['last_claimed'] > (int(time.time()) - 86400):
            await ctx.send(f'{ctx.author.mention}, you have already claimed your daily reward!')
            return

        # Give daily reward (e.g., 100 coins)
        await conn.execute('''
            INSERT INTO balances (user_id, balance)
            VALUES ($1, 100)
            ON CONFLICT (user_id) DO UPDATE SET balance = balance + 100
        ''', ctx.author.id)

        await conn.execute('''
            INSERT INTO last_daily (user_id, last_claimed)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET last_claimed = $2
        ''', ctx.author.id, int(time.time()))

        await ctx.send(f'{ctx.author.mention}, you have claimed your daily reward of 100 coins!')

# Leaderboard command
@bot.command()
async def leaderboard(ctx):
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM balances ORDER BY balance DESC LIMIT 10')
    
    leaderboard = '\n'.join([f'{i+1}. <@{row["user_id"]}>: {row["balance"]} coins' for i, row in enumerate(rows)])

    await ctx.send(f'**Leaderboard**\n{leaderboard}')

# Profile command
@bot.command()
async def profile(ctx):
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM balances WHERE user_id = $1', ctx.author.id)
        if row:
            balance = row['balance']
            await ctx.send(f'{ctx.author.mention}, your profile: {balance} coins.')
        else:
            await ctx.send(f'{ctx.author.mention}, you have no profile yet.')

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
