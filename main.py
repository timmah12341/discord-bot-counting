import discord
from discord.ext import commands
from discord import app_commands
import random
import json

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Load database
try:
    with open('database.json', 'r') as f:
        db = json.load(f)
except FileNotFoundError:
    db = {"current_number": 1, "leaderboard": {}, "economy": {}, "banned_words": [], "inventory": {}}

def save_db():
    with open('database.json', 'w') as f:
        json.dump(db, f, indent=4)

# Load trivia
with open('trivia.json', 'r') as f:
    trivia_questions = json.load(f)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# /balance
@bot.tree.command(name="balance")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    balance = db["economy"].get(user_id, 0)
    await interaction.response.send_message(f"You have {balance} coins.")

# /buy
@bot.tree.command(name="buy")
@app_commands.describe(item="The item you want to buy")
async def buy(interaction: discord.Interaction, item: str):
    user_id = str(interaction.user.id)
    shop_items = {
        "cool_role": 200,
        "epic_title": 500
    }

    item = item.lower()

    if item not in shop_items:
        await interaction.response.send_message("That item doesn't exist.", ephemeral=True)
        return

    price = shop_items[item]
    balance = db["economy"].get(user_id, 0)

    if balance >= price:
        db["economy"][user_id] -= price
        db["inventory"].setdefault(user_id, [])
        db["inventory"][user_id].append(item)
        save_db()
        await interaction.response.send_message(f"You bought **{item}** for {price} coins!")
    else:
        await interaction.response.send_message(f"Not enough coins! You need {price - balance} more.", ephemeral=True)

# /inventory
@bot.tree.command(name="inventory")
async def inventory(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    items = db["inventory"].get(user_id, [])

    if not items:
        await interaction.response.send_message("You don't have any items yet.")
        return

    item_list = "\n".join(f"- {item}" for item in items)
    embed = discord.Embed(title=f"{interaction.user.name}'s Inventory", description=item_list, color=discord.Color.orange())
    await interaction.response.send_message(embed=embed)

# /use
@bot.tree.command(name="use")
@app_commands.describe(item="The item you want to use")
async def use(interaction: discord.Interaction, item: str):
    user_id = str(interaction.user.id)
    items = db["inventory"].get(user_id, [])

    if item.lower() not in items:
        await interaction.response.send_message("You don't have that item.", ephemeral=True)
        return

    # Example effect
    await interaction.response.send_message(f"You used **{item}**! It sparkled!")

    # Remove item after use
    items.remove(item.lower())
    db["inventory"][user_id] = items
    save_db()

# /trivia
@bot.tree.command(name="trivia")
async def trivia(interaction: discord.Interaction):
    question = random.choice(trivia_questions)

    class TriviaButton(discord.ui.Button):
        def __init__(self, label, is_correct):
            super().__init__(label=label, style=discord.ButtonStyle.primary)
            self.is_correct = is_correct
            self.answered = False

        async def callback(self, button_interaction: discord.Interaction):
            if self.view.answered:
                await button_interaction.response.send_message("Trivia already answered.", ephemeral=True)
                return

            self.view.answered = True

            for child in self.view.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True
                    if child.is_correct:
                        child.style = discord.ButtonStyle.success
                    else:
                        child.style = discord.ButtonStyle.secondary

            if self.is_correct:
                user_id = str(interaction.user.id)
                db["economy"][user_id] = db["economy"].get(user_id, 0) + 50
                save_db()
                await button_interaction.response.edit_message(content="Correct! +50 coins!", view=self.view)
            else:
                await button_interaction.response.edit_message(content="Wrong!", view=self.view)

    view = discord.ui.View()
    for key, choice in question["choices"].items():
        is_correct = (key == question["correct"])
        view.add_item(TriviaButton(label=choice, is_correct=is_correct))
    view.answered = False

    await interaction.response.send_message(f"**Trivia:** {question['question']}", view=view)

bot.run('YOUR_BOT_TOKEN')
