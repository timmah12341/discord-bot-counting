import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import random
import asyncio
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DB_FILE = "db.json"
TRIVIA_FILE = "trivia.json"
counting_channel_ids = [1368349957718802572, 1366574260554043503]

# === JSON DATABASE ===
def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"users": {}, "counting_channel": 1366574260554043503}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

db = load_db()

# === UTILITY FUNCTIONS ===
def get_user(user_id):
    if str(user_id) not in db["users"]:
        db["users"][str(user_id)] = {
            "balance": 0,
            "last_daily": "2000-01-01T00:00:00",
            "count": 0
        }
        save_db(db)
    return db["users"][str(user_id)]

def format_embed(title, description, color=discord.Color.blue()):
    return discord.Embed(title=title, description=description, color=color)

# === EVENTS ===
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await tree.sync()
    for channel_id in counting_channel_ids:
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                await channel.send("✅ Bot is now **online** and ready!")
            except Exception as e:
                print(f"Failed to send wake-up message to channel {channel_id}: {e}")

# === COMMANDS ===

@tree.command(name="setchannel", description="Set the counting channel")
async def setchannel(interaction: discord.Interaction):
    db["counting_channel"] = interaction.channel.id
    save_db(db)
    await interaction.response.send_message(embed=format_embed("🔧 Channel Set", f"Counting channel set to <#{interaction.channel.id}>"))

@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    last_claimed = datetime.fromisoformat(user["last_daily"])
    now = datetime.utcnow()
    if now - last_claimed >= timedelta(hours=24):
        amount = random.randint(100, 200)
        user["balance"] += amount
        user["last_daily"] = now.isoformat()
        save_db(db)
        await interaction.response.send_message(embed=format_embed("💰 Daily Claimed!", f"You received **{amount} coins**!"))
    else:
        remaining = timedelta(hours=24) - (now - last_claimed)
        await interaction.response.send_message(embed=format_embed("🕒 Not Yet!", f"Come back in **{str(remaining).split('.')[0]}**."), ephemeral=True)

@tree.command(name="balance", description="View your coin balance")
async def balance(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    await interaction.response.send_message(embed=format_embed("💰 Balance", f"You have **{user['balance']} coins**."))

@tree.command(name="meme", description="Get a mysterious meme")
async def meme(interaction: discord.Interaction):
    await interaction.response.send_message("ün ün ün 𓀂𓀇𓀉𓀍𓀠𓁀𓁂𓀱𓁉𓀿𓀪𓁶𓂧𓂮𓂫𓃹𓃳𓄜𓄲𓄓𓅆𓅢𓅼𓆀𓆾𓈙𓉒𓉼𓊪𓋜𓋒𓍲𓎳𓁀𓄲𓅢 ün ün ün ün ün ün AAAAAAAAAAAAAOOOOOOOOORRRRXT 01001000 0110101 01101000 01100101 0010000 01001001 0010000 01101000 01100001 01110110 01100101 00100000 01110011 01100101 01111000 00100000 01110111 01101001 01110100 01101000 00100000 01101101 00100000 01110000 01101111 01101111 01110000 01101111 01101111 00100000 01110000 01110000")

@tree.command(name="funny", description="Get a funny image")
async def funny(interaction: discord.Interaction):
    await interaction.response.send_message("https://cdn.discordapp.com/attachments/1368349957718802572/1368357820507885618/image.png?ex=6817ee07&is=68169c87&hm=537c1b38a8525ba52acb5e2a3c6b36796bb3ae85e9a72124162e7011b0d68aa3&")

@tree.command(name="shop", description="View the shop and buy items")
async def shop(interaction: discord.Interaction):
    options = [
        discord.SelectOption(label="🍪 Cookie", description="Just a cookie. Nom nom!", value="cookie"),
        discord.SelectOption(label="❓ a mystery ❓", description="Gives you a special role!", value="mystery")
    ]
    select = discord.ui.Select(placeholder="Choose an item to buy", options=options)

    class ShopView(discord.ui.View):
        @discord.ui.select(placeholder="Choose an item to buy", options=options)
        async def select_callback(self, select, interaction2: discord.Interaction):
            user = get_user(interaction2.user.id)
            choice = select.values[0]
            if choice == "cookie":
                if user["balance"] >= 50:
                    user["balance"] -= 50
                    save_db(db)
                    await interaction2.response.send_message(embed=format_embed("🍪 Enjoy!", "You ate a delicious cookie."))
                else:
                    await interaction2.response.send_message(embed=format_embed("❌ Not Enough!", "You don't have enough coins."), ephemeral=True)
            elif choice == "mystery":
                if user["balance"] >= 100:
                    user["balance"] -= 100
                    save_db(db)

                    await interaction2.response.send_modal(MysteryModal(user_id=interaction2.user.id))
                else:
                    await interaction2.response.send_message(embed=format_embed("❌ Not Enough!", "You need 100 coins."), ephemeral=True)

    await interaction.response.send_message(embed=format_embed("🛍️ Shop", "Choose an item to buy:"), view=ShopView())

class MysteryModal(discord.ui.Modal, title="Mystery Role"):
    role_name = discord.ui.TextInput(label="Role name to receive", placeholder="Enter an existing role name", required=True)

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name=self.role_name.value)
        if role:
            try:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(embed=format_embed("🎁 Mystery Solved!", f"You received the **{role.name}** role!"))
            except discord.Forbidden:
                await interaction.response.send_message(embed=format_embed("❌ Failed", "I don't have permission to assign that role."), ephemeral=True)
        else:
            await interaction.response.send_message(embed=format_embed("❌ Role Not Found", "That role doesn't exist."), ephemeral=True)

