import discord
from discord.ext import commands
import os
import json
import random
from discord import app_commands

# --- Load the token from environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    raise SystemExit("[ERROR] DISCORD_TOKEN environment variable is missing. Exiting...")

# --- Bot setup
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# --- Load your database
try:
    with open('db.json', 'r') as f:
        db = json.load(f)
except FileNotFoundError:
    db = {}

# --- Helper functions
def save_db():
    with open('db.json', 'w') as f:
        json.dump(db, f, indent=4)

def get_user_data(user_id):
    if str(user_id) not in db:
        db[str(user_id)] = {"coins": 0, "inventory": []}
        save_db()
    return db[str(user_id)]

# --- Trivia questions
try:
    with open('trivia.json', 'r') as f:
        trivia_questions = json.load(f)
except FileNotFoundError:
    trivia_questions = []

# --- Shop items
shop_items = {
    "cookie": 50,
    "sword": 200,
    "shield": 150
}

# --- Bot events
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# --- Commands
@tree.command(name="balance", description="Check your coins!")
async def balance(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    await interaction.response.send_message(f"You have {user_data['coins']} coins!", ephemeral=True)

@tree.command(name="inventory", description="Check your inventory!")
async def inventory(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    inventory_list = user_data["inventory"]
    if inventory_list:
        await interaction.response.send_message(f"Your inventory: {', '.join(inventory_list)}", ephemeral=True)
    else:
        await interaction.response.send_message("Your inventory is empty.", ephemeral=True)

@tree.command(name="shop", description="See available items!")
async def shop(interaction: discord.Interaction):
    items = "\n".join([f"{item}: {price} coins" for item, price in shop_items.items()])
    await interaction.response.send_message(f"Available items:\n{items}", ephemeral=True)

@tree.command(name="buy", description="Buy an item from the shop!")
@app_commands.describe(item="Item name")
async def buy(interaction: discord.Interaction, item: str):
    user_data = get_user_data(interaction.user.id)
    item = item.lower()
    if item not in shop_items:
        await interaction.response.send_message("Item not found.", ephemeral=True)
        return
    price = shop_items[item]
    if user_data["coins"] >= price:
        user_data["coins"] -= price
        user_data["inventory"].append(item)
        save_db()
        await interaction.response.send_message(f"You bought a {item}!", ephemeral=True)
    else:
        await interaction.response.send_message("You don't have enough coins.", ephemeral=True)

@tree.command(name="use", description="Use an item from your inventory!")
@app_commands.describe(item="Item name")
async def use(interaction: discord.Interaction, item: str):
    user_data = get_user_data(interaction.user.id)
    item = item.lower()
    if item in user_data["inventory"]:
        user_data["inventory"].remove(item)
        save_db()
        await interaction.response.send_message(f"You used a {item}!", ephemeral=True)
    else:
        await interaction.response.send_message("You don't have that item.", ephemeral=True)

@tree.command(name="trivia", description="Answer a trivia question!")
async def trivia(interaction: discord.Interaction):
    if not trivia_questions:
        await interaction.response.send_message("No trivia questions loaded.", ephemeral=True)
        return

    question_data = random.choice(trivia_questions)
    question = question_data["question"]
    choices = question_data["choices"]
    correct_answer = question_data["correct"]

    view = discord.ui.View()

    for letter, choice_text in choices.items():
        if letter == correct_answer:
            button = discord.ui.Button(label=f"{letter}: {choice_text}", style=discord.ButtonStyle.success)
        else:
            button = discord.ui.Button(label=f"{letter}: {choice_text}", style=discord.ButtonStyle.danger)

        async def callback(inter, letter=letter):
            user_data = get_user_data(inter.user.id)
            if hasattr(view, 'answered') and view.answered:
                await inter.response.send_message("Trivia already answered!", ephemeral=True)
                return

            if letter == correct_answer:
                await inter.response.edit_message(content=f"✅ Correct! You earned 10 coins.", view=None)
                user_data["coins"] += 10
            else:
                await inter.response.edit_message(content=f"❌ Wrong! The correct answer was {correct_answer}.", view=None)
            view.answered = True
            save_db()

        button.callback = callback
        view.add_item(button)

    view.answered = False
    await interaction.response.send_message(question, view=view, ephemeral=True)

# --- Run bot
bot.run(DISCORD_TOKEN)
