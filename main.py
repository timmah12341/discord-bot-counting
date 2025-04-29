import discord
from discord.ext import commands
import random
import json
import math
import os

# Get the token from environment variables for security
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Load data from db.json
with open("db.json", "r") as f:
    db = json.load(f)

# Load trivia questions
with open("trivia.json", "r") as f:
    trivia_data = json.load(f)

# Helper function to save data
def save_db():
    with open("db.json", "w") as f:
        json.dump(db, f)

# Command to view profile
@bot.command()
async def profile(ctx):
    user_id = str(ctx.author.id)
    if user_id not in db['users']:
        db['users'][user_id] = {"balance": 0, "count": 0, "items": []}
        save_db()
    
    user_info = db['users'][user_id]
    embed = discord.Embed(
        title=f"{ctx.author.name}'s Profile",
        description=f"Balance: {user_info['balance']} coins\nCount: {user_info['count']} counted numbers\nItems: {', '.join(user_info['items']) if user_info['items'] else 'None'}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

# Command to check balance
@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    if user_id not in db['users']:
        db['users'][user_id] = {"balance": 0, "count": 0, "items": []}
        save_db()

    user_info = db['users'][user_id]
    await ctx.send(f"{ctx.author.name}, your balance is {user_info['balance']} coins.")

# Command to add coins
@bot.command()
async def addcoins(ctx, amount: int, user: discord.User = None):
    if ctx.author.id != 1234567890:  # Change this to your admin ID
        await ctx.send("You don't have permission to use this command.")
        return

    user = user or ctx.author
    user_id = str(user.id)
    if user_id not in db['users']:
        db['users'][user_id] = {"balance": 0, "count": 0, "items": []}
    
    db['users'][user_id]["balance"] += amount
    save_db()
    await ctx.send(f"Added {amount} coins to {user.name}'s balance.")

# Command to buy items
@bot.command()
async def buy(ctx, item_name: str):
    user_id = str(ctx.author.id)
    if user_id not in db['users']:
        db['users'][user_id] = {"balance": 0, "count": 0, "items": []}
    
    user_info = db['users'][user_id]

    if item_name == "❓ a mystery ❓":
        if "❓ a mystery ❓" not in user_info["items"]:
            # Give the role "shop searcher" and grant the item
            role = discord.utils.get(ctx.guild.roles, name="shop searcher")
            if role:
                await ctx.author.add_roles(role)
            user_info["items"].append("❓ a mystery ❓")
            db['users'][user_id] = user_info
            save_db()
            await ctx.send(f"Congrats {ctx.author.name}, you've received the 'shop searcher' role!")
        else:
            await ctx.send(f"{ctx.author.name}, you already own the '❓ a mystery ❓' item.")
    else:
        await ctx.send("Item not found in the shop!")

# Counting command - count the numbers with math
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    if user_id not in db['users']:
        db['users'][user_id] = {"balance": 0, "count": 0, "items": []}

    user_info = db['users'][user_id]

    try:
        user_number = eval(message.content)  # to allow math expressions, like pi
    except:
        return

    # Check if the number is correct
    if user_number == user_info["count"] + 1:
        user_info["count"] += 1
        db['users'][user_id] = user_info
        save_db()
        await message.channel.send(f"{message.author.name} counted correctly! The next number is {user_info['count'] + 1}")
    else:
        await message.channel.send(f"{message.author.name}, you messed up! The next number should be {user_info['count'] + 1}.")

    await bot.process_commands(message)

# Trivia command
@bot.command()
async def trivia(ctx):
    question = random.choice(trivia_data)
    embed = discord.Embed(title=question["question"], color=discord.Color.green())

    for option, answer in question["choices"].items():
        embed.add_field(name=option, value=answer, inline=False)

    # Send the question and wait for an answer
    await ctx.send(embed=embed)

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        response = await bot.wait_for('message', check=check, timeout=30)
        if response.content.upper() == question["correct"]:
            await ctx.send(f"Correct! The answer was {question['choices'][question['correct']]}.")
            user_id = str(ctx.author.id)
            if user_id not in db['users']:
                db['users'][user_id] = {"balance": 0, "count": 0, "items": []}
            db['users'][user_id]["balance"] += 10
            save_db()
        else:
            await ctx.send(f"Incorrect! The correct answer was {question['choices'][question['correct']]}.")
    except TimeoutError:
        await ctx.send(f"Time's up! The correct answer was {question['choices'][question['correct']]}.")
    
# Start the bot
bot.run(DISCORD_TOKEN)
