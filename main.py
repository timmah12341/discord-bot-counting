import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import os

# Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Load database
try:
    with open('db.json', 'r') as f:
        db = json.load(f)
except FileNotFoundError:
    db = {
        "current_number": 1,
        "last_user_id": None,
        "users": {},
        "inventory": {},
        "coins": {},
        "counted_numbers": {},
    }

# Daily save
@tasks.loop(minutes=5)
async def save_database():
    with open('db.json', 'w') as f:
        json.dump(db, f)

# Discord token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if DISCORD_TOKEN is None:
    raise ValueError("DISCORD_TOKEN is not set.")

# --- EVENTS ---

@bot.event
async def on_ready():
    await tree.sync()
    save_database.start()
    print(f"Logged in as {bot.user}!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    try:
        number = int(message.content)
    except ValueError:
        return

    last_number = db.get("current_number", 1)
    last_user_id = db.get("last_user_id")

    # Check if user is posting in order
    if number == last_number and message.author.id != last_user_id:
        # Correct number
        db["current_number"] += 1
        db["last_user_id"] = message.author.id
        
        user_id = str(message.author.id)
        db["counted_numbers"][user_id] = db["counted_numbers"].get(user_id, 0) + 1
        
        with open('db.json', 'w') as f:
            json.dump(db, f)
        
        await message.channel.send(f"✅ {message.author.mention} counted **{number}** correctly!")
    else:
        # Wrong number -> reset
        db["current_number"] = 1
        db["last_user_id"] = None
        await message.channel.send(f"❌ Wrong number, counting reset to **1**! Start again!")

# --- COMMANDS ---

# /balance
@tree.command(name="balance", description="Check your coin balance.")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    coins = db["coins"].get(user_id, 0)
    embed = discord.Embed(
        title=f"{interaction.user.name}'s Balance",
        description=f"You have **{coins}** coins 💰",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed)

# /shop
@tree.command(name="shop", description="View the shop items.")
async def shop(interaction: discord.Interaction):
    items = {
        "Cookie 🍪": 50,
        "Sword ⚔️": 200,
        "Shield 🛡️": 150,
        "Potion 🧪": 100,
        "Crown 👑": 500
    }
    options = [
        discord.SelectOption(label=item, description=f"{price} coins", value=item)
        for item, price in items.items()
    ]

    select = discord.ui.Select(placeholder="Choose an item to buy!", options=options)
    
    async def select_callback(interaction2: discord.Interaction):
        item = select.values[0]
        await buy_item(interaction2, item)
    
    select.callback = select_callback

    view = discord.ui.View()
    view.add_item(select)

    embed = discord.Embed(
        title="Shop 🛒",
        description="Pick an item to purchase!",
        color=discord.Color.blue()
    )

    await interaction.response.send_message(embed=embed, view=view)

# /inventory
@tree.command(name="inventory", description="View your inventory.")
async def inventory(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    inv = db["inventory"].get(user_id, [])
    
    embed = discord.Embed(
        title=f"{interaction.user.name}'s Inventory 📦",
        color=discord.Color.green()
    )
    
    if not inv:
        embed.description = "You have no items yet!"
    else:
        for item in inv:
            embed.add_field(name=item, value="Owned", inline=True)
    
    await interaction.response.send_message(embed=embed)

# /profile
@tree.command(name="profile", description="View your profile.")
async def profile(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    coins = db["coins"].get(user_id, 0)
    count = db["counted_numbers"].get(user_id, 0)
    inventory = db["inventory"].get(user_id, [])

    embed = discord.Embed(
        title=f"{interaction.user.name}'s Profile 🧑",
        color=discord.Color.purple()
    )
    embed.set_thumbnail(url=interaction.user.avatar.url)
    embed.add_field(name="Coins 💰", value=str(coins), inline=True)
    embed.add_field(name="Numbers Counted 🔢", value=str(count), inline=True)
    embed.add_field(name="Inventory 📦", value=", ".join(inventory) if inventory else "Empty", inline=False)

    await interaction.response.send_message(embed=embed)

# /leaderboard
@tree.command(name="leaderboard", description="See the counting leaderboard.")
async def leaderboard(interaction: discord.Interaction):
    sorted_counts = sorted(db["counted_numbers"].items(), key=lambda x: x[1], reverse=True)
    embed = discord.Embed(
        title="Counting Leaderboard 🏆",
        color=discord.Color.orange()
    )
    for idx, (user_id, count) in enumerate(sorted_counts[:10], 1):
        user = await bot.fetch_user(int(user_id))
        embed.add_field(name=f"#{idx}: {user.name}", value=f"{count} numbers counted!", inline=False)

    await interaction.response.send_message(embed=embed)

# /trivia
@tree.command(name="trivia", description="Play a trivia question!")
async def trivia(interaction: discord.Interaction):
    try:
        with open('trivia.json', 'r') as f:
            trivia_data = json.load(f)
    except FileNotFoundError:
        await interaction.response.send_message("Trivia data not found.", ephemeral=True)
        return

    question_data = random.choice(trivia_data['questions'])
    question = question_data['question']
    choices = question_data['choices']
    correct_answer = question_data['correct_answer']

    options = [discord.SelectOption(label=choice, value=choice) for choice in choices]
    select = discord.ui.Select(placeholder="Choose your answer!", options=options)

    async def select_callback(interaction2: discord.Interaction):
        selected = select.values[0]
        if selected == correct_answer:
            await interaction2.response.send_message("🎉 Correct Answer!", ephemeral=True)
        else:
            await interaction2.response.send_message(f"❌ Wrong! Correct was **{correct_answer}**", ephemeral=True)

    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)

    embed = discord.Embed(
        title="Trivia Time ❓",
        description=question,
        color=discord.Color.teal()
    )

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# --- BUY ITEM HELPER FUNCTION ---

async def buy_item(interaction, item_name):
    user_id = str(interaction.user.id)
    items_prices = {
        "Cookie 🍪": 50,
        "Sword ⚔️": 200,
        "Shield 🛡️": 150,
        "Potion 🧪": 100,
        "Crown 👑": 500
    }

    price = items_prices.get(item_name)
    if price is None:
        await interaction.response.send_message("Invalid item.", ephemeral=True)
        return

    user_coins = db["coins"].get(user_id, 0)

    if user_coins >= price:
        db["coins"][user_id] = user_coins - price
        db["inventory"].setdefault(user_id, []).append(item_name)

        with open('db.json', 'w') as f:
            json.dump(db, f)

        await interaction.response.send_message(f"You bought {item_name}! 🎉", ephemeral=True)
    else:
        await interaction.response.send_message("Not enough coins! 😢", ephemeral=True)

# --- RUN ---
bot.run(DISCORD_TOKEN)