@tree.command(name="trivia", description="Answer a trivia question")
async def trivia(interaction: discord.Interaction):
    if not os.path.exists(TRIVIA_FILE):
        await interaction.response.send_message("Trivia file not found.")
        return
    with open(TRIVIA_FILE, "r") as f:
        questions = json.load(f)
    question = random.choice(questions)
    correct_answer = question["correct"]
    choices = question["choices"]

    class TriviaView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=15)
            for key, val in choices.items():
                self.add_item(discord.ui.Button(label=val, custom_id=key))

            self.add_item(discord.ui.Button(label="🔁 Another Question", style=discord.ButtonStyle.secondary, custom_id="another"))

        @discord.ui.button(label="🔁 Another Question", style=discord.ButtonStyle.secondary, custom_id="another")
        async def another(self, button: discord.ui.Button, interaction2: discord.Interaction):
            await trivia(interaction2)

        async def interaction_check(self, interaction2: discord.Interaction) -> bool:
            if interaction2.user != interaction.user:
                await interaction2.response.send_message("This isn't your question!", ephemeral=True)
                return False
            return True

        async def on_timeout(self):
            await interaction.edit_original_response(view=None)

        async def on_error(self, interaction2: discord.Interaction, error: Exception, item):
            await interaction2.response.send_message("An error occurred.", ephemeral=True)

    embed = format_embed("❓ Trivia Time!", question["question"])
    await interaction.response.send_message(embed=embed, view=TriviaView())

@tree.command(name="leaderboard", description="Show top counters")
async def leaderboard(interaction: discord.Interaction):
    users_sorted = sorted(db["users"].items(), key=lambda x: x[1].get("count", 0), reverse=True)
    desc = "\n".join([f"<@{uid}>: {info.get('count', 0)} counts" for uid, info in users_sorted[:10]])
    await interaction.response.send_message(embed=format_embed("🏆 Leaderboard", desc or "No data yet."))

@tree.command(name="profile", description="View your profile")
async def profile(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    embed = format_embed("👤 Profile", f"**Balance**: {user['balance']} coins\n**Counted**: {user['count']} times")
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

# === MESSAGE-BASED COUNTING ===
@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author.bot or message.channel.id != db.get("counting_channel"):
        return

    user = get_user(message.author.id)
    try:
        result = eval(message.content, {"__builtins__": None}, {"pi": 3.14159})
        if int(result) % 2 == 1:
            count = int(result + 1)
            user["count"] += 1
            save_db(db)
            await message.channel.send(f"{count}")
    except:
        pass

# === RUN ===
bot.run(os.getenv("DISCORD_TOKEN"))
