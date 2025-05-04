import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import asyncpg

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.environ['DISCORD_TOKEN']
DATABASE_URL = os.environ['DATABASE_URL']
wake_channels = [1368349957718802572, 1366574260554043503]
counting_channel_id = None
pool = None

@bot.event
async def on_ready():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    await setup_db()
    await bot.tree.sync()
    for ch_id in wake_channels:
        ch = bot.get_channel(ch_id)
        if ch:
            await ch.send("🤖 Bot is now awake and ready!")

async def setup_db():
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                balance INT DEFAULT 0,
                last_daily TIMESTAMP,
                count INT DEFAULT 0
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS trivia (
                question TEXT,
                choice_a TEXT,
                choice_b TEXT,
                choice_c TEXT,
                correct CHAR(1)
            );
        ''')

async def get_config(key):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT value FROM config WHERE key = $1", key)
        return row['value'] if row else None

async def set_config(key, value):
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO config (key, value) VALUES ($1, $2)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        ''', key, value)

@bot.tree.command(name="setchannel", description="Set this channel as the counting channel.")
async def set_channel(interaction: discord.Interaction):
    await set_config("counting_channel", str(interaction.channel.id))
    await interaction.response.send_message("✅ This channel is now set as the counting channel.", ephemeral=True)

@bot.tree.command(name="balance", description="Check your balance.")
async def balance(interaction: discord.Interaction):
    async with pool.acquire() as conn:
        user_id = interaction.user.id
        row = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)
        balance = row['balance'] if row else 0
        await interaction.response.send_message(embed=discord.Embed(title="💰 Your Balance", description=f"You have {balance} coins!", color=0x00ff00))

@bot.tree.command(name="daily", description="Claim your daily reward.")
async def daily(interaction: discord.Interaction):
    import datetime
    now = datetime.datetime.utcnow()
    async with pool.acquire() as conn:
        user_id = interaction.user.id
        row = await conn.fetchrow("SELECT last_daily, balance FROM users WHERE user_id = $1", user_id)
        if row:
            last_claim = row['last_daily']
            if last_claim and (now - last_claim).total_seconds() < 86400:
                await interaction.response.send_message("🕒 You have already claimed your daily reward today!", ephemeral=True)
                return
            await conn.execute("UPDATE users SET last_daily = $1, balance = balance + 100 WHERE user_id = $2", now, user_id)
        else:
            await conn.execute("INSERT INTO users (user_id, last_daily, balance) VALUES ($1, $2, 100)", user_id, now)
        await interaction.response.send_message("🎉 You've received 100 coins for your daily login!")

@bot.tree.command(name="profile", description="Show your profile.")
async def profile(interaction: discord.Interaction):
    async with pool.acquire() as conn:
        user_id = interaction.user.id
        row = await conn.fetchrow("SELECT balance, count FROM users WHERE user_id = $1", user_id)
        bal = row['balance'] if row else 0
        cnt = row['count'] if row else 0
        embed = discord.Embed(title=f"{interaction.user.name}'s Profile", color=0x7289DA)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="💰 Balance", value=f"{bal}", inline=True)
        embed.add_field(name="🔢 Counted", value=f"{cnt}", inline=True)
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="meme", description="Get a mysterious meme.")
async def meme(interaction: discord.Interaction):
    await interaction.response.send_message("🧠 You've been visited by the ancient meme of wisdom. Don't scroll without saying 👁️👄👁️")

@bot.tree.command(name="funny", description="Show a funny image.")
async def funny(interaction: discord.Interaction):
    await interaction.response.send_message("https://cdn.discordapp.com/attachments/111111111111111111/222222222222222222/funny.png")

@bot.tree.command(name="leaderboard", description="See the top users.")
async def leaderboard(interaction: discord.Interaction):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
        desc = "\n".join([f"<@{r['user_id']}> — {r['balance']} coins" for r in rows])
        await interaction.response.send_message(embed=discord.Embed(title="🏆 Leaderboard", description=desc))

@bot.tree.command(name="shop", description="Browse the shop.")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 Shop", description="Here are the items you can buy:\n- 🍪 Cookie (50 coins)\n- ❓ a mystery ❓ (FREE role)", color=0xffa500)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="trivia", description="Answer a trivia question.")
async def trivia(interaction: discord.Interaction):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM trivia ORDER BY RANDOM() LIMIT 1")
        if not row:
            await interaction.response.send_message("❌ No trivia questions available.")
            return

        question = row['question']
        choices = {'A': row['choice_a'], 'B': row['choice_b'], 'C': row['choice_c']}
        correct = row['correct']
        view = discord.ui.View()

        for key, val in choices.items():
            async def button_callback(interaction, k=key):
                msg = "✅ Correct!" if k == correct else f"❌ Wrong! Correct answer was **{correct}**"
                await interaction.response.edit_message(content=msg, view=None)

            btn = discord.ui.Button(label=f"{key}: {val}", style=discord.ButtonStyle.primary)
            btn.callback = button_callback
            view.add_item(btn)

        await interaction.response.send_message(f"❓ {question}", view=view)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    global counting_channel_id
    if not counting_channel_id:
        raw = await get_config("counting_channel")
        if raw:
            counting_channel_id = int(raw)

    if message.channel.id != counting_channel_id:
        return

    try:
        num = eval(message.content)
        if isinstance(num, (int, float)) and num % 2 == 1:
            even = int(num) + 1
            async with pool.acquire() as conn:
                await conn.execute("INSERT INTO users (user_id, count) VALUES ($1, 1) ON CONFLICT (user_id) DO UPDATE SET count = users.count + 1", message.author.id)
            await message.channel.send(f"{even}")
    except:
        pass

bot.run(TOKEN)
