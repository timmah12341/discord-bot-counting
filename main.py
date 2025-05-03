import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import random
import math
import ast
from datetime import datetime, timedelta

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
TOKEN = os.getenv("DISCORD_TOKEN")

# Load or initialize database
if not os.path.exists("db.json"):
    with open("db.json", "w") as f:
        json.dump({"users": {}, "count": {"current": 1, "channel": None}}, f)

def load_db():
    with open("db.json", "r") as f:
        return json.load(f)

def save_db(data):
    with open("db.json", "w") as f:
        json.dump(data, f, indent=4)

def safe_eval(expr):
    try:
        allowed_names = {k: getattr(math, k) for k in dir(math) if not k.startswith("__")}
        allowed_names.update({"abs": abs})
        return eval(expr, {"__builtins__": {}}, allowed_names)
    except:
        return None

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    db = load_db()
    count_channel_id = db["count"]["channel"]
    if message.channel.id != count_channel_id:
        return

    try:
        user_input = safe_eval(message.content.strip())
        if user_input is None or not isinstance(user_input, (int, float)):
            return
        user_input = round(user_input)
    except:
        return

    current = db["count"]["current"]
    if user_input != current:
        db["count"]["current"] = 1
        save_db(db)
        return await message.channel.send(f"❌ Wrong number! Count restarted. Start again from `1`.")

    # Update user stats
    user_id = str(message.author.id)
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0, "count": 0, "last_daily": None, "items": []}
    db["users"][user_id]["count"] += 1
    db["users"][user_id]["balance"] += 1
    db["count"]["current"] += 1
    save_db(db)

    await message.channel.send(f"✅ {db['count']['current'] - 1}")
    return

@bot.tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    db = load_db()
    user_id = str(interaction.user.id)
    bal = db["users"].get(user_id, {}).get("balance", 0)
    await interaction.response.send_message(embed=discord.Embed(
        title="💰 Your Balance",
        description=f"You have **{bal}** coins.",
        color=discord.Color.gold()
    ), ephemeral=True)

@bot.tree.command(name="daily", description="Get daily reward")
async def daily(interaction: discord.Interaction):
    db = load_db()
    user_id = str(interaction.user.id)
    now = datetime.utcnow()

    user_data = db["users"].setdefault(user_id, {"balance": 0, "count": 0, "last_daily": None, "items": []})
    last_claim = user_data.get("last_daily")

    if last_claim:
        last_time = datetime.strptime(last_claim, "%Y-%m-%d")
        if (now - last_time).days < 1:
            return await interaction.response.send_message("🕒 You already claimed your daily today!", ephemeral=True)

    user_data["balance"] += 50
    user_data["last_daily"] = now.strftime("%Y-%m-%d")
    save_db(db)
    await interaction.response.send_message("🎉 You claimed your daily 50 coins!", ephemeral=True)

@bot.tree.command(name="leaderboard", description="Top counters")
async def leaderboard(interaction: discord.Interaction):
    db = load_db()
    sorted_users = sorted(db["users"].items(), key=lambda x: x[1]["count"], reverse=True)
    desc = ""
    for i, (uid, data) in enumerate(sorted_users[:10], start=1):
        user = await bot.fetch_user(int(uid))
        desc += f"**{i}. {user.name}** — {data['count']} counts\n"

    embed = discord.Embed(title="🏆 Leaderboard", description=desc or "No data", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="profile", description="View your profile")
async def profile(interaction: discord.Interaction):
    db = load_db()
    user_id = str(interaction.user.id)
    user_data = db["users"].get(user_id, {"balance": 0, "count": 0, "items": []})
    embed = discord.Embed(title="👤 Your Profile", color=discord.Color.purple())
    embed.add_field(name="🧮 Total Counted", value=str(user_data["count"]), inline=True)
    embed.add_field(name="💸 Balance", value=str(user_data["balance"]), inline=True)
    embed.add_field(name="🎒 Items", value=", ".join(user_data["items"]) or "None", inline=False)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

items = {
    "🍪 Cookie": {"price": 10, "desc": "*nom nom*"},
    "🍕 Pizza": {"price": 20, "desc": "Hot and cheesy!"},
    "🐱 Cat Plush": {"price": 30, "desc": "So soft and cute!"},
    "🎩 Fancy Hat": {"price": 40, "desc": "Very stylish!"},
    "❓ a mystery ❓": {"price": 0, "desc": "Grants a role!", "role": "Shop Searcher"}
}

@bot.tree.command(name="shop", description="View and buy items")
async def shop(interaction: discord.Interaction):
    options = [discord.SelectOption(label=item, description=data["desc"]) for item, data in items.items()]
    select = discord.ui.Select(placeholder="Choose an item to buy", options=options)

    class BuyView(discord.ui.View):
        @discord.ui.select(placeholder="Choose an item", options=options)
        async def select_callback(self, interaction2: discord.Interaction, select: discord.ui.Select):
            choice = select.values[0]
            db = load_db()
            user_id = str(interaction.user.id)
            user_data = db["users"].setdefault(user_id, {"balance": 0, "count": 0, "last_daily": None, "items": []})
            item_data = items[choice]

            if choice in user_data["items"]:
                return await interaction2.response.send_message("You already own this!", ephemeral=True)

            if user_data["balance"] < item_data["price"]:
                return await interaction2.response.send_message("Not enough coins!", ephemeral=True)

            user_data["balance"] -= item_data["price"]
            user_data["items"].append(choice)

            # Give role if item is special
            if choice == "❓ a mystery ❓":
                role = discord.utils.get(interaction.guild.roles, name=item_data["role"])
                if role:
                    await interaction.user.add_roles(role)

            save_db(db)
            await interaction2.response.send_message(f"✅ Bought {choice}! {item_data['desc']}", ephemeral=True)

    embed = discord.Embed(title="🛍️ Shop", description="Buy items using your coins!", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, view=BuyView(), ephemeral=True)

@bot.tree.command(name="setchannel", description="Set the counting channel")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    db = load_db()
    db["count"]["channel"] = channel.id
    save_db(db)
    await interaction.response.send_message(f"✅ Counting channel set to {channel.mention}")

# Trivia
with open("trivia.json", "r") as f:
    trivia_questions = json.load(f)

@bot.tree.command(name="trivia", description="Answer a trivia question")
async def trivia(interaction: discord.Interaction):
    q = random.choice(trivia_questions)
    correct = q["correct"]
    buttons = []

    class TriviaView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            for key, value in q["choices"].items():
                self.add_item(discord.ui.Button(label=f"{key}: {value}", custom_id=key))

            self.add_item(discord.ui.Button(label="🔄 Another Question", style=discord.ButtonStyle.secondary, custom_id="another"))

        @discord.ui.button(label="Placeholder", disabled=True)
        async def handle_answer(self, interaction2: discord.Interaction, button: discord.ui.Button):
            pass

        async def interaction_check(self, i: discord.Interaction):
            return i.user == interaction.user

        async def on_timeout(self):
            await interaction.followup.send("⏰ Time's up!", ephemeral=True)

        async def on_submit(self, i: discord.Interaction):
            pass

    embed = discord.Embed(title="❓ Trivia", description=q["question"], color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, view=TriviaView(), ephemeral=True)

bot.run("DISCORD_TOKEN")
