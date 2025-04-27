import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load database
try:
    with open('db.json', 'r') as f:
        db = json.load(f)
except FileNotFoundError:
    db = {"current_number": 1, "leaderboard": {}, "economy": {}, "banned_words": [], "inventory": {}}

def save_db():
    with open('db.json', 'w') as f:
        json.dump(db, f, indent=4)

# Load trivia questions
try:
    with open('trivia.json', 'r') as f:
        trivia_questions = json.load(f)
except FileNotFoundError:
    trivia_questions = []

class TriviaButton(discord.ui.View):
    def __init__(self, correct_choice, user_id, reward_amount):
        super().__init__(timeout=30)
        self.correct_choice = correct_choice
        self.user_id = user_id
        self.answered = False
        self.reward_amount = reward_amount

    @discord.ui.button(label="A", style=discord.ButtonStyle.secondary)
    async def button_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, "A")

    @discord.ui.button(label="B", style=discord.ButtonStyle.secondary)
    async def button_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, "B")

    @discord.ui.button(label="C", style=discord.ButtonStyle.secondary)
    async def button_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, "C")

    async def handle_answer(self, interaction, choice):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your trivia question!", ephemeral=True)
            return

        if self.answered:
            await interaction.response.send_message("You've already answered!", ephemeral=True)
            return

        self.answered = True

        if choice == self.correct_choice:
            await interaction.response.send_message(f"Correct! You earned {self.reward_amount} coins!", ephemeral=True)

            user_id = str(interaction.user.id)
            db["economy"][user_id] = db["economy"].get(user_id, 0) + self.reward_amount
            save_db()
        else:
            await interaction.response.send_message("Wrong!", ephemeral=True)

        # Disable all buttons
        for item in self.children:
            item.disabled = True
            if item.label == self.correct_choice:
                item.style = discord.ButtonStyle.success  # Highlight correct answer
            elif item.label == choice:
                item.style = discord.ButtonStyle.danger  # Highlight wrong answer

        await interaction.message.edit(view=self)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(e)

@bot.tree.command(name="trivia", description="Play a trivia question!")
async def trivia(interaction: discord.Interaction):
    question = random.choice(trivia_questions)
    embed = discord.Embed(title="Trivia Time!", description=question["question"], color=discord.Color.blue())

    choices = ""
    for letter, answer in question["choices"].items():
        choices += f"**{letter}**: {answer}\n"
    embed.add_field(name="Choices", value=choices, inline=False)

    view = TriviaButton(correct_choice=question["correct"], user_id=interaction.user.id, reward_amount=10)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="balance", description="Check your coin balance!")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    balance = db["economy"].get(user_id, 0)
    await interaction.response.send_message(f"You have {balance} coins.")

@bot.tree.command(name="inventory", description="Check your inventory!")
async def inventory(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    inventory = db["inventory"].get(user_id, [])
    if not inventory:
        await interaction.response.send_message("Your inventory is empty.")
    else:
        items = "\n".join(f"- {item}" for item in inventory)
        await interaction.response.send_message(f"Your items:\n{items}")

@bot.tree.command(name="use", description="Use an item from your inventory!")
@app_commands.describe(item_name="The name of the item you want to use")
async def use(interaction: discord.Interaction, item_name: str):
    user_id = str(interaction.user.id)
    inventory = db["inventory"].get(user_id, [])
    if item_name not in inventory:
        await interaction.response.send_message("You don't have that item!")
        return

    # Example item effect
    if item_name == "Double Coins":
        await interaction.response.send_message("You used **Double Coins**! For your next trivia, you'll earn double!")
        # Here you could set a 'double' flag in db
    else:
        await interaction.response.send_message(f"You used **{item_name}**!")

    inventory.remove(item_name)
    db["inventory"][user_id] = inventory
    save_db()

# Example command to manually add items for testing
@bot.tree.command(name="giveitem", description="Give yourself an item!")
@app_commands.describe(item_name="The name of the item to give")
async def giveitem(interaction: discord.Interaction, item_name: str):
    user_id = str(interaction.user.id)
    inventory = db["inventory"].get(user_id, [])
    inventory.append(item_name)
    db["inventory"][user_id] = inventory
    save_db()
    await interaction.response.send_message(f"Given item {item_name}!")

# Run bot
bot.run("YOUR_TOKEN_HERE")
