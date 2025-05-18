import discord
import asyncpg
import os
from discord.ext import commands

# Initialize bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Load environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Connect to PostgreSQL database
async def connect_db():
    conn = await asyncpg.connect(DATABASE_URL)
    return conn

# Function to check and add the 'last_number' column if missing
async def ensure_last_number_column(conn, guild_id):
    try:
        # Check if the column exists
        result = await conn.fetch(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'guild_{guild_id}_counting' AND column_name = 'last_number';
        """)

        # If the column doesn't exist, add it
        if not result:
            print(f"'last_number' column not found. Adding the column.")
            await conn.execute(f"""
                ALTER TABLE guild_{guild_id}_counting ADD COLUMN last_number INTEGER DEFAULT 0;
            """)
            print(f"'last_number' column added successfully.")
    except Exception as e:
        print(f"Error ensuring 'last_number' column: {e}")

# Command to add a counting channel to the database
@bot.command()
async def addchannel(ctx, channel: discord.TextChannel):
    try:
        conn = await connect_db()
        guild_id = ctx.guild.id
        channel_id = channel.id

        # Ensure that the last_number column exists
        await ensure_last_number_column(conn, guild_id)

        # Check if the channel already exists
        existing_channel = await conn.fetchrow(f"""
            SELECT * FROM guild_{guild_id}_counting WHERE channel_id = $1
        """, channel_id)

        if existing_channel:
            await ctx.send(f"This channel is already set for counting!")
        else:
            await conn.execute(f"""
                INSERT INTO guild_{guild_id}_counting (channel_id, last_number)
                VALUES ($1, 0)
            """, channel_id)
            await ctx.send(f"Counting has been added for channel {channel.mention}!")
    except Exception as e:
        await ctx.send(f"Error while adding the channel: {e}")
    finally:
        await conn.close()

# Command to remove a counting channel from the database
@bot.command()
async def removechannel(ctx, channel: discord.TextChannel):
    try:
        conn = await connect_db()
        guild_id = ctx.guild.id
        channel_id = channel.id

        # Remove the counting channel
        await conn.execute(f"""
            DELETE FROM guild_{guild_id}_counting WHERE channel_id = $1
        """, channel_id)
        await ctx.send(f"Counting has been removed for channel {channel.mention}!")
    except Exception as e:
        await ctx.send(f"Error while removing the channel: {e}")
    finally:
        await conn.close()

# Listen to messages for counting
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    try:
        guild_id = message.guild.id
        channel_id = message.channel.id

        conn = await connect_db()

        # Ensure that the last_number column exists
        await ensure_last_number_column(conn, guild_id)

        # Fetch the last number from the database for the current channel
        result = await conn.fetchrow(f"""
            SELECT last_number FROM guild_{guild_id}_counting WHERE channel_id = $1
        """, channel_id)

        if result:
            last_number = result['last_number']
            # Logic for counting based on the last_number
            if message.content.isdigit():
                num = int(message.content)
                if num == last_number + 1:
                    # Update the last_number in the database
                    await conn.execute(f"""
                        UPDATE guild_{guild_id}_counting
                        SET last_number = $1
                        WHERE channel_id = $2
                    """, num, channel_id)
                    await message.add_reaction('✅')
                else:
                    await message.add_reaction('❌')

        else:
            print(f"No counting data found for channel {channel_id} in guild {guild_id}.")
    except Exception as e:
        print(f"Error in on_message: {e}")
    finally:
        await conn.close()

# Add a new shop item (simplified)
@bot.command()
async def shop(ctx):
    try:
        conn = await connect_db()
        guild_id = ctx.guild.id

        # Example items, extend as needed
        items = {
            "Mystery Box": 100,
            "Rare Item": 500,
        }

        embed = discord.Embed(title="Shop", description="Buy items with your points!")
        for item, price in items.items():
            embed.add_field(name=item, value=f"Price: {price} points", inline=False)

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error fetching the shop: {e}")
    finally:
        await conn.close()

# Run the bot
bot.run(DISCORD_TOKEN)
