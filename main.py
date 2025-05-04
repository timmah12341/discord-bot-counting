import discord
from discord.ext import commands
import asyncpg
import json
import os

# Environment variables and database connection
DATABASE_URL = os.getenv('DATABASE_URL')

# Create an instance of the bot
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = bot.tree

async def setup_database():
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Create tables if not exists
    await conn.execute('''
    CREATE TABLE IF NOT EXISTS trivia_questions (
        id SERIAL PRIMARY KEY,
        question TEXT NOT NULL,
        choices JSONB NOT NULL,
        correct_answer TEXT NOT NULL
    );
    ''')

    await conn.execute('''
    CREATE TABLE IF NOT EXISTS counting_channels (
        guild_id BIGINT PRIMARY KEY,
        channel_ids TEXT[]
    );
    ''')
    
    await conn.close()

async def refresh_trivia():
    conn = await asyncpg.connect(DATABASE_URL)

    # Fetch trivia questions from trivia.json
    with open('trivia.json') as f:
        trivia_data = json.load(f)

    # Delete old trivia questions and insert the new ones
    await conn.execute('DELETE FROM trivia_questions')
    for question in trivia_data['questions']:
        await conn.execute('''
            INSERT INTO trivia_questions(question, choices, correct_answer)
            VALUES($1, $2, $3)
        ''', question['question'], json.dumps(question['choices']), question['correct'])
    
    await conn.close()

# Register commands
@tree.command(name="setchannel", description="Set the counting channel")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conn = await asyncpg.connect(DATABASE_URL)
    guild_id = interaction.guild.id

    # Check if the guild exists in the database, if not create it
    existing = await conn.fetchrow('SELECT * FROM counting_channels WHERE guild_id = $1', guild_id)
    if not existing:
        await conn.execute('INSERT INTO counting_channels(guild_id, channel_ids) VALUES($1, $2)', guild_id, [str(channel.id)])
    else:
        # Add the new channel to the existing list
        updated_channels = existing['channel_ids']
        updated_channels.append(str(channel.id))
        await conn.execute('UPDATE counting_channels SET channel_ids = $1 WHERE guild_id = $2', updated_channels, guild_id)

    await conn.close()
    await interaction.response.send_message(f"Counting channel set to {channel.mention}")

@tree.command(name="removechannel", description="Remove a counting channel")
async def removechannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conn = await asyncpg.connect(DATABASE_URL)
    guild_id = interaction.guild.id

    # Get the existing channel list
    existing = await conn.fetchrow('SELECT * FROM counting_channels WHERE guild_id = $1', guild_id)
    if existing:
        updated_channels = [ch for ch in existing['channel_ids'] if ch != str(channel.id)]
        await conn.execute('UPDATE counting_channels SET channel_ids = $1 WHERE guild_id = $2', updated_channels, guild_id)
        await interaction.response.send_message(f"Removed {channel.mention} from counting channels.")
    else:
        await interaction.response.send_message("No counting channels found.")

    await conn.close()

@tree.command(name="trivia", description="Start a trivia game")
async def trivia(interaction: discord.Interaction):
    conn = await asyncpg.connect(DATABASE_URL)

    # Fetch a random trivia question
    question_data = await conn.fetchrow('SELECT * FROM trivia_questions ORDER BY RANDOM() LIMIT 1')
    question = question_data['question']
    choices = json.loads(question_data['choices'])
    
    await conn.close()
    
    # Send the trivia question and choices to the user
    await interaction.response.send_message(f"**{question}**\n"
                                            f"A: {choices['A']}\n"
                                            f"B: {choices['B']}\n"
                                            f"C: {choices['C']}")

@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    # You can implement daily rewards here (e.g., adding money, XP, etc.)
    await interaction.response.send_message("You have claimed your daily reward!")

@bot.event
async def on_ready():
    await setup_database()  # Set up the database when the bot starts
    await refresh_trivia()  # Load trivia questions into the database
    await bot.tree.sync()  # Sync all commands with Discord
    print(f'Logged in as {bot.user}')

bot.run(os.getenv('DISCORD_TOKEN'))
