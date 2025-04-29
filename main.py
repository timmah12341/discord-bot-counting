import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load database
if not os.path.exists('db.json'):
    with open('db.json', 'w') as f:
        json.dump({"current_number": 1, "leaderboard": {}, "economy": {}, "inventory": {}, "shop": []}, f)

with open('db.json', 'r') as f:
    db = json.load(f)

# Save database
def save_db():
    with open('db.json', 'w') as f:
        json.dump(db, f, indent=4)

# Load trivia questions
if not os.path.exists('trivia.json'):
    with open('trivia.json', 'w') as f:
        json.dump([], f)

with open('trivia.json', 'r') as f:
    trivia_questions = json.load(f)

# Predefined items
predefined_items = [
    {"name": "Cookie", "price": 20, "description": "🍪 A tasty cookie."},
    {"name": "Magic Wand", "price": 150, "description": "✨ Cast spells!"},
    {"name": "Golden Apple", "price": 300, "description": "🍏 Grants fortune."},
    {"name": "Sword", "price": 250, "description": "⚔️ Useful for battles."},
    {"name": "Potion", "price": 100, "description": "🧪 Heals you instantly."},
    {"name": "Treasure Map", "price": 500, "description": "🗺️ Leads to riches."},
    {"name": "Fishing Rod", "price": 75, "description": "🎣 Catch something!"},
    {"name": "Mysterious Box", "price": 400, "description": "🎁 What's inside?"},
    {"name": "Toy Robot", "price": 80, "description": "🤖 Fun and mechanical."},
    {"name": "Balloons", "price": 50, "description": "🎈 Party time!"}
]

# Add predefined items if shop is empty
if not db["shop"]:
    db["shop"] = predefined_items
    save_db()

# Special messages when using items
item_use_messages = {
    "Cookie": "*nom nom!* 🍪",
    "Magic Wand": "*You wave the wand... magic sparkles everywhere!* ✨",
    "Golden Apple": "*You feel incredibly lucky!* 🍏",
    "Sword": "*You swing the sword mightily!* ⚔️",
    "Potion": "*You drink the potion and feel refreshed!* 🧪",
    "Treasure Map": "*You unfold the map and start your journey!* 🗺️",
    "Fishing Rod": "*You cast your line into the water.* 🎣",
    "Mysterious Box": "*The box opens with a mysterious glow!* 🎁",
    "Toy Robot": "*The robot whirs to life and dances!* 🤖",
    "Balloons": "*The balloons float up cheerfully!* 🎈"
}

