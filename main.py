import discord
from discord.ext import commands, tasks
import json
import random
import os
from datetime import datetime
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Load the token from the environment
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Load the database
if not os.path.exists('db.json'):
    with open('db.json', 'w') as db:
        json.dump({}, db)

# Load trivia questions
if not os.path.exists('trivia.json'):
    with open('trivia.json', 'w') as trivia_file:
        json.dump([{
            "question": "What is the capital of France?",
            "choices": {"A": "Paris", "B": "London", "C": "Rome"},
            "correct": "A"
        }], trivia_file)

with open('db.json', 'r') as f:
    db = json.load(f)

with open('trivia.json', 'r') as f:
    trivia = json.load(f)

# Load roles
SHOP_SEARCHER_ROLE = "Shop Searcher"

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Make sure the bot only responds in the allowed channel
    if message.channel.id != 1366574260554043503:
        return
    
    # Counting system (message counting)
    if message.content.isdigit():
        num = int(message.content)
        if num % 2 != 0:
            await message.channel.send(str(num + 1))
    
    # Update balance for each user
    if message.author.id not in db:
        db[message.author.id] = {
            "balance": 0,
            "inventory": [],
            "counted": 0
        }
    
    db[message.author.id]['counted'] += 1
    with open('db.json', 'w') as f:
        json.dump(db, f)

    await bot.process_commands(message)

@bot.command()
async def balance(ctx):
    """Shows your balance."""
    user = ctx.author
    if user.id not in db:
        db[user.id] = {"balance": 0, "inventory": [], "counted": 0}
    
    balance = db[user.id]["balance"]
    await ctx.send(f"{user.mention} Your current balance is: {balance} coins.")

@bot.command()
async def shop(ctx):
    """Shows the shop items."""
    items = {
        "🍪 Cookie": {"price": 50, "description": "A delicious cookie! *nom nom*"},
        "🔮 Magic Wand": {"price": 100, "description": "A wand that grants random powers."},
        "❓ a mystery ❓": {"price": 0, "description": "A mysterious item that grants the 'Shop Searcher' role!"}
    }
    
    embed = discord.Embed(title="Shop", description="Welcome to the shop! Here are the items you can buy:")
    for item, details in items.items():
        embed.add_field(name=item, value=f"Price: {details['price']} coins\nDescription: {details['description']}", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item_name):
    """Buy an item from the shop."""
    user = ctx.author
    if user.id not in db:
        db[user.id] = {"balance": 0, "inventory": [], "counted": 0}

    items = {
        "🍪 Cookie": {"price": 50, "description": "A delicious cookie! *nom nom*"},
        "🔮 Magic Wand": {"price": 100, "description": "A wand that grants random powers."},
        "❓ a mystery ❓": {"price": 0, "description": "A mysterious item that grants the 'Shop Searcher' role!"}
    }

    if item_name not in items:
        await ctx.send("Item not found in the shop.")
        return

    item = items[item_name]
    
    # Check if the user has enough balance
    if db[user.id]["balance"] < item["price"]:
        await ctx.send(f"{user.mention}, you do not have enough coins for this item.")
        return
    
    # Deduct the coins and add to the inventory
    db[user.id]["balance"] -= item["price"]
    db[user.id]["inventory"].append(item_name)
    
    if item_name == "❓ a mystery ❓":
        # Grant the Shop Searcher role
        role = discord.utils.get(user.guild.roles, name=SHOP_SEARCHER_ROLE)
        if role:
            await user.add_roles(role)
            await ctx.send(f"{user.mention}, you have received the {SHOP_SEARCHER_ROLE} role!")
        else:
            await ctx.send(f"Role {SHOP_SEARCHER_ROLE} not found on this server.")
    
    with open('db.json', 'w') as f:
        json.dump(db, f)

    await ctx.send(f"{user.mention} successfully bought {item_name}!")

@bot.command()
async def profile(ctx):
    """Shows your profile with balance, items, and counted numbers."""
    user = ctx.author
    if user.id not in db:
        db[user.id] = {"balance": 0, "inventory": [], "counted": 0}
    
    balance = db[user.id]["balance"]
    inventory = ', '.join(db[user.id]["inventory"]) if db[user.id]["inventory"] else "No items"
    counted = db[user.id]["counted"]
    
    embed = discord.Embed(title=f"{user.name}'s Profile", description=f"Here is your profile:")
    embed.set_thumbnail(url=user.avatar.url)
    embed.add_field(name="Balance", value=f"{balance} coins")
    embed.add_field(name="Inventory", value=inventory)
    embed.add_field(name="Total Numbers Counted", value=str(counted))

    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    """Shows the leaderboard of top counters."""
    sorted_users = sorted(db.items(), key=lambda x: x[1]['counted'], reverse=True)
    embed = discord.Embed(title="Leaderboard", description="Here are the top counters:")
    
    for i, (user_id, data) in enumerate(sorted_users[:10], 1):
        user = await bot.fetch_user(user_id)
        embed.add_field(name=f"{i}. {user.name}", value=f"Counted: {data['counted']}", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def trivia(ctx):
    """Starts a trivia question."""
    question_data = random.choice(trivia)
    question = question_data["question"]
    choices = question_data["choices"]
    correct_answer = question_data["correct"]
    
    buttons = [
        discord.ui.Button(label=choices["A"], custom_id="A"),
        discord.ui.Button(label=choices["B"], custom_id="B"),
        discord.ui.Button(label=choices["C"], custom_id="C")
    ]
    
    async def button_callback(interaction):
        if interaction.user.id == ctx.author.id:
            if interaction.custom_id == correct_answer:
                await interaction.response.send_message("Correct answer!", ephemeral=True)
            else:
                await interaction.response.send_message(f"Wrong answer! The correct answer was {choices[correct_answer]}", ephemeral=True)
            # Allow another question button after answering
            another_button = discord.ui.Button(label="Another Question", custom_id="another_question")
            await interaction.response.send_message("Click below for another question.", components=[another_button])
    
    # Send the trivia question
    embed = discord.Embed(title="Trivia Time!", description=question)
    for choice, answer in choices.items():
        embed.add_field(name=choice, value=answer, inline=False)
    
    await ctx.send(embed=embed, components=[buttons])

    for button in buttons:
        button.callback = button_callback

    await ctx.send(embed=embed)

bot.run(DISCORD_TOKEN)