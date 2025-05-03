import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import json
import os
from dotenv import load_dotenv
import random
import math
import asyncio

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Database File
db_path = "db.json"
if not os.path.exists(db_path):
    with open(db_path, 'w') as f:
        json.dump({}, f)

# Helper to load DB
def load_db():
    with open(db_path, 'r') as f:
        return json.load(f)

# Helper to save DB
def save_db(data):
    with open(db_path, 'w') as f:
        json.dump(data, f, indent=4)

# Load trivia questions
with open("trivia.json", "r") as file:
    trivia_data = json.load(file)

# Counting Settings
counting_channel_id = None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    load_db()

# Counting System
@bot.event
async def on_message(message):
    global counting_channel_id
    if counting_channel_id is None:
        return

    if message.channel.id == counting_channel_id and message.author != bot.user:
        try:
            user_input = int(message.content)
            last_count = load_db().get("count", 0)
            if user_input == last_count + 1:
                last_count += 1
                save_db({"count": last_count})
                await message.channel.send(f"{last_count} ✅")
            else:
                await message.channel.send(f"❌ Wrong number! The last count was {last_count}. Please start from {last_count + 1}.")
        except ValueError:
            pass

    await bot.process_commands(message)

# /setchannel command
@bot.command()
async def setchannel(ctx, channel_id: int):
    if ctx.channel.id == channel_id:
        counting_channel_id = channel_id
        await ctx.send(f"Counting channel set to {ctx.channel.name}")
    else:
        await ctx.send("Invalid channel.")

# /shop command
@bot.command()
async def shop(ctx):
    shop_items = [
        {"name": "Mystery Box", "price": 100, "description": "A mysterious box that grants a surprise! 🎁"},
        {"name": "Cookie 🍪", "price": 50, "description": "Nom nom! 🍪"},
        {"name": "Role Mystery ❓", "price": 200, "description": "Get a random mystery role! 🎭"}
    ]
    
    shop_embed = discord.Embed(title="Welcome to the Shop!", description="Pick an item to buy!")
    for item in shop_items:
        shop_embed.add_field(name=item['name'], value=f"Price: {item['price']} Coins\nDescription: {item['description']}", inline=False)
    
    shop_embed.set_footer(text="Use the /buy command to purchase items.")
    await ctx.send(embed=shop_embed)

# /buy command
@bot.command()
async def buy(ctx, item_name: str):
    # Example check for the role "Shop Searcher"
    if item_name.lower() == "role mystery ❓":
        user_data = load_db().get(str(ctx.author.id), {})
        user_balance = user_data.get("balance", 0)

        if user_balance >= 200:
            user_data["balance"] -= 200
            save_db(user_data)
            role = discord.utils.get(ctx.guild.roles, name="Shop Searcher")
            await ctx.author.add_roles(role)
            await ctx.send(f"Congrats {ctx.author.mention}, you've bought the Mystery Role! 🎉")
        else:
            await ctx.send("You don't have enough coins! 😞")

# /balance command
@bot.command()
async def balance(ctx):
    user_data = load_db().get(str(ctx.author.id), {})
    balance = user_data.get("balance", 0)
    await ctx.send(f"{ctx.author.mention}, you currently have {balance} coins!")

# /daily command
@bot.command()
async def daily(ctx):
    user_data = load_db().get(str(ctx.author.id), {})
    last_claim = user_data.get("last_claim", 0)
    if last_claim + 86400 > int(time.time()):
        await ctx.send("You can only claim your daily reward once every 24 hours!")
        return

    user_data["balance"] = user_data.get("balance", 0) + 100
    user_data["last_claim"] = int(time.time())
    save_db(user_data)
    await ctx.send(f"Congrats {ctx.author.mention}, you've received 100 coins! 🎉")

# Trivia command
@bot.command()
async def trivia(ctx):
    question = random.choice(trivia_data)
    question_embed = discord.Embed(title=question["question"], description="")
    for choice, answer in question["choices"].items():
        question_embed.add_field(name=choice, value=answer, inline=False)
    view = View()
    for choice, answer in question["choices"].items():
        button = Button(label=choice, style=discord.ButtonStyle.secondary, custom_id=choice)
        view.add_item(button)
    await ctx.send(embed=question_embed, view=view)

    # Wait for the user's answer
    def check(interaction):
        return interaction.user == ctx.author

    interaction = await bot.wait_for("button_click", check=check)
    if interaction.custom_id == question["correct"]:
        await interaction.response.send_message("Correct! 🎉")
    else:
        await interaction.response.send_message("Wrong answer! 😞")

    await ctx.send("Another Question?")

# Funny command
@bot.command()
async def funny(ctx):
    funny_url = "https://cdn.discordapp.com/attachments/1368349957718802572/1368357820507885618/image.png?ex=6817ee07&is=68169c87&hm=537c1b38a8525ba52acb5e2a3c6b36796bb3ae85e9a72124162e7011b0d68aa3&"
    await ctx.send(funny_url)

# Meme command
@bot.command()
async def meme(ctx):
    await ctx.send("ün ün ün 𓀂𓀇𓀉𓀍𓀠𓁀𓁂𓀱𓁉𓀿𓀪𓁶𓂧𓂮𓂫𓃹𓃳𓄜𓄲𓄓𓅆𓅢𓅼𓆀𓆾𓈙𓉒𓉼𓊪𓋜𓋒𓍲𓎳𓁀𓄲𓅢 ün ün ün ün ün ün AAAAAAAAAAAAAOOOOOOOOORRRRXT 01001000 0110101 01101000 01100101 0010000 01001001 0010000 01101000 01100001 01110110 01100101 00100000 01110011 01100101 01111000 00100000 01110111 01101001 01110100 01101000 00100000 01101101 00100000 01110000 01101111 01101111 01110000 01101111 01101111 00100000 01110000 01110000")

bot.run(TOKEN)
