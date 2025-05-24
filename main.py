import os
import discord
import asyncpg
import json
import random
import datetime
from discord.ext import commands, tasks
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

db = None
trivia_data = []

async def init_db():
    global db
    db = await asyncpg.connect(DATABASE_URL)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT,
            guild_id BIGINT,
            balance INTEGER DEFAULT 0,
            last_daily TIMESTAMP,
            PRIMARY KEY (user_id, guild_id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS counting (
            guild_id BIGINT,
            channel_id BIGINT,
            last_number INTEGER,
            PRIMARY KEY (guild_id, channel_id)
        )
    """)

@bot.event
async def on_ready():
    await init_db()
    with open("trivia.json") as f:
        global trivia_data
        trivia_data = json.load(f)
    await tree.sync()
    print(f"Logged in as {bot.user}")

# ===== Counting =====

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    record = await db.fetchrow("SELECT last_number FROM counting WHERE guild_id=$1 AND channel_id=$2", message.guild.id, message.channel.id)
    if not record:
        return

    try:
        number = int(eval(message.content))
    except:
        return

    last_number = record["last_number"]
    expected = 2 if last_number is None else last_number + 2

    if number == expected:
        await db.execute("UPDATE counting SET last_number=$1 WHERE guild_id=$2 AND channel_id=$3", number, message.guild.id, message.channel.id)
    else:
        await db.execute("UPDATE counting SET last_number=NULL WHERE guild_id=$1 AND channel_id=$2", message.guild.id, message.channel.id)
        await message.channel.send("**Wrong number! Count reset.**")

# ===== Commands =====

@tree.command(name="addchannel", description="Enable counting in this channel")
async def addchannel(interaction: discord.Interaction):
    await db.execute("INSERT INTO counting (guild_id, channel_id, last_number) VALUES ($1, $2, NULL) ON CONFLICT DO NOTHING", interaction.guild.id, interaction.channel.id)
    await interaction.response.send_message("Counting enabled in this channel!", ephemeral=True)

@tree.command(name="removechannel", description="Disable counting in this channel")
async def removechannel(interaction: discord.Interaction):
    await db.execute("DELETE FROM counting WHERE guild_id=$1 AND channel_id=$2", interaction.guild.id, interaction.channel.id)
    await interaction.response.send_message("Counting disabled in this channel.", ephemeral=True)

@tree.command(name="daily", description="Claim your daily coins!")
async def daily(interaction: discord.Interaction):
    now = datetime.datetime.utcnow()
    user = await db.fetchrow("SELECT balance, last_daily FROM users WHERE user_id=$1 AND guild_id=$2", interaction.user.id, interaction.guild.id)

    if user and user["last_daily"]:
        delta = now - user["last_daily"]
        if delta.total_seconds() < 86400:
            remaining = 86400 - delta.total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            return await interaction.response.send_message(f"Try again in {hours}h {minutes}m.", ephemeral=True)

    amount = random.randint(50, 150)
    await db.execute("""
        INSERT INTO users (user_id, guild_id, balance, last_daily)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (user_id, guild_id) DO UPDATE
        SET balance = users.balance + $3, last_daily = $4
    """, interaction.user.id, interaction.guild.id, amount, now)

    await interaction.response.send_message(f"You got {amount} coins!", ephemeral=True)

@tree.command(name="balance", description="Check your balance.")
async def balance(interaction: discord.Interaction):
    user = await db.fetchrow("SELECT balance FROM users WHERE user_id=$1 AND guild_id=$2", interaction.user.id, interaction.guild.id)
    bal = user["balance"] if user else 0
    await interaction.response.send_message(f"Balance: {bal} coins.", ephemeral=True)

@tree.command(name="leaderboard", description="Top balances!")
async def leaderboard(interaction: discord.Interaction):
    rows = await db.fetch("SELECT user_id, balance FROM users WHERE guild_id=$1 ORDER BY balance DESC LIMIT 10", interaction.guild.id)
    text = "\n".join([f"<@{r['user_id']}>: {r['balance']} coins" for r in rows])
    await interaction.response.send_message(f"**Leaderboard**:\n{text or 'Nobody yet!'}")

@tree.command(name="profile", description="View your profile")
async def profile(interaction: discord.Interaction):
    user = await db.fetchrow("SELECT balance FROM users WHERE user_id=$1 AND guild_id=$2", interaction.user.id, interaction.guild.id)
    balance = user["balance"] if user else 0
    embed = discord.Embed(title=f"{interaction.user.name}'s Profile", color=discord.Color.blue())
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="Balance", value=f"{balance} coins", inline=False)
    await interaction.response.send_message(embed=embed)

# ===== Shop =====

shop_items = {
    "cookie": {"price": 50, "desc": "A tasty cookie! Nom nom."},
    "❓ a mystery ❓": {"price": 0, "desc": "Does... something."}
}

@tree.command(name="shop", description="Open the shop")
async def shop(interaction: discord.Interaction):
    options = [discord.SelectOption(label=name, description=data["desc"]) for name, data in shop_items.items()]
    select = discord.ui.Select(placeholder="Choose an item to buy", options=options)

    async def select_callback(i: discord.Interaction):
        item = select.values[0]
        price = shop_items[item]["price"]
        user = await db.fetchrow("SELECT balance FROM users WHERE user_id=$1 AND guild_id=$2", i.user.id, i.guild.id)
        balance = user["balance"] if user else 0
        if balance < price:
            await i.response.send_message("Not enough coins!", ephemeral=True)
            return
        await db.execute("UPDATE users SET balance = balance - $1 WHERE user_id=$2 AND guild_id=$3", price, i.user.id, i.guild.id)
        await i.response.send_message(f"You bought {item}! {shop_items[item]['desc']}", ephemeral=True)

    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Welcome to the shop!", view=view, ephemeral=True)

# ===== Trivia =====

@tree.command(name="trivia", description="Answer a trivia question!")
async def trivia(interaction: discord.Interaction):
    q = random.choice(trivia_data)
    correct = q["correct"]
    buttons = []
    for key, value in q["choices"].items():
        button = discord.ui.Button(label=value, style=discord.ButtonStyle.gray)

        async def callback(i: discord.Interaction, key=key):
            if key == correct:
                await i.response.send_message("Correct!", ephemeral=True)
            else:
                await i.response.send_message(f"Wrong! The correct answer was **{q['choices'][correct]}**", ephemeral=True)

        button.callback = callback
        buttons.append(button)

    view = discord.ui.View()
    for b in buttons:
        view.add_item(b)
    await interaction.response.send_message(q["question"], view=view, ephemeral=True)

bot.run(TOKEN)