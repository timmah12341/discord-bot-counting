import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import random
import math
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
channel_id = 1366574260554043503

db_file = "db.json"
trivia_file = "trivia.json"

if not os.path.exists(db_file):
    with open(db_file, "w") as f:
        json.dump({}, f)

def load_db():
    with open(db_file, "r") as f:
        return json.load(f)

def save_db(data):
    with open(db_file, "w") as f:
        json.dump(data, f, indent=2)

def get_user_data(user_id):
    db = load_db()
    if str(user_id) not in db:
        db[str(user_id)] = {"balance": 0, "count": 0, "last_daily": None, "inventory": []}
        save_db(db)
    return db[str(user_id)]

def update_user_data(user_id, key, value):
    db = load_db()
    if str(user_id) not in db:
        get_user_data(user_id)
        db = load_db()
    db[str(user_id)][key] = value
    save_db(db)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != channel_id:
        return

    db = load_db()
    user_id = str(message.author.id)
    user_data = get_user_data(user_id)

    try:
        user_input = eval(message.content, {"__builtins__": None, "pi": math.pi, "e": math.e, "sqrt": math.sqrt, "abs": abs})
    except:
        return

    if isinstance(user_input, (int, float)):
        expected = user_data.get("expected", 1)
        if math.isclose(user_input, expected, rel_tol=1e-9):
            bot_number = expected + 1
            await message.channel.send(f"**{bot_number}** ✅")
            update_user_data(user_id, "expected", bot_number + 1)
            update_user_data(user_id, "count", user_data["count"] + 1)
        else:
            await message.channel.send("❌ Wrong number. Restarting count.")
            update_user_data(user_id, "expected", 1)

@bot.tree.command(name="balance")
async def balance(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    embed = discord.Embed(title=f"💰 Balance", description=f"You have **{user_data['balance']}** coins.", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="daily")
async def daily(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    now = datetime.utcnow()
    last = user_data.get("last_daily")
    if last:
        last_time = datetime.fromisoformat(last)
        if now - last_time < timedelta(days=1):
            await interaction.response.send_message("⏳ You already claimed your daily reward. Come back later.")
            return
    coins = random.randint(50, 150)
    user_data["balance"] += coins
    user_data["last_daily"] = now.isoformat()
    update_user_data(interaction.user.id, "balance", user_data["balance"])
    update_user_data(interaction.user.id, "last_daily", user_data["last_daily"])
    await interaction.response.send_message(f"🎉 You received **{coins}** coins!")

@bot.tree.command(name="shop")
async def shop(interaction: discord.Interaction):
    items = {
        "🍪 Cookie": "nom nom!",
        "🥤 Soda": "*slurp!*",
        "🎉 Party Popper": "🎊 woohoo!",
        "📦 Mystery Box": "A random surprise!",
        "❓ a mystery ❓": "Gives you a secret role!"
    }
    embed = discord.Embed(title="🛍️ Shop", description="Use `/buy <item>` to purchase.", color=discord.Color.purple())
    for item, desc in items.items():
        embed.add_field(name=item, value=desc, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buy")
@app_commands.describe(item="Name of the item to buy")
async def buy(interaction: discord.Interaction, item: str):
    user_data = get_user_data(interaction.user.id)
    item = item.strip()

    if item == "❓ a mystery ❓":
        await interaction.response.send_message("Please enter the role name you want this to assign:")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=30)
            role = discord.utils.get(interaction.guild.roles, name=msg.content)
            if role:
                await interaction.user.add_roles(role)
                user_data["inventory"].append(item)
                update_user_data(interaction.user.id, "inventory", user_data["inventory"])
                await interaction.followup.send(f"🔍 You received the **{role.name}** role!")
            else:
                await interaction.followup.send("❌ Role not found.")
        except:
            await interaction.followup.send("⏳ Timeout. Please try again.")
    else:
        messages = {
            "🍪 Cookie": "*nom nom*",
            "🥤 Soda": "*slurp*",
            "🎉 Party Popper": "🎉 pop!",
            "📦 Mystery Box": "🎁 you opened the box!"
        }
        if item in messages:
            user_data["inventory"].append(item)
            update_user_data(interaction.user.id, "inventory", user_data["inventory"])
            await interaction.response.send_message(messages[item])
        else:
            await interaction.response.send_message("❌ Invalid item.")

@bot.tree.command(name="profile")
async def profile(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    embed = discord.Embed(title=f"🧾 Profile - {interaction.user.name}", color=discord.Color.blue())
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="Balance", value=f"💰 {user_data['balance']}", inline=True)
    embed.add_field(name="Counted", value=f"🔢 {user_data['count']}", inline=True)
    embed.add_field(name="Inventory", value=", ".join(user_data["inventory"]) or "None", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard")
async def leaderboard(interaction: discord.Interaction):
    db = load_db()
    top = sorted(db.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:10]
    embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.green())
    for i, (uid, data) in enumerate(top, start=1):
        user = await bot.fetch_user(int(uid))
        embed.add_field(name=f"#{i} - {user.name}", value=f"🔢 Counted: {data.get('count', 0)}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="trivia")
async def trivia(interaction: discord.Interaction):
    with open(trivia_file) as f:
        questions = json.load(f)
    q = random.choice(questions)
    correct = q["correct"]

    buttons = [
        discord.ui.Button(label=f"{letter}: {text}", style=discord.ButtonStyle.primary, custom_id=letter)
        for letter, text in q["choices"].items()
    ]
    view = discord.ui.View()
    for b in buttons:
        view.add_item(b)

    async def callback(interact: discord.Interaction):
        choice = interact.data["custom_id"]
        if choice == correct:
            await interact.response.send_message("✅ Correct!", ephemeral=True)
        else:
            await interact.response.send_message(f"❌ Wrong! Correct was {correct}: {q['choices'][correct]}", ephemeral=True)

    for b in view.children:
        b.callback = callback

    await interaction.response.send_message(embed=discord.Embed(title="🤔 Trivia", description=q["question"]), view=view, ephemeral=True)

# Load token from environment
import os
bot.run(os.getenv("DISCORD_TOKEN"))
