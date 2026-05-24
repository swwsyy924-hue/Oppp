import discord
from discord.ext import commands
import asyncio
import random
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CATEGORY_ID = int(os.getenv("CATEGORY_ID"))
PROXY_URL = os.getenv("PROXY_URL")
REPLY_MSG = os.getenv("REPLY_MESSAGE", "🎫 شكراً لتواصلك، سيتم الرد قريباً.")
DELAY_MIN = float(os.getenv("DELAY_MIN", "1"))
DELAY_MAX = float(os.getenv("DELAY_MAX", "3"))

# إعداد الـ proxy إذا وجد
proxy = None
if PROXY_URL:
    proxy = PROXY_URL

bot = commands.Bot(command_prefix="!", self_bot=True, proxy=proxy)

@bot.event
async def on_ready():
    print(f"✅ Self-bot يعمل باسم: {bot.user.name} (ID: {bot.user.id})")
    print(f"📁 مراقبة الفئة: {CATEGORY_ID}")

@bot.event
async def on_guild_channel_create(channel):
    # تحقق من أن القناة نصية وتقع في الفئة المطلوبة
    if not isinstance(channel, discord.TextChannel):
        return
    if channel.category_id != CATEGORY_ID:
        return

    # تأخير عشوائي لتجنب الاكتشاف
    delay = random.uniform(DELAY_MIN, DELAY_MAX)
    await asyncio.sleep(delay)

    # محاولة إرسال الرسالة مع إعادة المحاولة التلقائية عند حدوث rate limit
    for attempt in range(3):
        try:
            await channel.send(REPLY_MSG)
            print(f"📨 [{channel.guild.name}] تم الإرسال في {channel.name}")
            break
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limited
                retry_after = e.retry_after
                print(f"⏳ Rate limit، انتظر {retry_after} ثانية...")
                await asyncio.sleep(retry_after + 0.5)
            else:
                print(f"❌ فشل الإرسال: {e}")
                break

@bot.event
async def on_command_error(ctx, error):
    print(f"⚠️ خطأ: {error}")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ التوكن غير موجود! ضع DISCORD_TOKEN في ملف .env")
    else:
        bot.run(TOKEN)