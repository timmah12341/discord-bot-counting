import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import random
import math
import datetime

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

DB_FILE = 'db.json'
TRIVIA_FILE = 'trivia.json'

# Load database
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    else:
        return {}

def save_db():
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

db = load_db()

# Helper functions
def get_user_data(user_id):
    if str(user_id) not in db:
        db[str(user_id)] = {"balance": 0, "last_daily": "", "count": 1}
    return db[str(user_id)]

def get_counting_channel(guild_id):
    return db.get("channels", {}).get(str(guild_id))

def set_counting_channel(guild_id, channel_id):
    if "channels" not in db:
        db["channels"] = {}
    db["channels"][str(guild_id)] = channel_id
    save_db()

# Wake-up message
target_channels = [1368349957718802572, 1366574260554043503]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    for channel_id in target_channels:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send("👋 Wake up! Bot is now online.")

# Counting
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild_id = str(message.guild.id)
    channel_id = str(message.channel.id)
    counting_channel = get_counting_channel(guild_id)

    if counting_channel and channel_id == counting_channel:
        try:
            expression = message.content.strip()
            result = eval(expression, {"__builtins__": None, "pi": math.pi, "e": math.e, "sqrt": math.sqrt})
            result = int(result)
        except:
            return

        user_data = get_user_data(message.author.id)
        expected = user_data.get("count", 1)

        if result == expected:
            bot_reply = result + 1
            user_data["count"] = bot_reply
            save_db()
            await message.channel.send(f"✅ {bot_reply}")

# /setchannel
@tree.command(name="setchannel", description="Set this channel as the counting channel.")
async def setchannel(interaction: discord.Interaction):
    set_counting_channel(interaction.guild.id, interaction.channel.id)
    await interaction.response.send_message("✅ This channel is now set as the counting channel!", ephemeral=True)

# /balance
@tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    await interaction.response.send_message(embed=discord.Embed(
        title=f"💰 {interaction.user.name}'s Balance",
        description=f"You have **{user_data['balance']}** coins.",
        color=discord.Color.gold()
    ))

# /daily
@tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    now = datetime.datetime.utcnow().date().isoformat()
    if user_data["last_daily"] == now:
        await interaction.response.send_message("🕓 You already claimed your daily reward today!", ephemeral=True)
        return
    user_data["last_daily"] = now
    user_data["balance"] += 100
    save_db()
    await interaction.response.send_message("✅ You claimed 100 coins!")

# /funny
@tree.command(name="funny", description="Send the funny image")
async def funny(interaction: discord.Interaction):
    await interaction.response.send_message("https://cdn.discordapp.com/attachments/1368349957718802572/1368357820507885618/image.png")

# /meme
@tree.command(name="meme", description="Get cursed with meme")
async def meme(interaction: discord.Interaction):
    text = "ün ün ün 𓀂𓀇𓀉𓀍𓀠𓁀𓁂𓀱𓁉𓀿𓀪𓁶𓂧𓂮𓂫𓃹𓃳𓄜𓄲𓄓𓅆𓅢𓅼𓆀𓆾𓈙𓉒𓉼𓊪𓋜𓋒𓍲𓎳𓁀𓄲𓅢 ün ün ün ün ün ün AAAAAAAAAAAAAOOOOOOOOORRRRXT 01001000 0110101 01101000 01100101 0010000 01001001 0010000 01101000 01100001 01110110 01100101 00100000 01110011 01100101 01111000 00100000 01110111 01101001 01110100 01101000 00100000 01101101 00100000 01110000 01101111 01101111 01110000 01101111 01101111 00100000 01110000 01110000"
    await interaction.response.send_message(text)

# Shop items
shop_items = {
    "🍪 cookie": {"price": 10, "effect": "nom nom"},
    "❓ a mystery ❓": {"price": 0, "effect": "Grants a role!"}
}

# /shop
@tree.command(name="shop", description="Browse the shop")
async def shop(interaction: discord.Interaction):
    options = [
        discord.SelectOption(label=item, description=f"{info['price']} coins - {info['effect']}")
        for item, info in shop_items.items()
    ]
    select = discord.ui.Select(placeholder="Choose an item to buy", options=options)

    async def select_callback(interact):
        choice = select.values[0]
        user_data = get_user_data(interact.user.id)
        cost = shop_items[choice]["price"]
        if user_data["balance"] < cost:
            await interact.response.send_message("❌ Not enough coins!", ephemeral=True)
            return
        user_data["balance"] -= cost
        if choice == "❓ a mystery ❓":
            await interact.response.send_modal(RoleModal())
        else:
            await interact.response.send_message(f"You bought {choice}! {shop_items[choice]['effect']}")
        save_db()

    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("🛒 Shop:", view=view)

class RoleModal(discord.ui.Modal, title="Enter Role Name"):
    role = discord.ui.TextInput(label="Role Name", placeholder="Type the name of the role")

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        role_obj = discord.utils.get(guild.roles, name=self.role.value)
        if role_obj:
            await interaction.user.add_roles(role_obj)
            await interaction.response.send_message(f"✅ You got the role: {role_obj.name}!")
        else:
            await interaction.response.send_message("❌ Role not found.", ephemeral=True)

# /profile
@tree.command(name="profile", description="See your profile")
async def profile(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    embed = discord.Embed(title=f"📜 {interaction.user.name}'s Profile", color=discord.Color.blurple())
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="Balance", value=f"{user_data['balance']} coins")
    embed.add_field(name="Next Count", value=str(user_data.get("count", 1)))
    await interaction.response.send_message(embed=embed)

# /leaderboard
@tree.command(name="leaderboard", description="Top balances")
async def leaderboard(interaction: discord.Interaction):
    top = sorted(((uid, data["balance"]) for uid, data in db.items() if uid.isdigit()), key=lambda x: x[1], reverse=True)[:10]
    desc = ""
    for i, (uid, bal) in enumerate(top, 1):
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else f"User {uid}"
        desc += f"**{i}. {name}** - {bal} coins\n"
    embed = discord.Embed(title="🏆 Leaderboard", description=desc or "No data", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

# /trivia
@tree.command(name="trivia", description="Answer a trivia question")
async def trivia(interaction: discord.Interaction):
    with open(TRIVIA_FILE, 'r') as f:
        questions = json.load(f)
    q = random.choice(questions)

    class TriviaView(discord.ui.View):
        def __init__(self):
            super().__init__()
            for key, answer in q['choices'].items():
                self.add_item(discord.ui.Button(label=answer, custom_id=key))
            self.add_item(discord.ui.Button(label="Reveal Answer", style=discord.ButtonStyle.danger, custom_id="reveal"))
            self.add_item(discord.ui.Button(label="Another Question", style=discord.ButtonStyle.secondary, custom_id="another"))

        @discord.ui.button(label="Reveal Answer", custom_id="reveal")
        async def reveal_answer(self, interaction2: discord.Interaction, button):
            correct = q['choices'][q['correct']]
            await interaction2.response.send_message(f"✅ The correct answer was: **{correct}**")

        @discord.ui.button(label="Another Question", custom_id="another")
        async def another_question(self, interaction2: discord.Interaction, button):
            await trivia(interaction2)

    embed = discord.Embed(title="❓ Trivia", description=q['question'], color=discord.Color.orange())
    await interaction.response.send_message(embed=embed, view=TriviaView())

# Start bot
if __name__ == '__main__':
    bot.run(os.getenv("DISCORD_TOKEN"))
