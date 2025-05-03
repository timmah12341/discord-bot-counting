import discord
from discord.ext import commands, tasks
import os
import random
import json
import time
from discord.ui import Button, View

# Load environment variables (e.g., DISCORD_TOKEN) from the environment
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Setup the bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Load trivia questions
with open('trivia.json', 'r') as file:
    trivia_data = json.load(file)

# User data storage (this will be saved in a JSON file)
user_data = {}

# Load saved user data
def load_user_data():
    global user_data
    try:
        with open("user_data.json", "r") as file:
            user_data = json.load(file)
    except FileNotFoundError:
        user_data = {}

def save_user_data():
    with open("user_data.json", "w") as file:
        json.dump(user_data, file, indent=4)

load_user_data()

# Counting system
count_channel_id = None  # To store the channel ID for counting

# Command to set the counting channel
@bot.tree.command(name="setchannel", description="Set the counting channel.")
async def setchannel(interaction: discord.Interaction):
    """Command to set the counting channel to the current one."""
    global count_channel_id
    count_channel_id = interaction.channel.id
    await interaction.response.send_message(f"Counting channel set to <#{count_channel_id}>.")

# Counting function (handles both math and regular counting)
@bot.event
async def on_message(message):
    global count_channel_id

    if message.author == bot.user:
        return

    if count_channel_id and message.channel.id == count_channel_id:
        if message.content.isdigit():
            num = int(message.content)
            if num % 2 != 0:  # User posts odd number
                next_number = num + 1
                await message.channel.send(str(next_number))  # Bot posts even number
            else:
                await message.channel.send("You posted an even number. Try posting an odd one!")
        else:
            # If the message has math symbols, evaluate it
            try:
                result = eval(message.content)
                await message.channel.send(f"Result: {result}")
            except Exception as e:
                await message.channel.send(f"Error in math expression: {e}")
    else:
        await bot.process_commands(message)

# Trivia command
@bot.command()
async def trivia(ctx):
    """Starts a trivia quiz."""
    question = random.choice(trivia_data)
    correct_answer = question["correct"]
    options = question["choices"]

    buttons = [
        Button(label=options["A"], custom_id="A"),
        Button(label=options["B"], custom_id="B"),
        Button(label=options["C"], custom_id="C"),
    ]

    view = View()
    for button in buttons:
        view.add_item(button)

    def check(interaction):
        return interaction.user == ctx.author and interaction.message == ctx.message

    await ctx.send(question["question"], view=view)

    # Wait for an answer
    interaction = await bot.wait_for("interaction", check=check)

    # Show the correct answer
    await interaction.response.send_message(f"The correct answer is: {correct_answer}.")

# Balance command
@bot.command()
async def balance(ctx):
    """Shows the user's balance."""
    user_id = str(ctx.author.id)
    balance = user_data.get(user_id, {}).get("balance", 0)
    await ctx.send(f"Your balance is: {balance} coins.")

# Daily reward command
@bot.command()
async def daily(ctx):
    """Gives the user a daily reward."""
    user_id = str(ctx.author.id)
    if user_id not in user_data:
        user_data[user_id] = {"balance": 0, "last_daily": 0}
        save_user_data()

    last_daily = user_data[user_id].get("last_daily", 0)
    current_time = int(time.time())

    # Check if the user has already claimed the daily reward
    if current_time - last_daily < 86400:
        await ctx.send("You have already claimed your daily reward! Try again tomorrow.")
    else:
        # Give daily reward (100 coins)
        user_data[user_id]["balance"] += 100
        user_data[user_id]["last_daily"] = current_time
        save_user_data()
        await ctx.send("You have claimed your daily reward of 100 coins!")

# Meme command
@bot.command()
async def meme(ctx):
    """Send a cryptic meme message."""
    await ctx.send("ün ün ün 𓀂𓀇𓀉𓀍𓀠𓁀𓁂𓀱𓁉𓀿𓀪𓁶𓂧𓂮𓂫𓃹𓃳𓄜𓄲𓄓𓅆𓅢𓅼𓆀𓆾𓈙𓉒𓉼𓊪𓋜𓋒𓍲𓎳𓁀𓄲𓅢 ün ün ün ün ün ün AAAAAAAAAAAAAOOOOOOOOORRRRXT 01001000 0110101 01101000 01100101 0010000 01001001 0010000 01101000 01100001 01110110 01100101 00100000 01110011 01100101 01111000 00100000 01110111 01101001 01110100 01101000 00100000 01101101 00100000 01110000 01101111 01101111 01110000 01101111 01101111 00100000 01110000 01110000")

# Funny command
@bot.command()
async def funny(ctx):
    """Send a funny image URL."""
    await ctx.send("Here’s a funny image for you: https://cdn.discordapp.com/attachments/1368349957718802572/1368357820507885618/image.png")

# Shop command (now allows role purchases)
@bot.command()
async def shop(ctx):
    """Show the available items in the shop."""
    items = {
        "Mystery Box": "A box full of surprises, buy to find out what you get!",
        "Magic Wand": "A wand that grants you a random bonus when used.",
        "❓ a mystery ❓": "A mystery box that grants the 'Shop Searcher' role! Free to claim."
    }

    item_buttons = []
    for item, description in items.items():
        button = Button(label=f"{item}: {description}", custom_id=item)
        item_buttons.append(button)

    view = View()
    for button in item_buttons:
        view.add_item(button)

    await ctx.send("Welcome to the shop! Choose an item to buy:", view=view)

    def check(interaction):
        return interaction.user == ctx.author and interaction.message == ctx.message

    interaction = await bot.wait_for("interaction", check=check)

    if interaction.custom_id == "❓ a mystery ❓":
        role = discord.utils.get(ctx.guild.roles, name="Shop Searcher")
        if not role:
            role = await ctx.guild.create_role(name="Shop Searcher")
        await interaction.user.add_roles(role)
        await interaction.response.send_message("You have received the 'Shop Searcher' role!")

# Leaderboard command
@bot.command()
async def leaderboard(ctx):
    """Show the leaderboard based on balance."""
    sorted_users = sorted(user_data.items(), key=lambda x: x[1].get("balance", 0), reverse=True)
    leaderboard_message = "Leaderboard:\n"
    for idx, (user_id, data) in enumerate(sorted_users[:10]):
        user = await bot.fetch_user(user_id)
        balance = data.get("balance", 0)
        leaderboard_message += f"{idx + 1}. {user.name} - {balance} coins\n"

    await ctx.send(leaderboard_message)

# Profile command
@bot.command()
async def profile(ctx):
    """Show the user's profile with balance info."""
    user_id = str(ctx.author.id)
    balance = user_data.get(user_id, {}).get("balance", 0)
    await ctx.send(f"Profile for {ctx.author.name}:\nBalance: {balance} coins")

# Sync commands to Discord on ready event
@bot.event
async def on_ready():
    # Sync commands to Discord
    await bot.tree.sync()  # This will sync all commands with Discord
    print(f"Logged in as {bot.user}")

# Run the bot
bot.run(DISCORD_TOKEN)
