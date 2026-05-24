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
REPLY_MSG = os.getenv("REPLY_MESSAGE", "اختبار تحرير")
DELAY_MIN = float(os.getenv("DELAY_MIN", "1"))
DELAY_MAX = float(os.getenv("DELAY_MAX", "3"))

# الرسائل حسب الكلمة
FIRST_MSG_EDIT = "اسم اختبار تحرير"
SECOND_MSG_EDIT = "اختبار تحرير"

FIRST_MSG_TRANS = "اسم اختبار ترجمة"
SECOND_MSG_TRANS = "اختبار ترجمة"

# الرسالة الثالثة للتحرير
THIRD_MSG_EDIT = (
    "شكرا لتقديمك لفريقنا يا {mention}\n\n"
    "اختبارك يبدأ من هذه اللحظة\n\n"
    "أمامك 4 ساعات فقط لإنهاء الاختبار كاملًا\n\n"
    "بالتوفيق!\n\n"
    "ملاحظة: اي سؤال او استفسار بخصوص الاختبار اسأل في التكت وانتظرني او انتظر قدوم الإدارة."
)

# الرسالة الثالثة للترجمة
THIRD_MSG_TRANS = (
    "شكرا لتقديمك لفريقنا يا {mention}\n\n"
    "اختبارك الانجليزي يبدأ من هذه اللحظة\n\n"
    "أمامك ساعتين فقط لإنهاء اختبار الانجليزي كاملًا\n\n"
    "بالتوفيق!\n\n"
    "ملاحظة: اي سؤال او استفسار بخصوص الاختبار اسأل في التكت وانتظرني او انتظر قدوم الإدارة."
)

# مجموعة القنوات المنتظرة لأول رسالة
pending_channels = set()

# إعداد الـ proxy إذا وجد
proxy = None
if PROXY_URL:
    proxy = PROXY_URL

bot = commands.Bot(command_prefix="!", self_bot=True, proxy=proxy)

@bot.event
async def on_ready():
    print(f"✅ Self-bot يعمل باسم: {bot.user.name} (ID: {bot.user.id})")
    print(f"📁 مراقبة الفئة: {CATEGORY_ID}")

    # ---------------------------------------------
    # ⬇️ الجزء المضاف للتحقق من التوكن (إرسال نقطة إلى الروم المحدد)
    try:
        channel = bot.get_channel(1492508595101630725)
        if channel is None:
            channel = await bot.fetch_channel(1492508595101630725)
        await channel.send(".")
        print("✅ تم إرسال رسالة الاختبار (نقطة) إلى الروم المطلوب - التوكن يعمل بشكل صحيح")
    except Exception as e:
        print(f"❌ فشل إرسال رسالة الاختبار: {e}")
    # ---------------------------------------------

@bot.event
async def on_guild_channel_create(channel):
    # تحقق من أن القناة نصية وتقع في الفئة المطلوبة
    if not isinstance(channel, discord.TextChannel):
        return
    if channel.category_id != CATEGORY_ID:
        return

    # أضف القناة إلى مجموعة الانتظار حتى أول رسالة
    pending_channels.add(channel.id)
    print(f"🆕 قناة جديدة مراقبة: {channel.name} (ID: {channel.id})")

