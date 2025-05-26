
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import psycopg2
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS counting (
    guild_id BIGINT,
    channel_id BIGINT,
    last_number BIGINT DEFAULT 0,
    last_user BIGINT,
    PRIMARY KEY (guild_id, channel_id)
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT,
    guild_id BIGINT,
    balance BIGINT DEFAULT 0,
    inventory JSON DEFAULT '[]',
    last_daily TIMESTAMP,
    PRIMARY KEY (user_id, guild_id)
);
""")
conn.commit()

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild_id = message.guild.id
    channel_id = message.channel.id
    author_id = message.author.id

    cur.execute("SELECT last_number FROM counting WHERE guild_id=%s AND channel_id=%s", (guild_id, channel_id))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO counting (guild_id, channel_id, last_number, last_user) VALUES (%s, %s, %s, %s)",
                    (guild_id, channel_id, 0, None))
        conn.commit()
        return
    last_number = row[0]
    try:
        user_number = int(message.content)
    except ValueError:
        return

    expected = last_number + 2
    if user_number == expected:
        cur.execute("UPDATE counting SET last_number=%s, last_user=%s WHERE guild_id=%s AND channel_id=%s",
                    (user_number, author_id, guild_id, channel_id))
        conn.commit()
        await message.channel.send(f"✅ {message.author.mention} counted {user_number}")
    else:
        cur.execute("UPDATE counting SET last_number=0, last_user=NULL WHERE guild_id=%s AND channel_id=%s",
                    (guild_id, channel_id))
        conn.commit()
        await message.channel.send(f"❌ Wrong number! Count reset to 0.")

@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    now = datetime.utcnow()
    cur.execute("SELECT balance, last_daily FROM users WHERE user_id=%s AND guild_id=%s", (user_id, guild_id))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (user_id, guild_id, balance, last_daily) VALUES (%s, %s, %s, %s)",
                    (user_id, guild_id, 100, now))
        conn.commit()
        await interaction.response.send_message("✅ Daily claimed! You received 100 coins.")
        return

    balance, last_daily = row
    if last_daily and now - last_daily < timedelta(hours=24):
        await interaction.response.send_message("🕒 You already claimed your daily reward.")
        return

    cur.execute("UPDATE users SET balance = balance + 100, last_daily = %s WHERE user_id=%s AND guild_id=%s",
                (now, user_id, guild_id))
    conn.commit()
    await interaction.response.send_message("✅ Daily claimed! You received 100 coins.")

@tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    cur.execute("SELECT balance FROM users WHERE user_id=%s AND guild_id=%s", (user_id, guild_id))
    row = cur.fetchone()
    if not row:
        balance = 0
        cur.execute("INSERT INTO users (user_id, guild_id, balance) VALUES (%s, %s, %s)",
                    (user_id, guild_id, 0))
        conn.commit()
    else:
        balance = row[0]
    await interaction.response.send_message(f"💰 You have {balance} coins.")

items = {
    "cookie": {"price": 50, "effect": "You ate a cookie! 🍪"},
    "mystery": {"price": 0, "effect": "❓ You found a strange artifact..."}
}

class BuyMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=item, description=f"{data['price']} coins")
            for item, data in items.items()
        ]
        super().__init__(placeholder="Choose an item to buy", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        item = self.values[0]
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        cur.execute("SELECT balance, inventory FROM users WHERE user_id=%s AND guild_id=%s", (user_id, guild_id))
        row = cur.fetchone()
        if not row:
            await interaction.response.send_message("❌ You have no coins.")
            return

        balance, inventory = row
        price = items[item]["price"]
        if balance < price:
            await interaction.response.send_message("❌ Not enough coins.")
            return

        inventory = json.loads(inventory or "[]")
        inventory.append(item)
        cur.execute("UPDATE users SET balance=balance-%s, inventory=%s WHERE user_id=%s AND guild_id=%s",
                    (price, json.dumps(inventory), user_id, guild_id))
        conn.commit()
        await interaction.response.send_message(f"✅ You bought a {item}!")

class BuyView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(BuyMenu())

@tree.command(name="buy", description="Buy items from the shop")
async def buy(interaction: discord.Interaction):
    await interaction.response.send_message("🛒 Select an item to buy:", view=BuyView())

@tree.command(name="inventory", description="See your inventory")
async def inventory(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    cur.execute("SELECT inventory FROM users WHERE user_id=%s AND guild_id=%s", (user_id, guild_id))
    row = cur.fetchone()
    if not row or not row[0]:
        await interaction.response.send_message("🎒 Your inventory is empty.")
        return
    inv = json.loads(row[0])
    if not inv:
        await interaction.response.send_message("🎒 Your inventory is empty.")
        return
    await interaction.response.send_message("🎒 Your inventory: " + ", ".join(inv))

@tree.command(name="use", description="Use an item from your inventory")
@app_commands.describe(item="The name of the item to use")
async def use(interaction: discord.Interaction, item: str):
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    cur.execute("SELECT inventory FROM users WHERE user_id=%s AND guild_id=%s", (user_id, guild_id))
    row = cur.fetchone()
    if not row or not row[0]:
        await interaction.response.send_message("❌ You have no items.")
        return
    inv = json.loads(row[0])
    if item not in inv:
        await interaction.response.send_message("❌ You don't have that item.")
        return
    inv.remove(item)
    cur.execute("UPDATE users SET inventory=%s WHERE user_id=%s AND guild_id=%s",
                (json.dumps(inv), user_id, guild_id))
    conn.commit()
    effect = items[item]["effect"]
    await interaction.response.send_message(f"🎉 {effect}")

bot.run(TOKEN)

