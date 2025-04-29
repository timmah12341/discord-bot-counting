import os
import discord
from discord.ext import commands
import json
import random
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Load your token from the environment variable
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("No Discord token found in environment variables!")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# Example command: Hello command
@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')

# Example trivia command with trivia.json
@bot.command()
async def trivia(ctx):
    # Load trivia questions from trivia.json
    with open('trivia.json', 'r') as file:
        trivia_data = json.load(file)

    # Select a random trivia question
    question = random.choice(trivia_data)
    choices = question["choices"]

    # Send the trivia question as an embed
    embed = discord.Embed(
        title="Trivia Question",
        description=question["question"],
        color=discord.Color.blue()
    )

    for key, value in choices.items():
        embed.add_field(name=key, value=value, inline=False)

    # Send a private message to the user with the trivia question
    await ctx.author.send(embed=embed)

    # Wait for the user's response (mockup: simulating the answer)
    def check(msg):
        return msg.author == ctx.author and msg.content.upper() in choices.keys()

    try:
        response = await bot.wait_for('message', check=check, timeout=30)
        if response.content.upper() == question["correct"]:
            await ctx.author.send(f'Correct! 🎉 The answer is **{response.content.upper()}**')
        else:
            await ctx.author.send(f'Incorrect! 😢 The correct answer was **{question["correct"]}**')
    except asyncio.TimeoutError:
        await ctx.author.send("You took too long to answer. Please try again later!")

# Example /inventory command
@bot.command()
async def inventory(ctx):
    # Check if user has an inventory in the database (mockup)
    user_id = str(ctx.author.id)
    try:
        with open('db.json', 'r') as db_file:
            db_data = json.load(db_file)

        user_inventory = db_data.get("inventory", {}).get(user_id, [])
        if user_inventory:
            await ctx.send(f"Your inventory: {', '.join(user_inventory)}")
        else:
            await ctx.send("You don't have any items in your inventory.")
    except FileNotFoundError:
        await ctx.send("Database not found, please try again later!")

# Example /shop command
@bot.command()
async def shop(ctx):
    shop_items = ["Cookie 🍪", "Potion 🧪", "Sword ⚔️", "Shield 🛡️"]
    embed = discord.Embed(
        title="Shop",
        description="Welcome to the shop! Choose an item to buy.",
        color=discord.Color.green()
    )

    for item in shop_items:
        embed.add_field(name=item, value=f"Price: 100 coins", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item: str):
    # Check if user has enough coins (mockup: we'll just deduct from their balance)
    user_id = str(ctx.author.id)
    try:
        with open('db.json', 'r') as db_file:
            db_data = json.load(db_file)

        user_data = db_data.get("economy", {}).get(user_id, {"coins": 0})

        item_prices = {"Cookie 🍪": 100, "Potion 🧪": 200, "Sword ⚔️": 300, "Shield 🛡️": 400}

        if item in item_prices:
            if user_data["coins"] >= item_prices[item]:
                user_data["coins"] -= item_prices[item]
                db_data["economy"][user_id] = user_data

                # Add item to the user's inventory
                if "inventory" not in db_data:
                    db_data["inventory"] = {}

                if user_id not in db_data["inventory"]:
                    db_data["inventory"][user_id] = []

                db_data["inventory"][user_id].append(item)

                with open('db.json', 'w') as db_file:
                    json.dump(db_data, db_file)

                await ctx.send(f'You bought {item} successfully! 🛍️')
            else:
                await ctx.send(f'You don\'t have enough coins to buy {item}.')
        else:
            await ctx.send('Item not found in the shop.')
    except FileNotFoundError:
        await ctx.send("Database not found, please try again later!")

# Run the bot using the token from the environment variable
bot.run(DISCORD_TOKEN)
