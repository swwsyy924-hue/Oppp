import discord
from config import *
from control_panel import process_control_command

# البوت الحقيقي (بدون Intents للتوافق مع الإصدار القديم)
bot_client = discord.Client()

@bot_client.event
async def on_ready():
    print(f"🤖 البوت الحقيقي يعمل باسم: {bot_client.user.name} (ID: {bot_client.user.id})")

@bot_client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.author.id == OWNER_ID:
        from main import bot as self_bot
        await process_control_command(message, self_bot)