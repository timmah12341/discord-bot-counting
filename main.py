import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import math
import random
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Load or create database
if os.path.exists("db.json"):
    with open("db.json", "r") as f:
        db = json.load(f)
else:
    db = {"users": {}, "counting": {"current": 1, "channel_id": None}}

def save_db():
    with open("db.json", "w") as f:
        json.dump(db, f, indent=4)

def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0, "counted": 0, "inventory": [], "last_daily": None}
    return db["users"][user_id]

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    channel_id = db["counting"]["channel_id"]
    if not channel_id or message.channel.id != channel_id:
        return

    user_input = message.content.replace(" ", "")
    try:
        expected = db["counting"]["current"]
        evaluated = round(eval(user_input, {"__builtins__": None, "pi": math.pi, "e": math.e, "sqrt": math.sqrt}), 6)
        if evaluated == expected and expected % 2 == 1:
            db["counting"]["current"] += 1
            get_user_data(message.author.id)["counted"] += 1
            save_db()
            await message.channel.send(embed=discord.Embed(
                description=f"🧠 {bot.user.mention} says **{db['counting']['current']}**!",
                color=discord.Color.blurple()
            ))
            db["counting"]["current"] += 1
            save_db()
        else:
            db["counting"]["current"] = 1
            await message.channel.send(embed=discord.Embed(
                description="❌ Wrong number! Resetting count to **1**!",
                color=discord.Color.red()
            ))
            save_db()
    except:
        pass

@tree.command(name="balance", description="View your balance")
async def balance(interaction: discord.Interaction):
    data = get_user_data(interaction.user.id)
    await interaction.response.send_message(embed=discord.Embed(
        title="💰 Your Balance",
        description=f"You have **{data['balance']}** coins!",
        color=discord.Color.gold()
    ), ephemeral=True)

@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    data = get_user_data(interaction.user.id)
    now = datetime.utcnow()
    if data["last_daily"] and datetime.fromisoformat(data["last_daily"]) > now - timedelta(hours=24):
        await interaction.response.send_message("⏳ You've already claimed your daily today!", ephemeral=True)
    else:
        data["balance"] += 100
        data["last_daily"] = now.isoformat()
        save_db()
        await interaction.response.send_message("✅ You claimed **100 coins**!", ephemeral=True)

@tree.command(name="profile", description="View your profile")
async def profile(interaction: discord.Interaction):
    data = get_user_data(interaction.user.id)
    embed = discord.Embed(
        title=f"{interaction.user.name}'s Profile 🧾",
        description=f"**Balance:** {data['balance']} coins\n**Counted:** {data['counted']} times\n**Items:** {', '.join(data['inventory']) or 'None'}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="shop", description="View and buy items")
async def shop(interaction: discord.Interaction):
    items = {
        "🍪 Cookie": {"cost": 10, "message": "*nom nom*"},
        "🎟️ Ticket": {"cost": 25, "message": "🎫 A ticket to nowhere."},
        "❓ a mystery ❓": {"cost": 0, "message": "🤫 What could it be?"}
    }

    options = [
        discord.SelectOption(label=name, description=f"Buy for {info['cost']} coins")
        for name, info in items.items()
    ]

    class ShopView(discord.ui.View):
        @discord.ui.select(placeholder="Choose an item to buy", options=options)
        async def select_callback(self, interaction2, select):
            item = select.values[0]
            data = get_user_data(interaction.user.id)
            if item == "❓ a mystery ❓":
                role_name = "Shop Searcher"
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if not role:
                    role = await interaction.guild.create_role(name=role_name)
                await interaction.user.add_roles(role)
                await interaction2.response.send_message(f"You got the **{item}**! {items[item]['message']}\nGiven role: {role.mention}", ephemeral=True)
            elif data["balance"] >= items[item]["cost"]:
                data["balance"] -= items[item]["cost"]
                data["inventory"].append(item)
                save_db()
                await interaction2.response.send_message(f"✅ Bought **{item}**! {items[item]['message']}", ephemeral=True)
            else:
                await interaction2.response.send_message("❌ Not enough coins.", ephemeral=True)

    await interaction.response.send_message(embed=discord.Embed(
        title="🛒 Shop",
        description="Choose something fun!",
        color=discord.Color.green()
    ), view=ShopView(), ephemeral=True)

@tree.command(name="leaderboard", description="Show top counters")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(db["users"].items(), key=lambda x: x[1].get("counted", 0), reverse=True)
    desc = ""
    for i, (uid, data) in enumerate(sorted_users[:10], 1):
        member = await bot.fetch_user(int(uid))
        desc += f"**{i}.** {member.name} — {data['counted']} ✅\n"
    await interaction.response.send_message(embed=discord.Embed(
        title="🏆 Counting Leaderboard",
        description=desc or "Nobody has counted yet!",
        color=discord.Color.purple()
    ))

@tree.command(name="trivia", description="Answer a trivia question")
async def trivia(interaction: discord.Interaction):
    with open("trivia.json") as f:
        questions = json.load(f)
    q = random.choice(questions)
    correct_key = q["correct"]
    correct_text = q["choices"][correct_key]

    class TriviaView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=20)
            self.answered = False

        @discord.ui.button(label="A", style=discord.ButtonStyle.secondary)
        async def a(self, _, interaction2): await self.check_answer(interaction2, "A")
        @discord.ui.button(label="B", style=discord.ButtonStyle.secondary)
        async def b(self, _, interaction2): await self.check_answer(interaction2, "B")
        @discord.ui.button(label="C", style=discord.ButtonStyle.secondary)
        async def c(self, _, interaction2): await self.check_answer(interaction2, "C")
        @discord.ui.button(label="🔁 Another Question", style=discord.ButtonStyle.blurple)
        async def again(self, _, interaction2):
            if interaction2.user.id == interaction.user.id:
                await trivia(interaction2)

        async def check_answer(self, interaction2, choice):
            if self.answered or interaction2.user.id != interaction.user.id:
                return
            self.answered = True
            if choice == correct_key:
                get_user_data(interaction.user.id)["balance"] += 50
                save_db()
                await interaction2.response.send_message(f"✅ Correct! You earned 50 coins.\nAnswer: **{correct_text}**", ephemeral=True)
            else:
                await interaction2.response.send_message(f"❌ Wrong! The correct answer was **{correct_text}**", ephemeral=True)

    embed = discord.Embed(title="🧠 Trivia Time!", description=q["question"], color=discord.Color.orange())
    for k, v in q["choices"].items():
        embed.add_field(name=k, value=v, inline=False)
    await interaction.response.send_message(embed=embed, view=TriviaView(), ephemeral=True)

@tree.command(name="setchannel", description="Set the counting channel")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    db["counting"]["channel_id"] = channel.id
    save_db()
    await interaction.response.send_message(f"✅ Counting channel set to {channel.mention}", ephemeral=True)

# Run the bot using environment variable
bot.run(os.environ["DISCORD_TOKEN"])
