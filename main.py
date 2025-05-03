import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import asyncio
import math
import random
import time
from datetime import datetime, timedelta

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

db_file = "db.json"
trivia_file = "trivia.json"
counting_channel_id = None

if os.path.exists(db_file):
    with open(db_file, "r") as f:
        db = json.load(f)
else:
    db = {"users": {}, "counting": {"number": 1, "last_user": None, "channel_id": None}}

def save_db():
    with open(db_file, "w") as f:
        json.dump(db, f, indent=4)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@tree.command(name="setchannel", description="Set the counting channel")
async def setchannel(interaction: discord.Interaction):
    db["counting"]["channel_id"] = interaction.channel.id
    save_db()
    await interaction.response.send_message("This channel is now the counting channel!", ephemeral=True)

@tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0, "last_daily": 0, "counted": 0}
    save_db()
    await interaction.response.send_message(f"Your balance: 💰 {db['users'][user_id]['balance']}")

@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    now = int(time.time())
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0, "last_daily": 0, "counted": 0}
    if now - db["users"][user_id]["last_daily"] >= 86400:
        db["users"][user_id]["balance"] += 100
        db["users"][user_id]["last_daily"] = now
        save_db()
        await interaction.response.send_message("You claimed 💰 100 daily coins!")
    else:
        remaining = 86400 - (now - db["users"][user_id]["last_daily"])
        await interaction.response.send_message(f"You need to wait {int(remaining/3600)}h {int((remaining%3600)/60)}m more.")

@tree.command(name="leaderboard", description="See the counting leaderboard")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(db["users"].items(), key=lambda x: x[1].get("counted", 0), reverse=True)
    desc = ""
    for i, (uid, data) in enumerate(sorted_users[:10], 1):
        user = await bot.fetch_user(int(uid))
        desc += f"**{i}.** {user.name} - {data.get('counted', 0)} counts\n"
    embed = discord.Embed(title="🏆 Leaderboard", description=desc)
    await interaction.response.send_message(embed=embed)

@tree.command(name="shop", description="View and buy items")
@app_commands.describe(role_name="For ❓ a mystery ❓, enter the role to receive")
async def shop(interaction: discord.Interaction, role_name: str = None):
    user_id = str(interaction.user.id)
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0, "last_daily": 0, "counted": 0}
    items = {
        "🍪 Cookie": {"price": 10, "desc": "nom nom"},
        "🎁 Lootbox": {"price": 50, "desc": "What's inside?"},
        "❓ a mystery ❓": {"price": 0, "desc": "Gives you a role!"}
    }
    options = []
    for name, data in items.items():
        options.append(discord.SelectOption(label=name, description=f"{data['desc']} (💰 {data['price']})"))

    class ShopSelect(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder="Choose an item to buy", options=options)

        async def callback(self, interaction2: discord.Interaction):
            choice = self.values[0]
            item = items[choice]
            if db["users"][user_id]["balance"] >= item["price"]:
                db["users"][user_id]["balance"] -= item["price"]
                if choice == "❓ a mystery ❓" and role_name:
                    role = discord.utils.get(interaction.guild.roles, name=role_name)
                    if role:
                        await interaction.user.add_roles(role)
                        await interaction2.response.send_message(f"You got the role {role_name}! 🎉")
                    else:
                        await interaction2.response.send_message("Role not found.")
                else:
                    await interaction2.response.send_message(f"You bought {choice}!")
                save_db()
            else:
                await interaction2.response.send_message("Not enough balance.")

    view = discord.ui.View()
    view.add_item(ShopSelect())
    await interaction.response.send_message("Welcome to the shop!", view=view)

@tree.command(name="profile", description="View your profile")
async def profile(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0, "last_daily": 0, "counted": 0}
    user = interaction.user
    embed = discord.Embed(title=f"{user.name}'s Profile")
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="💰 Balance", value=str(db["users"][user_id]["balance"]))
    embed.add_field(name="🔢 Counted", value=str(db["users"][user_id]["counted"]))
    await interaction.response.send_message(embed=embed)

@tree.command(name="trivia", description="Play a trivia game")
async def trivia(interaction: discord.Interaction):
    with open(trivia_file, "r") as f:
        questions = json.load(f)
    q = random.choice(questions)

    class TriviaView(discord.ui.View):
        def __init__(self):
            super().__init__()
            for key, val in q["choices"].items():
                self.add_item(discord.ui.Button(label=val, custom_id=key))
            self.add_item(discord.ui.Button(label="Another Question", style=discord.ButtonStyle.secondary, custom_id="another"))

        @discord.ui.button(label="Reveal Answer", style=discord.ButtonStyle.blurple)
        async def reveal(self, interaction2: discord.Interaction, button: discord.ui.Button):
            correct = q["choices"][q["correct"]]
            await interaction2.response.send_message(f"✅ Correct answer: {correct}")

    await interaction.response.send_message(f"❓ {q['question']}", view=TriviaView())

@tree.command(name="funny", description="Show a funny image")
async def funny(interaction: discord.Interaction):
    url = "https://cdn.discordapp.com/attachments/1368349957718802572/1368357820507885618/image.png?ex=6817ee07&is=68169c87&hm=537c1b38a8525ba52acb5e2a3c6b36796bb3ae85e9a72124162e7011b0d68aa3&"
    await interaction.response.send_message(url)

@tree.command(name="meme", description="Show a cryptic meme")
async def meme(interaction: discord.Interaction):
    msg = "ün ün ün 𓀂𓀇𓀉𓀍𓀠𓁀𓁂𓀱𓁉𓀿𓀪𓁶𓂧𓂮𓂫𓃹𓃳𓄜𓄲𓄓𓅆𓅢𓅼𓆀𓆾𓈙𓉒𓉼𓊪𓋜𓋒𓍲𓎳𓁀𓄲𓅢 ün ün ün ün ün ün AAAAAAAAAAAAAOOOOOOOOORRRRXT 01001000 0110101 01101000 01100101 0010000 01001001 0010000 01101000 01100001 01110110 01100101 00100000 01110011 01100101 01111000 00100000 01110111 01101001 01110100 01101000 00100000 01101101 00100000 01110000 01101111 01101111 01110000 01101111 01101111 00100000 01110000 01110000"
    await interaction.response.send_message(msg)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    channel_id = db["counting"].get("channel_id")
    if channel_id and message.channel.id == channel_id:
        content = message.content.replace(" ", "")
        try:
            number = eval(content, {"__builtins__": {}}, math.__dict__)
            if int(number) == db["counting"]["number"]:
                db["counting"]["number"] += 1
                db["counting"]["last_user"] = str(message.author.id)
                uid = str(message.author.id)
                if uid not in db["users"]:
                    db["users"][uid] = {"balance": 0, "last_daily": 0, "counted": 0}
                db["users"][uid]["counted"] += 1
                await message.channel.send(str(db["counting"]["number"]))
                db["counting"]["number"] += 1
            else:
                db["counting"]["number"] = 1
                await message.channel.send("❌ Wrong number! Start over from 1.")
        except:
            await message.channel.send("❌ Invalid input.")
        save_db()
    await bot.process_commands(message)

bot.run(os.getenv("DISCORD_TOKEN"))
