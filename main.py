import discord
from discord.ext import commands
import json
import random
import os

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Load data from a JSON file to store the counts, economy, and other data
try:
    with open('db.json', 'r') as f:
        db = json.load(f)
except FileNotFoundError:
    db = {
        "current_number": 1,
        "leaderboard": {},
        "economy": {},
        "banned_words": [],
        "inventory": {},
        "coins": {}
    }

# Fetch the Discord token from the environment variable (use this on Railway or similar platforms)
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')  # Use your environment variable for the token

# Check if the token is found
if DISCORD_TOKEN is None:
    raise ValueError("Discord token is missing! Please set the DISCORD_TOKEN environment variable.")

# Counting logic - count stays at 1, but 10 messages are sent in DM
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Get current count (always 1)
    count = db.get("current_number", 1)

    # Send 10 DMs to the user
    for i in range(100):
        try:
            await message.author.send(f"Message {i + 1}: Keep up the good work! 🎉")
        except discord.errors.Forbidden:
            print(f"Could not DM {message.author}.")

    # Create an embed to show the current count (which remains at 1)
    embed = discord.Embed(
        title="Message Count Update",
        description=f"Message count is still: **{count}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="Status", value="100 messages have been sent! 😎", inline=False)
    embed.set_footer(text="Keep up the good work!")

    # Send the embed back as a DM or to the channel
    await message.author.send(embed=embed)

    # Save the count back into the database
    db["current_number"] = count
    with open('db.json', 'w') as f:
        json.dump(db, f)

    # Allow the bot to process other commands
    await bot.process_commands(message)

# Trivia command
@bot.command()
async def trivia(ctx):
    try:
        with open('trivia.json', 'r') as f:
            trivia_data = json.load(f)
    except FileNotFoundError:
        await ctx.send("Trivia data not found. Please upload trivia.json.")
        return

    # Pick a random trivia question
    question = random.choice(trivia_data['questions'])
    correct_answer = question['correct_answer']
    choices = question['choices']

    # Create an embed to show the trivia question
    embed = discord.Embed(
        title="Trivia Question",
        description=question['question'],
        color=discord.Color.green()
    )
    for idx, choice in enumerate(choices, 1):
        embed.add_field(name=f"Choice {idx}", value=choice, inline=False)
    
    # Send the embed with buttons to the user
    buttons = []
    for idx, choice in enumerate(choices, 1):
        buttons.append(discord.ui.Button(label=f"Choice {idx}", custom_id=str(idx)))
    
    await ctx.send(embed=embed, components=buttons)

# Shop command
@bot.command()
async def shop(ctx):
    items = ["Cookie 🍪", "Potion 🧪", "Sword ⚔️", "Shield 🛡️"]
    prices = [50, 100, 200, 150]
    
    embed = discord.Embed(
        title="Shop",
        description="Welcome to the shop! 🛍️ Here are the items available for purchase:",
        color=discord.Color.purple()
    )
    for item, price in zip(items, prices):
        embed.add_field(name=item, value=f"Price: {price} coins", inline=False)

    await ctx.send(embed=embed)

# Inventory command
@bot.command()
async def inventory(ctx):
    user_id = str(ctx.author.id)
    inventory = db["inventory"].get(user_id, [])
    
    if not inventory:
        await ctx.send(f"{ctx.author.mention}, your inventory is empty! 😔")
        return
    
    embed = discord.Embed(
        title=f"{ctx.author.name}'s Inventory",
        description="Your items are:",
        color=discord.Color.blue()
    )
    for item in inventory:
        embed.add_field(name=item, value="Just an item!", inline=False)
    
    await ctx.send(embed=embed)

# Profile command
@bot.command()
async def profile(ctx):
    embed = discord.Embed(
        title=f"{ctx.author.name}'s Profile",
        description=f"Here is your profile picture, {ctx.author.mention}!",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=ctx.author.avatar.url)
    embed.set_footer(text="Profile Bot")

    await ctx.send(embed=embed)

# Economy command
@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    coins = db["coins"].get(user_id, 0)
    
    embed = discord.Embed(
        title=f"{ctx.author.name}'s Balance",
        description=f"You have {coins} coins 💰.",
        color=discord.Color.green()
    )
    
    await ctx.send(embed=embed)

# Add/remove banned words
@bot.command()
async def add_banned_word(ctx, word: str):
    db["banned_words"].append(word)
    with open('db.json', 'w') as f:
        json.dump(db, f)
    await ctx.send(f"Word '{word}' added to banned words list.")

@bot.command()
async def remove_banned_word(ctx, word: str):
    if word in db["banned_words"]:
        db["banned_words"].remove(word)
        with open('db.json', 'w') as f:
            json.dump(db, f)
        await ctx.send(f"Word '{word}' removed from banned words list.")
    else:
        await ctx.send(f"Word '{word}' not found in the banned words list.")

# Running the bot
bot.run(DISCORD_TOKEN)
