import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import random
import json
import os

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

# Load/save DB
DB_FILE = "db.json"
TRIVIA_FILE = "trivia_questions.json"

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"economy": {}, "inventory": {}, "leaderboard": {}, "current_number": 1, "stats": {}, "banned_words": []}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

# Load trivia questions
def load_trivia_questions():
    if not os.path.exists(TRIVIA_FILE):
        raise FileNotFoundError(f"{TRIVIA_FILE} is missing. Please add a trivia questions file.")
    with open(TRIVIA_FILE, "r") as f:
        return json.load(f)

# Init
bot = commands.Bot(command_prefix="!", intents=intents, application_id=os.environ.get("APPLICATION_ID"))
db = load_db()
trivia_questions = load_trivia_questions()

# --- Economy helpers ---
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
    def __init__(self, question_data):
        super().__init__()
        self.correct = question_data['correct']
        options = list(question_data['choices'].items())
        random.shuffle(options)  # Shuffle answer choices
        
        for opt in options:
            label, _ = opt
            self.add_item(TriviaButton(label, label == self.correct))

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
    # Pick a random question from the trivia questions list
    question_data = random.choice(trivia_questions)
    question = question_data['question']
    choices = question_data['choices']

    embed = create_embed("🧠 Trivia", f"{question}\n\nA) {choices['A']}\nB) {choices['B']}\nC) {choices['C']}")
    await interaction.response.send_message(embed=embed, view=TriviaView(question_data))

# --- Shop System ---
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
        await interaction.response.send_message(embed=create_embed("❌ Too Broke", f"You need {cost} coins to buy a {item}."))
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

        if number == current:
            if number % 2 == 1:
                db["leaderboard"][uid] = db["leaderboard"].get(uid, 0) + 1
                db["current_number"] += 1
                await message.channel.send(embed=create_embed("✅ Good Job", f"Next number is: {db['current_number']}"))
                db["current_number"] += 1
                save_db()
            else:
                db["current_number"] = 1
                save_db()
                await message.channel.send(embed=create_embed("❌ Wrong!", "Even numbers are bot's job! Game reset."))
        else:
            await message.channel.send(embed=create_embed("❌ Wrong Number", f"Expected: {current}"))
    await bot.process_commands(message)

bot.run(os.environ["DISCORD_TOKEN"])
