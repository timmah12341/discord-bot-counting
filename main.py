import os
import discord
import json
from discord.ext import commands
from discord.ui import Button, View

# Setting up the bot with the required intents
intents = discord.Intents.default()
intents.message_content = True  # To read the message content
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize the count (global count variable) and database
count = 0

# Load trivia questions from trivia.json
def load_trivia():
    try:
        with open('trivia.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

trivia_data = load_trivia()

# Load database (db.json)
def load_db():
    try:
        with open('db.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Initialize the database
db = load_db()

# Event when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# Event when a new message is sent in the chat
@bot.event
async def on_message(message):
    global count

    if message.author == bot.user:
        return

    # Increment the message count for each new message
    count += 1

    # Create an embed response with style and emojis
    embed = discord.Embed(
        title="Message Count Update",
        description=f"Message count is now: **{count}**",
        color=discord.Color.blue()
    )
    
    if count % 2 != 0:
        embed.add_field(name="Status", value=f"Odd count! 🎉", inline=False)
        embed.set_footer(text="Keep the messages coming!")
    else:
        embed.add_field(name="Status", value=f"Even count! 😎", inline=False)
        embed.set_footer(text="Great job, team!")

    # Send the embed only to the person who sent the message
    await message.author.send(embed=embed)

    # Allow the bot to process other commands (if any)
    await bot.process_commands(message)

# Command to view the user's profile
@bot.command()
async def viewprofile(ctx):
    user = ctx.author
    embed = discord.Embed(title=f"{user.name}'s Profile", color=discord.Color.green())
    embed.set_thumbnail(url=user.avatar.url)
    embed.add_field(name="Username", value=user.name, inline=True)
    embed.add_field(name="ID", value=user.id, inline=True)
    embed.set_footer(text="This is your profile!")
    await ctx.send(embed=embed)

# Trivia command
@bot.command()
async def trivia(ctx):
    if not trivia_data:
        await ctx.send("Sorry, no trivia questions available!")
        return

    question = trivia_data[0]  # Take the first question from the list for simplicity
    choices = question["choices"]
    embed = discord.Embed(
        title=question["question"],
        color=discord.Color.orange()
    )

    # Adding choices to embed
    for key, value in choices.items():
        embed.add_field(name=f"{key}", value=value, inline=False)

    # Create buttons for user to select
    buttons = [
        Button(label="A", custom_id="A"),
        Button(label="B", custom_id="B"),
        Button(label="C", custom_id="C")
    ]

    # Add the buttons to the view
    view = View(timeout=15)
    for button in buttons:
        view.add_item(button)

    # Send the trivia question
    await ctx.send(embed=embed, view=view)

    # Wait for the response and check if the answer is correct
    def check(interaction):
        return interaction.user == ctx.author and interaction.data["custom_id"] in choices

    try:
        interaction = await bot.wait_for("interaction", timeout=15.0, check=check)
        correct_answer = question["correct"]
        selected = interaction.data["custom_id"]

        # Respond based on the selected answer
        if selected == correct_answer:
            response = "Correct! 🎉"
        else:
            response = f"Oops! The correct answer was {correct_answer}. 😓"

        await interaction.response.send_message(response, ephemeral=True)
    except TimeoutError:
        await ctx.send("Time's up! No answer received in time.")

# Shop command
@bot.command()
async def shop(ctx):
    user_id = str(ctx.author.id)
    if user_id not in db:
        db[user_id] = {"coins": 100, "items": []}  # Default coins if new user

    user_data = db[user_id]
    coins = user_data["coins"]
    items = user_data["items"]

    embed = discord.Embed(
        title=f"{ctx.author.name}'s Shop",
        color=discord.Color.purple()
    )
    embed.add_field(name="Coins", value=f"💰 {coins}", inline=False)
    embed.add_field(name="Items", value=f"{', '.join(items) if items else 'None'}", inline=False)

    embed.add_field(name="Items for Sale", value="🍪 Cookie: 50 coins", inline=False)
    embed.add_field(name="Use `/buy cookie` to purchase", value="After purchasing, use `/use cookie` to eat!", inline=False)
    
    await ctx.send(embed=embed)

# Buy command
@bot.command()
async def buy(ctx, item: str):
    user_id = str(ctx.author.id)
    if user_id not in db:
        db[user_id] = {"coins": 100, "items": []}

    user_data = db[user_id]
    coins = user_data["coins"]
    items = user_data["items"]

    if item.lower() == "cookie" and coins >= 50:
        user_data["coins"] -= 50
        user_data["items"].append("Cookie")
        await ctx.send(f"🎉 You have bought a Cookie! 🍪 Enjoy!")
    else:
        await ctx.send("❌ You don't have enough coins or the item is unavailable.")

# Use command for items (cookie example)
@bot.command()
async def use(ctx, item: str):
    user_id = str(ctx.author.id)
    if user_id not in db or item.lower() not in db[user_id]["items"]:
        await ctx.send("❌ You don't have that item!")
        return

    if item.lower() == "cookie":
        db[user_id]["items"].remove("Cookie")
        await ctx.send("🍪 *Nom nom* You ate a cookie and feel happy! 🎉")
    else:
        await ctx.send("❌ That item is not usable.")

# Save database to file on shutdown
@bot.event
async def on_close():
    with open('db.json', 'w') as f:
        json.dump(db, f)

# Run the bot using the token from an environment variable
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("No Discord token found in environment variables!")

bot.run(DISCORD_TOKEN)
