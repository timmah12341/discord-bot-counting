import discord
from discord.ext import commands
import json
import random
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Load database
def load_db():
    try:
        with open('db.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "current_number": 1,
            "leaderboard": {},
            "economy": {},
            "banned_words": [],
            "inventory": {},
            "trivia_questions": []
        }

db = load_db()

# Load trivia questions from trivia.json
def load_trivia():
    try:
        with open('trivia.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

db['trivia_questions'] = load_trivia()  # Load trivia questions from the file

# Save database
def save_db():
    with open('db.json', 'w') as f:
        json.dump(db, f, indent=4)

# Command: /start
@bot.command()
async def start(ctx):
    db['economy'][str(ctx.author.id)] = {'coins': 0}
    save_db()
    await ctx.send(f"Welcome {ctx.author.name}, your account has been set up!")

# Command: /counting
@bot.command()
async def counting(ctx, number: int):
    if number != db['current_number']:
        await ctx.send(f"Wrong number! Expected: {db['current_number']}")
    else:
        db['current_number'] += 1
        save_db()
        await ctx.send(f"Correct! The next number is {db['current_number']}.")

# Command: /trivia
@bot.command()
async def trivia(ctx):
    if not db['trivia_questions']:
        await ctx.send("No trivia questions available!")
        return

    question = random.choice(db['trivia_questions'])
    embed = discord.Embed(title="Trivia Question", description=question["question"], color=discord.Color.blue())
    
    for choice, answer in question["choices"].items():
        embed.add_field(name=choice, value=answer, inline=False)

    # Send trivia question privately
    await ctx.author.send(embed=embed)
    await ctx.send("The trivia question has been sent to your DM!")

# Command: /profile
@bot.command()
async def profile(ctx):
    embed = discord.Embed(title=f"{ctx.author.name}'s Profile", color=discord.Color.green())
    embed.set_thumbnail(url=ctx.author.avatar.url)
    embed.add_field(name="Coins", value=db['economy'][str(ctx.author.id)]['coins'], inline=False)
    
    # Add other profile details if necessary

    await ctx.send(embed=embed)

# Command: /shop
@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="Shop", description="Here are the items you can buy:", color=discord.Color.gold())
    embed.add_field(name="🍪 Cookie", value="Price: 50 coins. *Nom Nom* 🍪", inline=False)
    embed.add_field(name="🎩 Top Hat", value="Price: 100 coins.", inline=False)
    embed.add_field(name="💎 Diamond", value="Price: 500 coins.", inline=False)
    
    await ctx.send(embed=embed)

# Command: /buy
@bot.command()
async def buy(ctx, item: str):
    items = {"cookie": 50, "tophat": 100, "diamond": 500}
    
    if item.lower() not in items:
        await ctx.send("Item not found!")
        return
    
    price = items[item.lower()]
    user_id = str(ctx.author.id)
    
    if db['economy'].get(user_id, {}).get('coins', 0) < price:
        await ctx.send("You don't have enough coins!")
        return
    
    db['economy'][user_id]['coins'] -= price
    db['inventory'].setdefault(user_id, []).append(item.lower())
    save_db()
    
    await ctx.send(f"{ctx.author.name} bought a {item} for {price} coins! 🎉")

# Command: /use
@bot.command()
async def use(ctx, item: str):
    user_id = str(ctx.author.id)
    
    if item.lower() not in db['inventory'].get(user_id, []):
        await ctx.send(f"You don't have a {item}!")
        return

    db['inventory'][user_id].remove(item.lower())
    save_db()
    
    if item.lower() == "cookie":
        await ctx.send(f"*Nom Nom* {ctx.author.name} ate a cookie! 🍪")
    elif item.lower() == "tophat":
        await ctx.send(f"{ctx.author.name} put on a top hat! 🎩")
    elif item.lower() == "diamond":
        await ctx.send(f"{ctx.author.name} used a diamond! 💎")
    else:
        await ctx.send(f"{ctx.author.name} used {item}!")

# Command: /leaderboard
@bot.command()
async def leaderboard(ctx):
    leaderboard = sorted(db['economy'].items(), key=lambda x: x[1]['coins'], reverse=True)
    embed = discord.Embed(title="Leaderboard", color=discord.Color.orange())
    
    for idx, (user_id, data) in enumerate(leaderboard[:10], 1):
        user = await bot.fetch_user(int(user_id))
        embed.add_field(name=f"{idx}. {user.name}", value=f"{data['coins']} coins", inline=False)
    
    await ctx.send(embed=embed)

bot.run('DISCORD_TOKEN')  # Replace with your actual token or use environment variable
