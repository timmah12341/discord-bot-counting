import discord
from discord.ext import commands
import random
import json
import os

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Load or create the database
if not os.path.exists("database.json"):
    with open("database.json", "w") as f:
        json.dump({"current_number": 1, "leaderboard": {}, "economy": {}, "banned_words": []}, f)

with open("database.json", "r") as f:
    db = json.load(f)

# Load trivia questions
with open("trivia.json", "r") as f:
    trivia_questions = json.load(f)

# Save database
def save_db():
    with open("database.json", "w") as f:
        json.dump(db, f, indent=4)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def count(ctx, number: int):
    if number == db["current_number"]:
        db["current_number"] += 1
        db["leaderboard"].setdefault(str(ctx.author.id), 0)
        db["leaderboard"][str(ctx.author.id)] += 1
        save_db()
        await ctx.send(f"{number}")
    else:
        await ctx.send(f"{db['current_number']}")

@bot.command()
async def leaderboard(ctx):
    sorted_leaderboard = sorted(db["leaderboard"].items(), key=lambda x: x[1], reverse=True)
    description = ""
    for i, (user_id, score) in enumerate(sorted_leaderboard[:10], start=1):
        user = await bot.fetch_user(int(user_id))
        description += f"{i}. {user.name}: {score}\n"
    
    embed = discord.Embed(title="Leaderboard", description=description, color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command()
async def trivia(ctx):
    question = random.choice(trivia_questions)
    embed = discord.Embed(title="Trivia Time!", description=question["question"], color=discord.Color.green())
    
    for option, answer in question["choices"].items():
        embed.add_field(name=option, value=answer, inline=False)
    
    message = await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.upper() in ["A", "B", "C"]

    try:
        guess = await bot.wait_for('message', timeout=20.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send(f"Time's up! The correct answer was {question['correct']}.")
        return

    if guess.content.upper() == question["correct"]:
        await ctx.send("Correct!")
        db["economy"].setdefault(str(ctx.author.id), 0)
        db["economy"][str(ctx.author.id)] += 10
        save_db()
    else:
        await ctx.send(f"Wrong! Correct answer: {question['correct']}")

@bot.command()
async def balance(ctx):
    balance = db["economy"].get(str(ctx.author.id), 0)
    await ctx.send(f"You have {balance} coins.")

@bot.command()
async def addban(ctx, *, word):
    db["banned_words"].append(word.lower())
    save_db()
    await ctx.send(f"Added `{word}` to banned words list.")

@bot.command()
async def banned(ctx):
    if db["banned_words"]:
        await ctx.send("Banned words: " + ", ".join(db["banned_words"]))
    else:
        await ctx.send("No banned words yet!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    for word in db["banned_words"]:
        if word in message.content.lower():
            await message.delete()
            await message.channel.send(f"{message.author.mention}, that word is banned!")
            return

    await bot.process_commands(message)

# Your bot token here
bot.run("YOUR_BOT_TOKEN")
