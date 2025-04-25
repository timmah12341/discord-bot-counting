import discord
from discord.ext import commands
import random
import asyncio
import os
import json

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

# Load and save database
def load_db():
    if not os.path.exists("db.json"):
        with open("db.json", "w") as f:
            json.dump({
                "current_number": 1,
                "leaderboard": {},
                "economy": {},
                "banned_words": []
            }, f)
    with open("db.json", "r") as f:
        return json.load(f)

def save_db(db):
    with open("db.json", "w") as f:
        json.dump(db, f)

db = load_db()

bot = commands.Bot(command_prefix="!", intents=intents, application_id=os.environ.get("APPLICATION_ID"))

@bot.event
async def on_ready():
    print(f"✅ Bot is online as: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"🔃 Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"⚠️ Failed to sync commands: {e}")

async def handle_permission_error(interaction: discord.Interaction):
    await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)

# Economy functions
def get_balance(user_id: str) -> int:
    return db["economy"].get(user_id, 0)

def update_balance(user_id: str, amount: int):
    db["economy"][user_id] = get_balance(user_id) + amount
    save_db(db)

# Add banned word command
@bot.tree.command(name="add_banned_word", description="Add a word to banned list")
async def add_banned_word(interaction: discord.Interaction, word: str):
    if interaction.user.guild_permissions.manage_messages:
        db["banned_words"].append(word.lower())
        save_db(db)
        await interaction.response.send_message(f"Added '{word}' to banned words list")
    else:
        await handle_permission_error(interaction)

# Balance command
@bot.tree.command(name="balance", description="Check your balance and stats")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    bal = get_balance(user_id)
    score = db["leaderboard"].get(user_id, 0)
    embed = discord.Embed(title="👤 User Profile", color=discord.Color.gold())
    embed.add_field(name="💰 Balance", value=f"{bal} coins", inline=False)
    embed.add_field(name="🏆 Score", value=f"{score} points", inline=False)
    await interaction.response.send_message(embed=embed)

# Work command
@bot.tree.command(name="work", description="Work to earn coins")
async def work(interaction: discord.Interaction):
    jobs = ["programmer", "chef", "doctor", "teacher", "artist"]
    earnings = random.randint(10, 100)
    job = random.choice(jobs)
    update_balance(str(interaction.user.id), earnings)
    await interaction.response.send_message(f"You worked as a {job} and earned {earnings} coins!")

# Current number command
@bot.tree.command(name="current", description="Check the current number in the counting game")
async def current(interaction: discord.Interaction):
    await interaction.response.send_message(f"The current number is: {db['current_number']}")

# Counting game handler
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check for banned words
    if any(word in message.content.lower() for word in db["banned_words"]):
        await message.delete()
        await message.channel.send(f"{message.author.mention} That word is not allowed!")
        return

    # Counting game logic
    try:
        if message.content.isdigit():
            number = int(message.content)
            current = db["current_number"]

            if number == current:
                if number % 2 == 1:
                    uid = str(message.author.id)
                    db["leaderboard"][uid] = db["leaderboard"].get(uid, 0) + 1
                    db["current_number"] += 1
                    await message.add_reaction("✅")
                    await message.channel.send(str(db["current_number"]))  # bot posts even number
                    db["current_number"] += 1
                    save_db(db)
                else:
                    await message.add_reaction("❌")
                    db["current_number"] = 1
                    save_db(db)
                    await message.channel.send("You need to send an odd number!\nGame restarted. Current number: 1")
            else:
                await message.add_reaction("❌")
                await message.channel.send(f"{message.author.mention}, wrong number! The next number should be {current}")
    except Exception as e:
        print(f"Error in number game: {e}")

    await bot.process_commands(message)

# Run the bot
bot.run(os.environ["DISCORD_TOKEN"])