# Counting Command
@bot.tree.command(name="count", description="Send the next number!")
async def count(interaction: discord.Interaction, number: int):
    user_id = str(interaction.user.id)
    expected = db["current_number"]

    if number == expected:
        db["current_number"] += 1
        db["leaderboard"][user_id] = db["leaderboard"].get(user_id, 0) + 1
        save_db()

        embed = discord.Embed(
            title="✅ Correct!",
            description=f"**{interaction.user.mention} counted {number}!** 🎉",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Next number: {db['current_number']}")
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Wrong!",
            description=f"You sent **{number}**, but expected **{expected}**.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

# Trivia Command
@bot.tree.command(name="trivia", description="Play a trivia question!")
async def trivia(interaction: discord.Interaction):
    if not trivia_questions:
        await interaction.response.send_message("⚠️ No trivia questions available.", ephemeral=True)
        return

    question = random.choice(trivia_questions)
    choices = question['choices']

    class TriviaView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=15)
            self.answered = False

        @discord.ui.button(label="A", style=discord.ButtonStyle.secondary, custom_id="A")
        async def a(self, interaction2, button):
            await self.answer(interaction2, "A")

        @discord.ui.button(label="B", style=discord.ButtonStyle.secondary, custom_id="B")
        async def b(self, interaction2, button):
            await self.answer(interaction2, "B")

        @discord.ui.button(label="C", style=discord.ButtonStyle.secondary, custom_id="C")
        async def c(self, interaction2, button):
            await self.answer(interaction2, "C")

        async def answer(self, interaction2, choice):
            if self.answered:
                await interaction2.response.send_message("You already answered!", ephemeral=True)
                return
            self.answered = True

            user_id = str(interaction2.user.id)
            if choice == question['correct']:
                db["economy"][user_id] = db["economy"].get(user_id, 0) + 50
                save_db()

                embed = discord.Embed(
                    title="🎉 Correct!",
                    description=f"Good job, **{interaction2.user.mention}**! You earned **💰 50 coins**.",
                    color=discord.Color.gold()
                )
            else:
                embed = discord.Embed(
                    title="❌ Incorrect!",
                    description=f"Better luck next time, **{interaction2.user.mention}**!",
                    color=discord.Color.red()
                )

            await interaction2.response.edit_message(embed=embed, view=None)

    embed = discord.Embed(
        title="🧠 Trivia Time!",
        description=f"**{question['question']}**",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Select the correct answer!")

    await interaction.response.send_message(embed=embed, view=TriviaView())

# View Profile Command
@bot.tree.command(name="viewprofile", description="See your profile info!")
async def viewprofile(interaction: discord.Interaction):
    user = interaction.user
    user_id = str(user.id)

    coins = db["economy"].get(user_id, 0)

    embed = discord.Embed(
        title=f"👤 {user.name}'s Profile",
        description=f"💰 Coins: {coins}\n📦 Items: {len(db['inventory'].get(user_id, []))}",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

# Shop Command
@bot.tree.command(name="shop", description="See what's for sale!")
async def shop(interaction: discord.Interaction):
    if not db["shop"]:
        await interaction.response.send_message("🛒 The shop is empty!", ephemeral=True)
        return

    embed = discord.Embed(
        title="🛍️ Shop",
        description="Here are the items for sale:",
        color=discord.Color.green()
    )
    for item in db["shop"]:
        embed.add_field(name=f"{item['name']} - {item['price']} coins", value=item['description'], inline=False)

    await interaction.response.send_message(embed=embed)

# Buy Command
@bot.tree.command(name="buy", description="Buy an item from the shop!")
@app_commands.describe(item_name="The item you want to buy.")
async def buy(interaction: discord.Interaction, item_name: str):
    user_id = str(interaction.user.id)

    item = next((i for i in db["shop"] if i["name"].lower() == item_name.lower()), None)
    if not item:
        await interaction.response.send_message("❌ Item not found!", ephemeral=True)
        return

    balance = db["economy"].get(user_id, 0)
    if balance < item["price"]:
        await interaction.response.send_message("❌ Not enough coins!", ephemeral=True)
        return

    db["economy"][user_id] -= item["price"]
    db["inventory"].setdefault(user_id, []).append(item["name"])
    save_db()

    embed = discord.Embed(
        title="✅ Purchase Successful!",
        description=f"You bought **{item['name']}** for **{item['price']} coins**!",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# Inventory Command
@bot.tree.command(name="inventory", description="View your inventory!")
async def inventory(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    items = db["inventory"].get(user_id, [])

    embed = discord.Embed(
        title=f"🎒 {interaction.user.name}'s Inventory",
        description="\n".join(f"• {item}" for item in items) if items else "No items yet!",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed)

# Use Command
@bot.tree.command(name="use", description="Use an item from your inventory!")
@app_commands.describe(item_name="The item you want to use.")
async def use(interaction: discord.Interaction, item_name: str):
    user_id = str(interaction.user.id)
    items = db["inventory"].get(user_id, [])

    if item_name not in items:
        await interaction.response.send_message("❌ You don't have that item!", ephemeral=True)
        return

    items.remove(item_name)
    db["inventory"][user_id] = items
    save_db()

    special_message = item_use_messages.get(item_name, f"You used **{item_name}**!")

    embed = discord.Embed(
        title="✨ Item Used!",
        description=special_message,
        color=discord.Color.luminous_vivid_pink()
    )
    await interaction.response.send_message(embed=embed)

# Bot Ready
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}!")

# Run Bot
bot.run(os.getenv("DISCORD_TOKEN"))
