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
    db = {"current_number": 1, "leaderboard": {}, "economy": {}, "banned_words": [], "inventory": {}, "boosts": {}}

def save_db():
    with open('db.json', 'w') as f:
        json.dump(db, f, indent=4)

# Load trivia questions
try:
    with open('trivia.json', 'r') as f:
        trivia_questions = json.load(f)
except FileNotFoundError:
    trivia_questions = []

# Define shop items
shop_items = {
    "Double Coins": 50,
    "Lucky Charm": 30,
    "Mystery Box": 100
}

class TriviaButton(discord.ui.View):
    def __init__(self, correct_choice, user_id):
        super().__init__(timeout=30)
        self.correct_choice = correct_choice
        self.user_id = user_id
        self.answered = False

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

        user_id = str(interaction.user.id)
        base_reward = 10

        if choice == self.correct_choice:
            reward = base_reward

            # Check for Double Coins boost
            if db.get("boosts", {}).get(user_id) == "Double Coins":
                reward *= 2
                db["boosts"].pop(user_id, None)  # Remove boost after use

            db["economy"][user_id] = db["economy"].get(user_id, 0) + reward
            save_db()
            await interaction.response.send_message(f"Correct! You earned {reward} coins.", ephemeral=True)
        else:
            await interaction.response.send_message("Wrong!", ephemeral=True)

        # Disable all buttons
        for item in self.children:
            item.disabled = True
            if item.label == self.correct_choice:
                item.style = discord.ButtonStyle.success
            elif item.label == choice:
                item.style = discord.ButtonStyle.danger

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

    view = TriviaButton(correct_choice=question["correct"], user_id=interaction.user.id)
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
        await interaction.response.send_message("You don't have that item!", ephemeral=True)
        return

    if item_name == "Double Coins":
        db.setdefault("boosts", {})[user_id] = "Double Coins"
        await interaction.response.send_message("You activated **Double Coins**! Your next trivia reward will be doubled.")
    elif item_name == "Lucky Charm":
        await interaction.response.send_message("You used **Lucky Charm**! (effect not implemented yet)")
    elif item_name == "Mystery Box":
        prize = random.choice(["10 Coins", "50 Coins", "Nothing"])
        if prize == "10 Coins":
            db["economy"][user_id] = db["economy"].get(user_id, 0) + 10
            await interaction.response.send_message("You opened a Mystery Box and won **10 coins**!")
        elif prize == "50 Coins":
            db["economy"][user_id] = db["economy"].get(user_id, 0) + 50
            await interaction.response.send_message("You opened a Mystery Box and won **50 coins**!")
        else:
            await interaction.response.send_message("You opened a Mystery Box... and got **nothing**!")
    else:
        await interaction.response.send_message(f"You used **{item_name}**!")

    inventory.remove(item_name)
    db["inventory"][user_id] = inventory
    save_db()

@bot.tree.command(name="shop", description="View the shop items!")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="Shop", description="Buy items to help you!", color=discord.Color.gold())
    for item, price in shop_items.items():
        embed.add_field(name=item, value=f"{price} coins", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buy", description="Buy an item from the shop!")
@app_commands.describe(item_name="The name of the item you want to buy")
async def buy(interaction: discord.Interaction, item_name: str):
    user_id = str(interaction.user.id)
    item_name_capitalized = item_name.title()

    if item_name_capitalized not in shop_items:
        await interaction.response.send_message("Item not found in the shop!", ephemeral=True)
        return

    price = shop_items[item_name_capitalized]
    balance = db["economy"].get(user_id, 0)

    if balance < price:
        await interaction.response.send_message(f"You don't have enough coins! {price} coins needed.", ephemeral=True)
        return

    db["economy"][user_id] -= price
    db.setdefault("inventory", {}).setdefault(user_id, []).append(item_name_capitalized)
    save_db()
    await interaction.response.send_message(f"You bought **{item_name_capitalized}** for {price} coins!")

# Run bot with token variable
bot.run(DISCORD_TOKEN)
