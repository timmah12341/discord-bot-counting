import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction, Embed, Intents
import asyncio
import os
import asyncpg
from datetime import datetime, timedelta

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL URL from Railway

pool = None  # Will be initialized later

data_initialized = False

@bot.event
async def on_ready():
    global pool, data_initialized
    if not data_initialized:
        pool = await asyncpg.create_pool(DATABASE_URL)
        await init_db()
        data_initialized = True
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)
    print(f"Logged in as {bot.user}")
    await send_wakeup_messages()


async def init_db():
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                last_daily TIMESTAMP
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                guild_id BIGINT PRIMARY KEY,
                counting_channel BIGINT
            );
        ''')


@tasks.loop(seconds=30)
async def send_wakeup_messages():
    channel_ids = [1368349957718802572, 1366574260554043503]
    for channel_id in channel_ids:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send("👋 Wake up!")


@bot.tree.command(name="setchannel", description="Set the counting channel.")
async def set_channel(interaction: Interaction):
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO settings (guild_id, counting_channel)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET counting_channel = $2;
        ''', interaction.guild.id, interaction.channel.id)
    await interaction.response.send_message("✅ Counting channel set to this channel.", ephemeral=True)


@bot.tree.command(name="daily", description="Claim your daily reward!")
async def daily(interaction: Interaction):
    user_id = interaction.user.id
    now = datetime.utcnow()

    async with pool.acquire() as conn:
        user = await conn.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)

        if user:
            last_daily = user['last_daily']
            if last_daily and now - last_daily < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_daily)
                await interaction.response.send_message(
                    f"⏳ You need to wait {remaining.seconds // 3600}h {(remaining.seconds % 3600) // 60}m more for daily."
                )
                return
            await conn.execute('''
                UPDATE users SET balance = balance + 100, last_daily = $1 WHERE user_id = $2
            ''', now, user_id)
        else:
            await conn.execute('''
                INSERT INTO users (user_id, balance, last_daily) VALUES ($1, 100, $2)
            ''', user_id, now)

    await interaction.response.send_message("💰 You claimed your daily 100 coins!")


@bot.tree.command(name="balance", description="Check your balance")
async def balance(interaction: Interaction):
    user_id = interaction.user.id
    async with pool.acquire() as conn:
        user = await conn.fetchrow('SELECT balance FROM users WHERE user_id = $1', user_id)
        if user:
            await interaction.response.send_message(f"💳 Your balance: {user['balance']} coins")
        else:
            await interaction.response.send_message("💼 You have no balance yet. Try /daily first!")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    async with pool.acquire() as conn:
        setting = await conn.fetchrow('SELECT counting_channel FROM settings WHERE guild_id = $1', message.guild.id)
        if setting and message.channel.id == setting['counting_channel']:
            try:
                num = eval(str(message.content), {"__builtins__": None}, {"pi": 3.14, "e": 2.71})
                if isinstance(num, (int, float)):
                    await message.channel.send(f"✅ You said {message.content}, result is {num*2:.2f}")
            except:
                await message.channel.send("❌ Invalid expression.")

    await bot.process_commands(message)


@bot.tree.command(name="profile", description="View your profile")
async def profile(interaction: Interaction):
    async with pool.acquire() as conn:
        user = await conn.fetchrow('SELECT balance FROM users WHERE user_id = $1', interaction.user.id)
        balance = user['balance'] if user else 0

    embed = Embed(title=f"{interaction.user.name}'s Profile", color=discord.Color.blue())
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="Balance", value=f"💰 {balance} coins")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="funny", description="Sends a funny image")
async def funny(interaction: Interaction):
    await interaction.response.send_message(
        "https://cdn.discordapp.com/attachments/1368349957718802572/1368357820507885618/image.png?ex=6817ee07&is=68169c87&hm=537c1b38a8525ba52acb5e2a3c6b36796bb3ae85e9a72124162e7011b0d68aa3&"
    )


@bot.tree.command(name="meme", description="Get a cursed meme")
async def meme(interaction: Interaction):
    await interaction.response.send_message(
        "\ud83c\udf1b \ud83c\udf1b \ud83c\udf1b 𓀂𓀇𓀉𓀍𓀠𓁀𓁂𓀱𓁉𓀿𓀪𓁶𓂧𓂮𓂫𓃹𓃳𓄜𓄲𓄓𓅆𓅢𓅼𓆀𓆾𓈙𓉒𓉼𓊪𓋜𓋒𓍲𓎳𓁀𓄲𓅢 \ud83c\udf1b AAAAAAAAAAAAAOOOOOOOOORRRRXT 01001000 0110101 01101000 01100101 0010000 01001001 0010000 01101000 01100001 01110110 01100101 00100000 01110011 01100101 01111000 00100000 01110111 01101001 01110100 01101000 00100000 01101101 00100000 01110000 01101111 01101111 01110000 01101111 01101111 00100000 01110000 01110000"
    )

bot.run(TOKEN)
