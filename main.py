import discord
from discord.ext import commands, tasks
from discord import app_commands
import json, os, random, math
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "db.json"
TRIVIA_FILE = "trivia.json"
CHANNEL_ID = 1366574260554043503

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

def get_user(user_id):
    if str(user_id) not in data:
        data[str(user_id)] = {
            "balance": 0,
            "count": 0,
            "inventory": [],
            "last_daily": "2000-01-01"
        }
    return data[str(user_id)]

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != CHANNEL_ID:
        return

    user = get_user(message.author.id)
    content = message.content.lower().replace(" ", "")
    try:
        user_input = eval(content, {"__builtins__": {}}, math.__dict__)
        if isinstance(user_input, (int, float)):
            if int(user_input) % 2 == 1:
                expected = user["count"] * 2 + 1
                if int(user_input) == expected:
                    user["count"] += 1
                    save_data(data)
                    await message.channel.send(embed=discord.Embed(
                        title="Counting!",
                        description=f"You said **{int(user_input)}**\nI say **{int(user_input)+1}**!",
                        color=discord.Color.green()
                    ))
                else:
                    user["count"] = 0
                    save_data(data)
                    await message.channel.send(embed=discord.Embed(
                        title="Oops!",
                        description=f"Wrong number! Restarting count.",
                        color=discord.Color.red()
                    ))
    except:
        pass
    await bot.process_commands(message)

@tree.command(name="balance")
async def balance(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    embed = discord.Embed(title="Your Balance", description=f"You have **{user['balance']}** coins!", color=0xFFD700)
    await interaction.response.send_message(embed=embed)

@tree.command(name="daily")
async def daily(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    last_claim = datetime.strptime(user["last_daily"], "%Y-%m-%d")
    if datetime.utcnow().date() > last_claim.date():
        user["balance"] += 100
        user["last_daily"] = datetime.utcnow().strftime("%Y-%m-%d")
        save_data(data)
        await interaction.response.send_message(embed=discord.Embed(
            title="Daily Reward",
            description="You got **100 coins**!",
            color=discord.Color.blue()
        ))
    else:
        await interaction.response.send_message(embed=discord.Embed(
            title="Already Claimed",
            description="Come back tomorrow!",
            color=discord.Color.red()
        ))

@tree.command(name="leaderboard")
async def leaderboard(interaction: discord.Interaction):
    leaderboard_data = sorted(data.items(), key=lambda x: x[1].get("count", 0), reverse=True)
    desc = ""
    for i, (uid, udata) in enumerate(leaderboard_data[:10]):
        user = await bot.fetch_user(int(uid))
        desc += f"**{i+1}.** {user.name} — {udata.get('count', 0)} counts\n"
    await interaction.response.send_message(embed=discord.Embed(title="Leaderboard", description=desc, color=0x00FFFF))

@tree.command(name="shop")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="Shop", description="Use `/buy item_name` to purchase!", color=0x8A2BE2)
    embed.add_field(name="cookie", value="Cost: 50 coins — *nom nom*", inline=False)
    embed.add_field(name="❓ a mystery ❓", value="Cost: 0 coins — Gives role `shop searcher`", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="buy")
@app_commands.describe(item="Item name to buy")
async def buy(interaction: discord.Interaction, item: str):
    user = get_user(interaction.user.id)
    item = item.lower()
    if item == "cookie":
        if user["balance"] >= 50:
            user["balance"] -= 50
            user["inventory"].append("cookie")
            save_data(data)
            await interaction.response.send_message(embed=discord.Embed(
                title="Yum!",
                description="You bought a **cookie**! *nom nom*",
                color=0xFF69B4
            ))
        else:
            await interaction.response.send_message("Not enough coins!")
    elif item == "❓ a mystery ❓":
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name="shop searcher")
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("You received the **shop searcher** role!")
    else:
        await interaction.response.send_message("Item not found!")

@tree.command(name="inventory")
async def inventory(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    inv = user["inventory"]
    embed = discord.Embed(title="Inventory", description="\n".join(inv) if inv else "Empty", color=0xFFFFFF)
    await interaction.response.send_message(embed=embed)

@tree.command(name="profile")
async def profile(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    embed = discord.Embed(
        title=f"{interaction.user.name}'s Profile",
        description=f"**Balance:** {user['balance']} coins\n**Counted:** {user['count']} numbers",
        color=0xADD8E6
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@tree.command(name="trivia")
async def trivia(interaction: discord.Interaction):
    with open(TRIVIA_FILE, "r") as f:
        trivia_list = json.load(f)
    q = random.choice(trivia_list)
    choices = q["choices"]

    class TriviaButton(discord.ui.Button):
        def __init__(self, label, correct):
            style = discord.ButtonStyle.gray
            super().__init__(label=label, style=style)
            self.correct = correct

        async def callback(self, i):
            correct = q["correct"]
            result = "Correct!" if self.label == correct else f"Wrong! Correct was **{correct}**: {choices[correct]}"
            if self.label == correct:
                u = get_user(i.user.id)
                if "trivia" not in u:
                    u["balance"] += 20
                    u["trivia"] = True
                    save_data(data)
            await i.response.edit_message(embed=discord.Embed(title="Trivia Result", description=result, color=0x00FF00), view=None)

    view = discord.ui.View()
    for key in choices:
        view.add_item(TriviaButton(label=key, correct=(key == q["correct"])))

    embed = discord.Embed(title="Trivia Time!", description=q["question"], color=0xFFA500)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(DISCORD_TOKEN)