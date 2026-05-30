import discord
from config import *
from control_panel import process_control_command

# إعداد البوت الحقيقي
intents = discord.Intents.default()
intents.message_content = True

bot_client = discord.Client(intents=intents)

@bot_client.event
async def on_ready():
    print(f"🤖 البوت الحقيقي يعمل باسم: {bot_client.user.name} (ID: {bot_client.user.id})")

@bot_client.event
async def on_message(message):
    # تجاهل رسائل البوت نفسه أو أي بوت آخر
    if message.author.bot:
        return

    # استمع فقط لمالك البوت (OWNER_ID) في أي مكان (DM أو قناة)
    if message.author.id == OWNER_ID:
        # استيراد السيلف-بوت من main.py لتمريره لدالة الأوامر
        from main import bot as self_bot
        await process_control_command(message, self_bot)