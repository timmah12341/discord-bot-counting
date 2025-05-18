import discord
from discord.ext import commands
from discord import app_commands
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

intents = discord.Intents.default()
intents.message_content = True
intents.typing = False

bot = commands.Bot(command_prefix="!", intents=intents)

# Connect to PostgreSQL database
async def get_db_connection():
    return await asyncpg.connect(DATABASE_URL)

# Add counting channel command
@bot.tree.command(name="addchannel")
@app_commands.describe(channel="The channel to add to the counting system.")
async def addchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conn = await get_db_connection()
    guild_id = interaction.guild.id
    try:
        # Creating the table if it doesn't exist for the guild
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS guild_{guild_id}_counting (
                channel_id BIGINT PRIMARY KEY,
                last_number INT DEFAULT 0
            )
        """)
        # Inserting the channel into the database
        await conn.execute(f"""
            INSERT INTO guild_{guild_id}_counting (channel_id) 
            VALUES ($1) 
            ON CONFLICT (channel_id) DO NOTHING
        """, channel.id)
        
        await interaction.response.send_message(f"Channel {channel.mention} added to the counting system!")
    except Exception as e:
        await interaction.response.send_message(f"Error adding channel: {str(e)}")
    finally:
        await conn.close()

# Remove counting channel command
@bot.tree.command(name="removechannel")
@app_commands.describe(channel="The channel to remove from the counting system.")
async def removechannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conn = await get_db_connection()
    guild_id = interaction.guild.id
    try:
        # Removing the channel from the counting system
        await conn.execute(f"DELETE FROM guild_{guild_id}_counting WHERE channel_id = $1", channel.id)
        await interaction.response.send_message(f"Channel {channel.mention} removed from the counting system!")
    except Exception as e:
        await interaction.response.send_message(f"Error removing channel: {str(e)}")
    finally:
        await conn.close()

# Shop command
@bot.tree.command(name="shop")
async def shop(interaction: discord.Interaction):
    conn = await get_db_connection()
    guild_id = interaction.guild.id
    
    # Example items
    items = [
        {"name": "Mystery Box", "description": "A random surprise!", "price": 100},
        {"name": "Super Role", "description": "A super cool role", "price": 500}
    ]
    
    shop_embed = discord.Embed(title="Shop", description="Browse the available items.", color=discord.Color.blue())
    for item in items:
        shop_embed.add_field(name=item["name"], value=f"{item['description']} - {item['price']} coins", inline=False)
    
    # Sending the shop embed with buy buttons
    view = discord.ui.View()
    for item in items:
        button = discord.ui.Button(label=f"Buy {item['name']}", custom_id=f"buy_{item['name'].lower().replace(' ', '_')}")
        view.add_item(button)
    
    await interaction.response.send_message(embed=shop_embed, view=view)

    # Close the connection
    await conn.close()

# Button handler for shop purchases
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.custom_id.startswith("buy_"):
            item_name = interaction.custom_id.split("_", 1)[1].replace("_", " ").title()
            await interaction.response.send_message(f"You've bought a {item_name}!", ephemeral=True)

# Counting feature
@bot.event
async def on_message(message):
    if message.channel.id not in [channel.id for channel in message.guild.text_channels]:
        return
    
    conn = await get_db_connection()
    guild_id = message.guild.id
    
    # Check if the channel is in the counting system
    result = await conn.fetchrow(f"SELECT last_number FROM guild_{guild_id}_counting WHERE channel_id = $1", message.channel.id)
    
    if result:
        last_number = result["last_number"]
        try:
            number = int(message.content)
            if number == last_number + 1:
                await conn.execute(f"UPDATE guild_{guild_id}_counting SET last_number = $1 WHERE channel_id = $2", number, message.channel.id)
            else:
                await message.channel.send(f"Oops! The next number should be {last_number + 1}. Try again!")
        except ValueError:
            await message.channel.send("Please only send numbers!")
    
    await conn.close()

# Leaderboard command
@bot.tree.command(name="leaderboard")
async def leaderboard(interaction: discord.Interaction):
    conn = await get_db_connection()
    guild_id = interaction.guild.id
    
    # Fetching all users and their scores
    results = await conn.fetch(f"SELECT user_id, score FROM guild_{guild_id}_leaderboard ORDER BY score DESC LIMIT 10")
    
    leaderboard_embed = discord.Embed(title="Leaderboard", color=discord.Color.green())
    for idx, result in enumerate(results, 1):
        user = await bot.fetch_user(result["user_id"])
        leaderboard_embed.add_field(name=f"{idx}. {user.name}", value=f"Score: {result['score']}", inline=False)
    
    await interaction.response.send_message(embed=leaderboard_embed)

    await conn.close()

# Daily command
@bot.tree.command(name="daily")
async def daily(interaction: discord.Interaction):
    conn = await get_db_connection()
    guild_id = interaction.guild.id
    user_id = interaction.user.id
    
    # Add daily reward logic here (e.g., increment balance)
    # For now, just a placeholder message
    await conn.execute(f"INSERT INTO guild_{guild_id}_users (user_id, balance) VALUES ($1, 0) ON CONFLICT (user_id) DO NOTHING")
    
    await interaction.response.send_message("You have claimed your daily reward!")

    await conn.close()

# Balance command
@bot.tree.command(name="balance")
async def balance(interaction: discord.Interaction):
    conn = await get_db_connection()
    guild_id = interaction.guild.id
    user_id = interaction.user.id
    
    # Fetch the user's balance
    result = await conn.fetchrow(f"SELECT balance FROM guild_{guild_id}_users WHERE user_id = $1", user_id)
    if result:
        balance = result["balance"]
        await interaction.response.send_message(f"Your balance: {balance} coins")
    else:
        await interaction.response.send_message("You don't have an account. Use the /daily command to create one!")
    
    await conn.close()

# On bot ready event
@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")

# Running the bot
bot.run(TOKEN)
