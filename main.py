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

# Trivia Questions
trivia_questions = [
    {"question": "What is the capital of France?", "choices": {"A": "Paris", "B": "London", "C": "Rome"}, "correct": "A"},
    {"question": "Who wrote 'Romeo and Juliet'?", "choices": {"A": "Shakespeare", "B": "Dickens", "C": "Hemingway"}, "correct": "A"},
    {"question": "What is the largest planet in our solar system?", "choices": {"A": "Earth", "B": "Jupiter", "C": "Saturn"}, "correct": "B"},
    {"question": "In which country would you find the Great Barrier Reef?", "choices": {"A": "Australia", "B": "USA", "C": "Japan"}, "correct": "A"},
    {"question": "What is the tallest mountain in the world?", "choices": {"A": "Mount Everest", "B": "Mount Kilimanjaro", "C": "Mount Fuji"}, "correct": "A"},
    {"question": "What is the smallest country in the world?", "choices": {"A": "Monaco", "B": "Vatican City", "C": "San Marino"}, "correct": "B"},
    {"question": "What is the longest river in the world?", "choices": {"A": "Amazon", "B": "Nile", "C": "Yangtze"}, "correct": "B"},
    {"question": "Which element has the chemical symbol 'O'?", "choices": {"A": "Oxygen", "B": "Osmium", "C": "Ozone"}, "correct": "A"},
    {"question": "What is the speed of light?", "choices": {"A": "300,000 km/s", "B": "150,000 km/s", "C": "500,000 km/s"}, "correct": "A"},
    {"question": "Which planet is known as the Red Planet?", "choices": {"A": "Mars", "B": "Venus", "C": "Mercury"}, "correct": "A"},
    {"question": "What is the capital of Japan?", "choices": {"A": "Beijing", "B": "Seoul", "C": "Tokyo"}, "correct": "C"},
    {"question": "Which animal is known as the king of the jungle?", "choices": {"A": "Lion", "B": "Elephant", "C": "Tiger"}, "correct": "A"},
    {"question": "How many continents are there?", "choices": {"A": "5", "B": "7", "C": "6"}, "correct": "B"},
    {"question": "Which country is known as the Land of the Rising Sun?", "choices": {"A": "China", "B": "Japan", "C": "South Korea"}, "correct": "B"},
    {"question": "Who painted the Mona Lisa?", "choices": {"A": "Picasso", "B": "Van Gogh", "C": "Da Vinci"}, "correct": "C"},
    {"question": "What is the chemical symbol for water?", "choices": {"A": "H2O", "B": "H2O2", "C": "CO2"}, "correct": "A"},
    {"question": "What is the largest animal on Earth?", "choices": {"A": "Elephant", "B": "Blue whale", "C": "Giraffe"}, "correct": "B"},
    {"question": "Which country invented pizza?", "choices": {"A": "USA", "B": "Italy", "C": "France"}, "correct": "B"},
    {"question": "What is the hardest natural substance on Earth?", "choices": {"A": "Gold", "B": "Diamond", "C": "Iron"}, "correct": "B"},
    {"question": "Which element has the chemical symbol 'Na'?", "choices": {"A": "Neon", "B": "Sodium", "C": "Nickel"}, "correct": "B"},
    {"question": "In which year did World War I begin?", "choices": {"A": "1912", "B": "1914", "C": "1916"}, "correct": "B"},
    {"question": "Which planet is the closest to the sun?", "choices": {"A": "Mercury", "B": "Venus", "C": "Earth"}, "correct": "A"},
    {"question": "Who discovered penicillin?", "choices": {"A": "Marie Curie", "B": "Alexander Fleming", "C": "Isaac Newton"}, "correct": "B"},
    {"question": "What is the capital of Canada?", "choices": {"A": "Toronto", "B": "Ottawa", "C": "Vancouver"}, "correct": "B"},
    {"question": "What is the national sport of Japan?", "choices": {"A": "Sumo", "B": "Baseball", "C": "Soccer"}, "correct": "A"},
    {"question": "Which country is the largest by land area?", "choices": {"A": "China", "B": "USA", "C": "Russia"}, "correct": "C"},
    {"question": "Which artist is famous for his work 'Starry Night'?", "choices": {"A": "Van Gogh", "B": "Monet", "C": "Picasso"}, "correct": "A"},
    {"question": "What is the longest running TV show?", "choices": {"A": "The Simpsons", "B": "Friends", "C": "The Office"}, "correct": "A"},
    {"question": "Which animal is the fastest on land?", "choices": {"A": "Lion", "B": "Cheetah", "C": "Elephant"}, "correct": "B"},
    {"question": "Which language is primarily spoken in Brazil?", "choices": {"A": "Spanish", "B": "Portuguese", "C": "French"}, "correct": "B"},
    {"question": "Which ocean is the largest?", "choices": {"A": "Atlantic", "B": "Indian", "C": "Pacific"}, "correct": "C"},
    {"question": "What is the tallest building in the world?", "choices": {"A": "Burj Khalifa", "B": "Empire State Building", "C": "Eiffel Tower"}, "correct": "A"},
    {"question": "Which country is home to the Great Pyramids?", "choices": {"A": "Mexico", "B": "Egypt", "C": "Peru"}, "correct": "B"},
    {"question": "Who was the first man to walk on the moon?", "choices": {"A": "Buzz Aldrin", "B": "Neil Armstrong", "C": "Yuri Gagarin"}, "correct": "B"},
    {"question": "What is the most popular fruit in the world?", "choices": {"A": "Apple", "B": "Banana", "C": "Orange"}, "correct": "B"}
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

# Math Command, Shop Command, and other existing commands would follow here...

# Sync Commands with Discord
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'We have logged in as {bot.user}')

bot.run(os.environ["DISCORD_TOKEN"])
