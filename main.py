import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import random
import asyncio
import json
import os

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

# Load/save DB
DB_FILE = "db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"economy": {}, "inventory": {}, "leaderboard": {}, "current_number": 1, "stats": {}}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

# Init
bot = commands.Bot(command_prefix="!", intents=intents, application_id=os.environ.get("APPLICATION_ID"))
db = load_db()

# Economy helpers
def get_balance(uid): return db["economy"].get(uid, 0)

def update_balance(uid, amount):
    db["economy"][uid] = get_balance(uid) + amount
    save_db()

def get_inventory(uid): return db["inventory"].get(uid, [])

def add_item(uid, item):
    inv = get_inventory(uid)
    inv.append(item)
    db["inventory"][uid] = inv
    save_db()

# --- Embeds ---
def create_embed(title, description, color=discord.Color.blurple()):
    return discord.Embed(title=title, description=description, color=color)

# --- Trivia ---
class TriviaView(View):
    def __init__(self, correct):
        super().__init__()
        self.correct = correct

        options = ["A", "B", "C"]
        random.shuffle(options)
        for opt in options:
            self.add_item(TriviaButton(opt, opt == self.correct))

class TriviaButton(Button):
    def __init__(self, label, is_correct):
        super().__init__(label=label, style=discord.ButtonStyle.green if is_correct else discord.ButtonStyle.red)
        self.is_correct = is_correct

    async def callback(self, interaction):
        if self.is_correct:
            update_balance(str(interaction.user.id), 50)
            await interaction.response.send_message(embed=create_embed("✅ Correct!", "You earned 50 coins!", discord.Color.green()), ephemeral=True)
        else:
            await interaction.response.send_message(embed=create_embed("❌ Wrong!", "Better luck next time."), ephemeral=True)

@bot.tree.command(name="trivia", description="Answer a trivia question")
async def trivia(interaction: discord.Interaction):
    question = "What is the capital of France?"
    choices = {"A": "Paris", "B": "London", "C": "Rome"}
    correct = "A"

    embed = create_embed("🧠 Trivia", f"{question}\n\nA) {choices['A']}\nB) {choices['B']}\nC) {choices['C']}")
    await interaction.response.send_message(embed=embed, view=TriviaView(correct))

# --- Math ---
class MathView(View):
    def __init__(self, answer):
        super().__init__()
        wrongs = [str(answer + i) for i in range(-2, 3) if i != 0]
        options = [str(answer)] + random.sample(wrongs, 2)
        random.shuffle(options)
        for opt in options:
            self.add_item(MathButton(opt, int(opt) == answer))

class MathButton(Button):
    def __init__(self, label, is_correct):
        super().__init__(label=label, style=discord.ButtonStyle.green if is_correct else discord.ButtonStyle.red)
        self.is_correct = is_correct

    async def callback(self, interaction):
        if self.is_correct:
            update_balance(str(interaction.user.id), 30)
            await interaction.response.send_message(embed=create_embed("✅ Correct!", "You earned 30 coins!", discord.Color.green()), ephemeral=True)
        else:
            await interaction.response.send_message(embed=create_embed("❌ Wrong!", "Better luck next time."), ephemeral=True)

@bot.tree.command(name="math", description="Solve a math problem")
async def math(interaction: discord.Interaction):
    a, b = random.randint(1, 10), random.randint(1, 10)
    question = f"{a} + {b}"
    answer = a + b
    embed = create_embed("➕ Math Time!", f"What is {question}?")
    await interaction.response.send_message(embed=embed, view=MathView(answer))

# --- Shop ---
items = {"cookie": 50, "potion": 100, "badge": 200}

@bot.tree.command(name="shop", description="See items for sale")
async def shop(interaction: discord.Interaction):
    desc = "\n".join([f"**{item}** - {price} coins" for item, price in items.items()])
    embed = create_embed("🛍️ Shop", desc)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buy", description="Buy an item")
@app_commands.describe(item="The item you want to buy")
async def buy(interaction: discord.Interaction, item: str):
    uid = str(interaction.user.id)
    item = item.lower()
    if item not in items:
        await interaction.response.send_message(embed=create_embed("❌ Not Found", "That item doesn't exist."))
        return
    cost = items[item]
    if get_balance(uid) < cost:
        await interaction.response.send_message(embed=create_embed("❌ Too Broke", f"You need {cost} coins to buy a {item}"))
        return
    update_balance(uid, -cost)
    add_item(uid, item)
    await interaction.response.send_message(embed=create_embed("✅ Bought!", f"You purchased a {item} for {cost} coins."))

@bot.tree.command(name="inventory", description="View your items")
async def inventory(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    inv = get_inventory(uid)
    if not inv:
        await interaction.response.send_message(embed=create_embed("📦 Inventory", "You own nothing yet."))
    else:
        counts = {i: inv.count(i) for i in set(inv)}
        desc = "\n".join([f"{item} x{amount}" for item, amount in counts.items()])
        await interaction.response.send_message(embed=create_embed("📦 Inventory", desc))

# --- Leaderboard ---
@bot.tree.command(name="leaderboard", description="Top number game players")
async def leaderboard(interaction: discord.Interaction):
    lb = db["leaderboard"]
    sorted_lb = sorted(lb.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.gold())
    for i, (uid, score) in enumerate(sorted_lb, 1):
        user = await bot.fetch_user(int(uid))
        embed.add_field(name=f"{i}. {user.name}", value=f"{score} points", inline=False)
    await interaction.response.send_message(embed=embed)

# --- Counting Game ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.isdigit():
        number = int(message.content)
        uid = str(message.author.id)
        current = db["current_number"]

        # Get or initialize user stats
        user_stats = db.get("stats", {}).get(uid, {"correct": 0, "incorrect": 0})
        
        if number == current:
            # Correct input
            if number % 2 == 1:  # Odd number for the user
                user_stats["correct"] += 1
                db["leaderboard"][uid] = db["leaderboard"].get(uid, 0) + 1
                db["current_number"] += 1
                await message.channel.send(embed=create_embed("✅ Good Job", f"Next number is: {db['current_number']}"))
            else:
                # Even numbers are bot's job, reset to 1
                db["current_number"] = 1
                await message.channel.send(embed=create_embed("❌ Wrong!", "Even numbers are bot's job! Game reset."))
            
            # Save the stats back to db
            if "stats" not in db:
                db["stats"] = {}
            db["stats"][uid] = user_stats
            save_db()
        else:
            # Incorrect number, reset and track the mistake
            user_stats["incorrect"] += 1
            db["current_number"] = 1  # Reset to 1
            await message.channel.send(embed=create_embed("❌ Wrong Number", f"Expected: {current}. Game reset."))
            
            # Save stats
            if "stats" not in db:
                db["stats"] = {}
            db["stats"][uid] = user_stats
            save_db()
            
    await bot.process_commands(message)

# --- User Stats Command ---
@bot.tree.command(name="userstats", description="View your counting game stats")
async def userstats(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    user_stats = db.get("stats", {}).get(uid, {"correct": 0, "incorrect": 0})
    await interaction.response.send_message(
        embed=create_embed(
            "Your Counting Stats", 
            f"Correct Counts: {user_stats['correct']}\nIncorrect Counts: {user_stats['incorrect']}"
        )
    )

bot.run(os.environ["DISCORD_TOKEN"])