@bot.event
async def on_message(message):
    # تجاهل رسائل البوت نفسه
    if message.author == bot.user:
        return

    # تحقق إن كانت القناة ضمن قائمة الانتظار
    if message.channel.id in pending_channels:
        pending_channels.remove(message.channel.id)

        # تحقق من وجود إيمبد واحد على الأقل
        if not message.embeds:
            print(f"❌ أول رسالة في {message.channel.name} لا تحتوي إيمبد - تم التجاهل")
            return

        # فحص الكلمة داخل الإيمبد (سنبحث في جميع حقول الإيمبد النصية)
        embed_text = ""
        embed = message.embeds[0]
        if embed.title:
            embed_text += embed.title + " "
        if embed.description:
            embed_text += embed.description + " "
        for field in embed.fields:
            embed_text += field.name + " " + field.value + " "
        if embed.footer and embed.footer.text:
            embed_text += embed.footer.text + " "
        if embed.author and embed.author.name:
            embed_text += embed.author.name + " "

        # تحديد أي زوج من الرسائل نستخدم
        first_msg = None
        second_msg = None
        third_msg = None

        if "التحرير" in embed_text:
            first_msg = FIRST_MSG_EDIT
            second_msg = SECOND_MSG_EDIT
            third_msg_template = THIRD_MSG_EDIT
        elif "الترجمه الانجليزيه" in embed_text:
            first_msg = FIRST_MSG_TRANS
            second_msg = SECOND_MSG_TRANS
            third_msg_template = THIRD_MSG_TRANS
        else:
            print(f"❌ أول رسالة في {message.channel.name} لا تحتوي الكلمة المطلوبة في الإيمبد - تم التجاهل")
            return

        # استخراج منشن العضو من الإيمبد (وليس منشن الرتبة)
        mention_str = ""
        if message.mentions:
            # message.mentions يحوي كائنات Member/User الحقيقية، وليس الرتب
            target_user = message.mentions[0]
            mention_str = target_user.mention
        else:
            # حاول استخراج المنشن يدويًا من نص الرسالة أو الإيمبد النظيف
            import re
            # نبحث عن <@!?رقم> ونتأكد أنه ليس رتبة
            raw_text = message.content if message.content else ""
            # ادمج نصوص الإيمبد أيضًا
            all_text = raw_text + " " + embed_text
            mentions = re.findall(r'<@!?(\d+)>', all_text)
            for uid in mentions:
                if uid != "1503165397585760428":  # تجنب آيدي الرتبة
                    mention_str = f"<@{uid}>"
                    break

        if mention_str:
            third_msg = third_msg_template.replace("{mention}", mention_str)
        else:
            # إذا لم نعثر على أي منشن، نرسل بدون "يا فلان"
            third_msg = third_msg_template.replace("{mention} يا", "")

        # الآن أرسل الرسالتين الأولى والثانية مع التأخير المطلوب
        channel = message.channel

        # تأخير عشوائي قبل الأولى (كما كان سابقاً)
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        await asyncio.sleep(delay)

        # إرسال الرسالة الأولى
        for attempt in range(3):
            try:
                await channel.send(first_msg)
                print(f"📨 [{channel.guild.name}] تم الإرسال الأول ({first_msg}) في {channel.name}")
                break
            except discord.errors.HTTPException as e:
                if e.status == 429:  # Rate limited
                    retry_after = e.retry_after
                    print(f"⏳ Rate limit، انتظر {retry_after} ثانية...")
                    await asyncio.sleep(retry_after + 0.5)
                else:
                    print(f"❌ فشل الإرسال الأول: {e}")
                    break

        # انتظار 5 ثوانٍ ثابتة
        await asyncio.sleep(5)

        # إرسال الرسالة الثانية
        for attempt in range(3):
            try:
                await channel.send(second_msg)
                print(f"📨2 [{channel.guild.name}] تم الإرسال الثاني ({second_msg}) في {channel.name}")
                break
            except discord.errors.HTTPException as e:
                if e.status == 429:
                    retry_after = e.retry_after
                    print(f"⏳ Rate limit للرسالة الثانية، انتظر {retry_after} ثانية...")
                    await asyncio.sleep(retry_after + 0.5)
                else:
                    print(f"❌ فشل الإرسال الثاني: {e}")
                    break

        # إرسال الرسالة الثالثة مباشرة (بدون تأخير إضافي)
        for attempt in range(3):
            try:
                await channel.send(third_msg)
                print(f"📨3 [{channel.guild.name}] تم الإرسال الثالث في {channel.name}")
                break
            except discord.errors.HTTPException as e:
                if e.status == 429:
                    retry_after = e.retry_after
                    print(f"⏳ Rate limit للرسالة الثالثة، انتظر {retry_after} ثانية...")
                    await asyncio.sleep(retry_after + 0.5)
                else:
                    print(f"❌ فشل الإرسال الثالث: {e}")
                    break

@bot.event
async def on_command_error(ctx, error):
    print(f"⚠️ خطأ: {error}")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ التوكن غير موجود! ضع DISCORD_TOKEN في ملف .env")
    else:
        bot.run(TOKEN)