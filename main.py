import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import random
import math

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DB_FILE = "db.json"
TRIVIA_FILE = "trivia.json"

# Load or initialize database
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

def load_db():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

def get_user_data(db, user_id):
    if str(user_id) not in db:
        db[str(user_id)] = {
            "balance": 0,
            "count": 0,
            "last_count": 0,
            "channel": None
        }
    return db[str(user_id)]

def eval_math(expr):
    try:
        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("__")
        }
        allowed_names.update({"pi": math.pi, "e": math.e})
        return eval(expr, {"__builtins__": {}}, allowed_names)
    except:
        return None

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    db = load_db()
    user_data = get_user_data(db, message.author.id)
    guild_data = db.get("guild", {})
    channel_id = guild_data.get("count_channel")

    if channel_id and message.channel.id == int(channel_id):
        result = eval_math(message.content)
        if result is None or int(result) != user_data["last_count"] + 2:
            user_data["last_count"] = 1 if int(result) == 1 else 0
            save_db(db)
            return

        user_data["last_count"] = int(result)
        user_data["count"] += 1
        user_data["balance"] += 1
        save_db(db)
        await message.channel.send(embed=discord.Embed(
            title="🔢 CountBot",
            description=f"{bot.user.mention}: **{user_data['last_count'] + 1}** 🎉",
            color=discord.Color.blurple()
        ))

    await bot.process_commands(message)

@tree.command(name="setchannel", description="Set the counting channel (current channel).")
async def setchannel(interaction: discord.Interaction):
    db = load_db()
    if "guild" not in db:
        db["guild"] = {}
    db["guild"]["count_channel"] = interaction.channel.id
    save_db(db)
    await interaction.response.send_message("✅ Counting channel has been set to this one!", ephemeral=True)

@tree.command(name="balance", description="Check your balance.")
async def balance(interaction: discord.Interaction):
    db = load_db()
    user_data = get_user_data(db, interaction.user.id)
    await interaction.response.send_message(embed=discord.Embed(
        title="💰 Your Balance",
        description=f"You have **{user_data['balance']}** coins!",
        color=discord.Color.gold()
    ), ephemeral=True)

@tree.command(name="profile", description="View your profile.")
async def profile(interaction: discord.Interaction):
    db = load_db()
    user_data = get_user_data(db, interaction.user.id)
    embed = discord.Embed(
        title=f"🧍 {interaction.user.name}'s Profile",
        description=f"🔢 Numbers Counted: `{user_data['count']}`\n💰 Balance: `{user_data['balance']}`",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else "")
    await interaction.response.send_message(embed=embed, ephemeral=True)

shop_items = {
    "🍪 Cookie": {
        "price": 5,
        "effect": "nom nom"
    },
    "📦 Loot Box": {
        "price": 15,
        "effect": "You found something cool inside!"
    },
    "🎩 Fancy Hat": {
        "price": 25,
        "effect": "You're now 20% fancier!"
    },
    "❓ a mystery ❓": {
        "price": 0,
        "effect": "You got the **Shop Searcher** role!"
    }
}

@tree.command(name="shop", description="Browse the shop.")
async def shop(interaction: discord.Interaction):
    options = [
        discord.SelectOption(label=name, description=f"{data['effect']} - {data['price']} coins")
        for name, data in shop_items.items()
    ]

    class ShopMenu(discord.ui.View):
        @discord.ui.select(placeholder="Choose an item to buy!", options=options)
        async def select_callback(self, interaction2: discord.Interaction, select: discord.ui.Select):
            db = load_db()
            user_data = get_user_data(db, interaction.user.id)
            item = select.values[0]
            item_data = shop_items[item]

            if user_data["balance"] < item_data["price"]:
                await interaction2.response.send_message("🚫 Not enough coins!", ephemeral=True)
                return

            if item == "❓ a mystery ❓":
                role = discord.utils.get(interaction.guild.roles, name="Shop Searcher")
                if role:
                    await interaction.user.add_roles(role)
                    await interaction2.response.send_message(f"{item_data['effect']}", ephemeral=True)
            else:
                await interaction2.response.send_message(f"✅ Bought {item}! {item_data['effect']}", ephemeral=True)

            user_data["balance"] -= item_data["price"]
            save_db(db)

    await interaction.response.send_message(embed=discord.Embed(
        title="🛍️ The Shop",
        description="Choose something fun to buy below!",
        color=discord.Color.green()
    ), view=ShopMenu(), ephemeral=True)

@tree.command(name="trivia", description="Answer a trivia question.")
async def trivia(interaction: discord.Interaction):
    with open(TRIVIA_FILE, "r") as f:
        questions = json.load(f)

    q = random.choice(questions)
    correct_answer = q["correct"]
    answer_texts = [f"{key}: {value}" for key, value in q["choices"].items()]

    class TriviaView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            for key, value in q["choices"].items():
                self.add_item(discord.ui.Button(label=value, custom_id=key, style=discord.ButtonStyle.blurple))

            self.add_item(discord.ui.Button(label="Another Question 🔁", style=discord.ButtonStyle.grey, custom_id="another"))

        @discord.ui.button(label="Another Question", style=discord.ButtonStyle.grey, custom_id="another")
        async def another_callback(self, interaction2: discord.Interaction, button: discord.ui.Button):
            await trivia(interaction2)

        async def interaction_check(self, i: discord.Interaction):
            return i.user.id == interaction.user.id

        async def on_timeout(self):
            self.stop()

        async def on_error(self, interaction: discord.Interaction, error: Exception, item):
            await interaction.response.send_message("❌ Something went wrong.", ephemeral=True)

    await interaction.response.send_message(embed=discord.Embed(
        title="❓ Trivia Time!",
        description=q["question"],
        color=discord.Color.purple()
    ), view=TriviaView(), ephemeral=True)

@tree.command(name="leaderboard", description="See the top counters.")
async def leaderboard(interaction: discord.Interaction):
    db = load_db()
    leaderboard = sorted(
        ((uid, data["count"]) for uid, data in db.items() if uid.isdigit()),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    desc = "\n".join([f"<@{uid}>: **{count}** counts" for uid, count in leaderboard])
    await interaction.response.send_message(embed=discord.Embed(
        title="🏆 Leaderboard",
        description=desc or "No one has counted yet!",
        color=discord.Color.orange()
    ))

# Run the bot
bot.run(os.environ["DISCORD_TOKEN"])
