import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import random
import json
import os

# Intents Setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Load/Save Database
DB_FILE = "db.json"
def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"economy": {}, "inventory": {}, "leaderboard": {}, "current_number": 1, "banned_words": []}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

# Initialize the bot
bot = commands.Bot(command_prefix="!", intents=intents, application_id=os.environ["APPLICATION_ID"])
db = load_db()

# Database helpers
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

# Embeds
def create_embed(title, description, color=discord.Color.blurple()):
    return discord.Embed(title=title, description=description, color=color)

# Trivia Command
trivia_questions = [
    {"question": "What is the capital of France?", "choices": {"A": "Paris", "B": "London", "C": "Rome"}, "correct": "A"},
    {"question": "Who wrote 'Romeo and Juliet'?", "choices": {"A": "Shakespeare", "B": "Dickens", "C": "Austen"}, "correct": "A"},
    [
    {
        "question": "What is the capital of France?",
        "choices": {
            "A": "Paris",
            "B": "London",
            "C": "Rome"
        },
        "correct": "A"
    },
    {
        "question": "Who wrote 'Romeo and Juliet'?",
        "choices": {
            "A": "Shakespeare",
            "B": "Dickens",
            "C": "Hemingway"
        },
        "correct": "A"
    },
    {
        "question": "What is the largest planet in our solar system?",
        "choices": {
            "A": "Earth",
            "B": "Jupiter",
            "C": "Saturn"
        },
        "correct": "B"
    },
    {
        "question": "In which country would you find the Great Barrier Reef?",
        "choices": {
            "A": "Australia",
            "B": "USA",
            "C": "Japan"
        },
        "correct": "A"
    },
    {
        "question": "What is the tallest mountain in the world?",
        "choices": {
            "A": "Mount Everest",
            "B": "Mount Kilimanjaro",
            "C": "Mount Fuji"
        },
        "correct": "A"
    },
    {
        "question": "What is the smallest country in the world?",
        "choices": {
            "A": "Monaco",
            "B": "Vatican City",
            "C": "San Marino"
        },
        "correct": "B"
    },
    {
        "question": "What is the longest river in the world?",
        "choices": {
            "A": "Amazon",
            "B": "Nile",
            "C": "Yangtze"
        },
        "correct": "B"
    },
    {
        "question": "Which element has the chemical symbol 'O'?",
        "choices": {
            "A": "Oxygen",
            "B": "Osmium",
            "C": "Ozone"
        },
        "correct": "A"
    },
    {
        "question": "What is the speed of light?",
        "choices": {
            "A": "300,000 km/s",
            "B": "150,000 km/s",
            "C": "500,000 km/s"
        },
        "correct": "A"
    },
    {
        "question": "Which planet is known as the Red Planet?",
        "choices": {
            "A": "Mars",
            "B": "Venus",
            "C": "Mercury"
        },
        "correct": "A"
    },
    {
        "question": "What is the capital of Japan?",
        "choices": {
            "A": "Beijing",
            "B": "Seoul",
            "C": "Tokyo"
        },
        "correct": "C"
    },
    {
        "question": "Which animal is known as the king of the jungle?",
        "choices": {
            "A": "Lion",
            "B": "Elephant",
            "C": "Tiger"
        },
        "correct": "A"
    },
    {
        "question": "How many continents are there?",
        "choices": {
            "A": "5",
            "B": "7",
            "C": "6"
        },
        "correct": "B"
    },
    {
        "question": "Which country is known as the Land of the Rising Sun?",
        "choices": {
            "A": "China",
            "B": "Japan",
            "C": "South Korea"
        },
        "correct": "B"
    },
    {
        "question": "Who painted the Mona Lisa?",
        "choices": {
            "A": "Picasso",
            "B": "Van Gogh",
            "C": "Da Vinci"
        },
        "correct": "C"
    },
    {
        "question": "What is the chemical symbol for water?",
        "choices": {
            "A": "H2O",
            "B": "H2O2",
            "C": "CO2"
        },
        "correct": "A"
    },
    {
        "question": "What is the largest animal on Earth?",
        "choices": {
            "A": "Elephant",
            "B": "Blue whale",
            "C": "Giraffe"
        },
        "correct": "B"
    },
    {
        "question": "Which country invented pizza?",
        "choices": {
            "A": "USA",
            "B": "Italy",
            "C": "France"
        },
        "correct": "B"
    },
    {
        "question": "What is the hardest natural substance on Earth?",
        "choices": {
            "A": "Gold",
            "B": "Diamond",
            "C": "Iron"
        },
        "correct": "B"
    },
    {
        "question": "Which element has the chemical symbol 'Na'?",
        "choices": {
            "A": "Neon",
            "B": "Sodium",
            "C": "Nickel"
        },
        "correct": "B"
    },
    {
        "question": "In which year did World War I begin?",
        "choices": {
            "A": "1912",
            "B": "1914",
            "C": "1916"
        },
        "correct": "B"
    },
    {
        "question": "Which planet is the closest to the sun?",
        "choices": {
            "A": "Mercury",
            "B": "Venus",
            "C": "Earth"
        },
        "correct": "A"
    },
    {
        "question": "Who discovered penicillin?",
        "choices": {
            "A": "Marie Curie",
            "B": "Alexander Fleming",
            "C": "Isaac Newton"
        },
        "correct": "B"
    },
    {
        "question": "What is the capital of Canada?",
        "choices": {
            "A": "Toronto",
            "B": "Ottawa",
            "C": "Vancouver"
        },
        "correct": "B"
    },
    {
        "question": "What is the national sport of Japan?",
        "choices": {
            "A": "Sumo",
            "B": "Baseball",
            "C": "Soccer"
        },
        "correct": "A"
    },
    {
        "question": "Which country is the largest by land area?",
        "choices": {
            "A": "China",
            "B": "USA",
            "C": "Russia"
        },
        "correct": "C"
    },
    {
        "question": "Which artist is famous for his work 'Starry Night'?",
        "choices": {
            "A": "Van Gogh",
            "B": "Monet",
            "C": "Picasso"
        },
        "correct": "A"
    },
    {
        "question": "What is the longest running TV show?",
        "choices": {
            "A": "The Simpsons",
            "B": "Friends",
            "C": "The Office"
        },
        "correct": "A"
    },
    {
        "question": "Which animal is the fastest on land?",
        "choices": {
            "A": "Lion",
            "B": "Cheetah",
            "C": "Elephant"
        },
        "correct": "B"
    },
    {
        "question": "Which language is primarily spoken in Brazil?",
        "choices": {
            "A": "Spanish",
            "B": "Portuguese",
            "C": "French"
        },
        "correct": "B"
    },
    {
        "question": "Which ocean is the largest?",
        "choices": {
            "A": "Atlantic",
            "B": "Indian",
            "C": "Pacific"
        },
        "correct": "C"
    },
    {
        "question": "What is the tallest building in the world?",
        "choices": {
            "A": "Burj Khalifa",
            "B": "Empire State Building",
            "C": "Eiffel Tower"
        },
        "correct": "A"
    },
    {
        "question": "Which country is home to the Great Pyramids?",
        "choices": {
            "A": "Mexico",
            "B": "Egypt",
            "C": "Peru"
        },
        "correct": "B"
    },
    {
        "question": "Who was the first man to walk on the moon?",
        "choices": {
            "A": "Buzz Aldrin",
            "B": "Neil Armstrong",
            "C": "Yuri Gagarin"
        },
        "correct": "B"
    },
    {
        "question": "What is the most popular fruit in the world?",
        "choices": {
            "A": "Apple",
            "B": "Banana",
            "C": "Orange"
        },
        "correct": "B"
    }
]
]

class TriviaView(View):
    def __init__(self, correct):
        super().__init__()
        options = ["A", "B", "C"]
        random.shuffle(options)
        for opt in options:
            self.add_item(TriviaButton(opt, opt == correct))

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
    question = random.choice(trivia_questions)
    choices = question["choices"]
    correct = question["correct"]

    embed = create_embed("🧠 Trivia", f"{question['question']}\n\nA) {choices['A']}\nB) {choices['B']}\nC) {choices['C']}")
    await interaction.response.send_message(embed=embed, view=TriviaView(correct))

# Math Command
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

# Shop Command
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

# Inventory Command
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

# Leaderboard Command
@bot.tree.command(name="leaderboard", description="Top number game players")
async def leaderboard(interaction: discord.Interaction):
    lb = db["leaderboard"]
    sorted_lb = sorted(lb.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.gold())
    for i, (uid, score) in enumerate(sorted_lb, 1):
        user = await bot.fetch_user(int(uid))
        embed.add_field(name=f"{i}. {user.name}", value=f"{score} points", inline=False)
    await interaction.response.send_message(embed=embed)

# Counting Game (Message-based)
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

# Sync Commands with Discord
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'We have logged in as {bot.user}')

bot.run(os.environ["DISCORD_TOKEN"])
