import discord
from discord.ext import commands
import asyncio
import random
import os
import re
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CATEGORY_ID = int(os.getenv("CATEGORY_ID"))
PROXY_URL = os.getenv("PROXY_URL")
REPLY_MSG = os.getenv("REPLY_MESSAGE", "اختبار تحرير")
DELAY_MIN = float(os.getenv("DELAY_MIN", "1"))
DELAY_MAX = float(os.getenv("DELAY_MAX", "3"))

# ═══════════════════════════════════════
# 🔧 أوضاع التقديم (True = مفتوح, False = مغلق)
# ═══════════════════════════════════════
EDIT_OPEN = True
TRANSLATE_OPEN = False
WHITENING_OPEN = False

# مدد الاختبارات بالثواني
EDIT_TEST_DURATION_SEC = 4 * 3600       # 4 ساعات
TRANSLATE_TEST_DURATION_SEC = 2 * 3600  # ساعتان
WHITENING_TEST_DURATION_SEC = 3 * 3600  # 3 ساعات

# الرسائل حسب الكلمة
FIRST_MSG_EDIT = "اسم اختبار تحرير"
SECOND_MSG_EDIT = "اختبار تحرير"

FIRST_MSG_TRANS = "اسم اختبار ترجمة"
SECOND_MSG_TRANS = "اختبار ترجمة"

FIRST_MSG_WHITENING = "اسم اختبار تبييض"
SECOND_MSG_WHITENING = "اختبار تبييض"

# الرسالة الثالثة للتحرير (محسّنة بالماركدون)
THIRD_MSG_EDIT = (
    "# شكراً لتقديمك يا {mention}\n\n"
    "**اختبارك يبدأ من هذه اللحظة**\n\n"
    "> أمامك **4 ساعات** فقط لإنهاء الاختبار كاملاً\n\n"
    "- يرجى قراءة التعليمات جيداً قبل البدء\n"
    "- التسليم عبر رابط **Google Drive** فقط\n\n"
    "**بالتوفيق!**\n\n"
    "-# ملاحظة: أي سؤال أو استفسار بخصوص الاختبار اسأل في التكت وانتظرني أو انتظر قدوم الإدارة"
)

# الرسالة الثالثة للترجمة (محسّنة بالماركدون)
THIRD_MSG_TRANS = (
    "# شكراً لتقديمك يا {mention}\n\n"
    "**اختبارك الانجليزي يبدأ من هذه اللحظة**\n\n"
    "> أمامك **ساعتان** فقط لإنهاء الاختبار كاملاً\n\n"
    "- يرجى قراءة التعليمات جيداً قبل البدء\n"
    "- التسليم عبر رابط **Google Docs** فقط\n\n"
    "**بالتوفيق!**\n\n"
    "-# ملاحظة: أي سؤال أو استفسار بخصوص الاختبار اسأل في التكت وانتظرني أو انتظر قدوم الإدارة"
)

# الرسالة الثالثة للتبييض (محسّنة بالماركدون)
THIRD_MSG_WHITENING = (
    "# شكراً لتقديمك يا {mention}\n\n"
    "**اختبارك يبدأ من هذه اللحظة**\n\n"
    "> أمامك **3 ساعات** فقط لإنهاء اختبار التبييض كاملاً\n\n"
    "- يرجى قراءة التعليمات جيداً قبل البدء\n"
    "- صور الاختبار **4**، قم بعمل **2** منهم فقط\n"
    "- التسليم عبر رابط **Google Drive** فقط\n\n"
    "**بالتوفيق!**\n\n"
    "-# ملاحظة: أي سؤال أو استفسار بخصوص الاختبار اسأل في التكت وانتظرني أو انتظر قدوم الإدارة"
)

# رسائل الإغلاق (عند إغلاق التقديم)
CLOSED_MSG_EDIT = (
    "# نعتذر منك 🙏\n\n"
    "**تقديم اختبار التحرير مغلق حالياً**\n\n"
    "> نرجو متابعة شات الإنضمام لمعرفة الاخبار الجديدة.\n\n"
    "إذا كان لديك أي استفسار،اترك رسالتك هنا ليتم الرد عليها من قبل الإدارة.\n"
    "-# شكراً لتفهمك"
)

CLOSED_MSG_TRANS = (
    "# نعتذر منك 🙏\n\n"
    "**تقديم اختبار الترجمة مغلق حالياً**\n\n"
    "> نرجو متابعة شات الإنضمام لمعرفة الاخبار الجديدة.\n\n"
    "إذا كان لديك أي استفسار،اترك رسالتك هنا ليتم الرد عليها من قبل الإدارة.\n"
    "-# شكراً لتفهمك"
)

CLOSED_MSG_WHITENING = (
    "# نعتذر منك 🙏\n\n"
    "**تقديم اختبار التبييض مغلق حالياً**\n\n"
    "> نرجو متابعة شات الإنضمام لمعرفة الاخبار الجديدة.\n\n"
    "إذا كان لديك أي استفسار،اترك رسالتك هنا ليتم الرد عليها من قبل الإدارة.\n"
    "-# شكراً لتفهمك"
)

# رسالة الفشل (عند انتهاء الوقت دون إرسال الرابط)
FAIL_MSG = (
    "{mention} انتهى وقت الاختبار للأسف 🤷‍♂️.\n"
    "لقد فشلت في الاختبار. سيتم إغلاق التكت بعد ساعة."
)

# مجموعة القنوات المنتظرة لأول رسالة
pending_channels = set()

# قاموس لتتبع القنوات النشطة ونوع الاختبار ومعلومات المقدم
active_tests = {}          # channel_id -> "edit" أو "translate" أو "whitening"
applicant_info = {}        # channel_id -> {"id": int, "mention": str}
applicant_spoke = set()    # قنوات أرسل فيها المقدم رسالة واحدة على الأقل
link_submitted = set()     # قنوات أرسل فيها المقدم رابط الاختبار

# قاموس لتخزين مهام الإغلاق التلقائي
close_tasks = {}

# قاموس لتخزين مهام التذكير الدورية
reminder_tasks = {}

# إعداد الـ proxy إذا وجد
proxy = None
if PROXY_URL:
    proxy = PROXY_URL

bot = commands.Bot(command_prefix="!", self_bot=True, proxy=proxy)

# دالة مساعدة: إرسال رسالة مع محاكاة الكتابة البشرية (عشوائية)
async def human_send(channel, content, min_typing=1.0, max_typing=3.0):
    """يُظهر حالة الكتابة لمدة عشوائية ثم يرسل الرسالة"""
    typing_duration = random.uniform(min_typing, max_typing)
    async with channel.typing():
        await asyncio.sleep(typing_duration)
    await channel.send(content)

async def monitor_test(channel, test_type, applicant_id, applicant_mention):
    """تراقب تقدم الاختبار وتقرر الإغلاق أو إرسال رسالة الفشل"""
    if test_type == "edit":
        duration = EDIT_TEST_DURATION_SEC
    elif test_type == "translate":
        duration = TRANSLATE_TEST_DURATION_SEC
    else:
        duration = WHITENING_TEST_DURATION_SEC

    await asyncio.sleep(duration)

    # إذا أُرسل رابط الاختبار خلال الفترة المسموحة → ألغِ المهمة بهدوء
    if channel.id in link_submitted:
        print(f"✅ تم تسليم الاختبار في {channel.name} - لن يتم الإغلاق التلقائي")
        return

    try:
        # إعادة جلب القناة
        try:
            channel = await bot.fetch_channel(channel.id)
        except discord.NotFound:
            print(f"❌ القناة لم تعد موجودة، تخطي")
            return

        # الحالة 1: المقدم لم يرسل أي رسالة نهائيًا
        if channel.id not in applicant_spoke:
            print(f"⏰ لم يرسل المقدم أي رسالة في {channel.name} - إغلاق مباشر")
            await close_ticket(channel)
            return

        # الحالة 2: المقدم أرسل رسائل لكن لم يرسل رابط الاختبار
        if channel.id not in link_submitted:
            print(f"⏰ انتهى الوقت دون رابط في {channel.name} - إرسال رسالة الفشل")
            fail_text = FAIL_MSG.replace("{mention}", applicant_mention)
            await channel.send(fail_text)
            await asyncio.sleep(3600)  # انتظر ساعة
            await close_ticket(channel)
            return

    except Exception as e:
        print(f"❌ خطأ في monitor_test: {e}")

async def close_ticket(channel):
    """تغلق التكت بكتابة 'اغلاق' ثم الضغط على 'تأكيد'"""
    try:
        await channel.send("اغلاق")
        print(f"💬 تم إرسال 'اغلاق' في {channel.name}")

        def check(m):
            if m.channel.id != channel.id:
                return False
            if not m.author.bot:
                return False
            if not m.components:
                return False
            for row in m.components:
                for c in row.children:
                    if isinstance(c, discord.Button) and "تأكيد" in c.label:
                        return True
            return False

        confirm_msg = None
        for _ in range(10):
            try:
                confirm_msg = await bot.wait_for('message', timeout=2.0, check=check)
                break
            except asyncio.TimeoutError:
                continue

        if confirm_msg is None:
            print(f"❌ لم تظهر رسالة تأكيد في {channel.name}")
            return

        for row in confirm_msg.components:
            for c in row.children:
                if isinstance(c, discord.Button) and "تأكيد" in c.label:
                    await c.click()
                    print(f"✅ تم الضغط على '{c.label}' وإغلاق الروم {channel.name}")
                    return

        print(f"❌ لم يتم العثور على زر تأكيد")

    except Exception as e:
        print(f"❌ فشل إغلاق الروم {channel.name}: {e}")

async def periodic_reminder(channel_id, applicant_mention, duration, test_type):
    """يرسل تذكيراً عند منتصف الوقت ثم كل ساعة للمُقدّم الذي لم يكتب أي شيء بعد"""
    # انتظر حتى منتصف المدة
    half_duration = duration / 2
    await asyncio.sleep(half_duration)

    # توقف إذا انتهى الاختبار أو أرسل المقدم شيئاً
    if channel_id in applicant_spoke or channel_id in link_submitted:
        return

    # حساب الوقت المتبقي بعد المنتصف
    remaining = duration - half_duration
    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    if hours > 0:
        time_str = f"{hours} ساعة"
        if minutes > 0:
            time_str += f" و {minutes} دقيقة"
    else:
        time_str = f"{minutes} دقيقة"

    # تذكير أنيق بمنتصف الوقت
    half_reminder = (
        f"# تنبيه {applicant_mention}\n\n"
        f"**تبقت لك {time_str} على انتهاء الاختبار**\n\n"
        "> يرجى الإسراع بتسليم الاختبار قبل انتهاء الوقت.\n\n"
        "بالتوفيق!"
    )
    try:
        channel = await bot.fetch_channel(channel_id)
        await channel.send(half_reminder)
        print(f"🔔 تذكير منتصف الوقت في {channel.name}")
    except Exception as e:
        print(f"❌ فشل إرسال تذكير المنتصف: {e}")

    # الآن ابدأ التذكيرات الدورية كل ساعة
    elapsed = half_duration
    interval = 3600  # ثانية
    while elapsed < duration:
        await asyncio.sleep(interval)
        elapsed += interval

        if channel_id in applicant_spoke or channel_id in link_submitted:
            break

        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            break

        remaining = duration - elapsed
        if remaining <= 0:
            break
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        if hours > 0:
            time_str = f"{hours} ساعة"
            if minutes > 0:
                time_str += f" و {minutes} دقيقة"
        else:
            time_str = f"{minutes} دقيقة"

        reminder = (
            f"# تنبيه {applicant_mention}\n\n"
            f"**تبقت لك {time_str} على انتهاء الاختبار**\n\n"
            "> يرجى الإسراع بتسليم الاختبار قبل انتهاء الوقت.\n\n"
            "بالتوفيق!"
        )
        try:
            await channel.send(reminder)
            print(f"🔔 تذكير دوري في {channel.name}")
        except Exception as e:
            print(f"❌ فشل إرسال التذكير: {e}")

@bot.event
async def on_ready():
    print(f"✅ Self-bot يعمل باسم: {bot.user.name} (ID: {bot.user.id})")
    print(f"📁 مراقبة الفئة: {CATEGORY_ID}")

    try:
        channel = bot.get_channel(1492508595101630725)
        if channel is None:
            channel = await bot.fetch_channel(1492508595101630725)
        await channel.send(".")
        print("✅ تم إرسال رسالة الاختبار (نقطة) إلى الروم المطلوب - التوكن يعمل بشكل صحيح")
    except Exception as e:
        print(f"❌ فشل إرسال رسالة الاختبار: {e}")

@bot.event
async def on_guild_channel_create(channel):
    if not isinstance(channel, discord.TextChannel):
        return
    if channel.category_id != CATEGORY_ID:
        return

    pending_channels.add(channel.id)
    print(f"🆕 قناة جديدة مراقبة: {channel.name} (ID: {channel.id})")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # ===== التعامل مع القنوات المنتظرة لأول رسالة (إيمبد البداية) =====
    if message.channel.id in pending_channels:
        pending_channels.remove(message.channel.id)

        if not message.embeds:
            print(f"❌ أول رسالة في {message.channel.name} لا تحتوي إيمبد - تم التجاهل")
            return

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

        first_msg = None
        second_msg = None
        third_msg = None
        test_type = None
        is_open = True

        if "التحرير" in embed_text:
            test_type = "edit"
            is_open = EDIT_OPEN
            if is_open:
                first_msg = FIRST_MSG_EDIT
                second_msg = SECOND_MSG_EDIT
                third_msg_template = THIRD_MSG_EDIT
            else:
                closed_msg = CLOSED_MSG_EDIT
        elif "الترجمه الانجليزيه" in embed_text:
            test_type = "translate"
            is_open = TRANSLATE_OPEN
            if is_open:
                first_msg = FIRST_MSG_TRANS
                second_msg = SECOND_MSG_TRANS
                third_msg_template = THIRD_MSG_TRANS
            else:
                closed_msg = CLOSED_MSG_TRANS
        elif "تبييض" in embed_text:
            test_type = "whitening"
            is_open = WHITENING_OPEN
            if is_open:
                first_msg = FIRST_MSG_WHITENING
                second_msg = SECOND_MSG_WHITENING
                third_msg_template = THIRD_MSG_WHITENING
            else:
                closed_msg = CLOSED_MSG_WHITENING
        else:
            print(f"❌ أول رسالة في {message.channel.name} لا تحتوي الكلمة المطلوبة في الإيمبد - تم التجاهل")
            return

        channel = message.channel

        # ---- إذا كان التقديم مغلقاً: إرسال رسالة واحدة فقط مع محاكاة كتابة لمدة 3 ثوانٍ ----
        if not is_open:
            # محاكاة كتابة لمدة 3 ثوانٍ بالضبط
            try:
                async with channel.typing():
                    await asyncio.sleep(3)
                await channel.send(closed_msg)
                print(f"🚫 تم إرسال رسالة الإغلاق في {channel.name}")
            except Exception as e:
                print(f"❌ فشل إرسال رسالة الإغلاق: {e}")
            return

        # ---- التقديم مفتوح: استخراج المقدم ----
        app_user = None
        mention_str = ""
        if message.mentions:
            app_user = message.mentions[0]
            mention_str = app_user.mention
        else:
            raw_text = message.content if message.content else ""
            all_text = raw_text + " " + embed_text
            mentions = re.findall(r'<@!?(\d+)>', all_text)
            for uid in mentions:
                if uid != "1503165397585760428":
                    mention_str = f"<@{uid}>"
                    try:
                        app_user = await bot.fetch_user(int(uid))
                    except:
                        pass
                    break

        if app_user is None:
            print(f"❌ لم يتم العثور على المقدم في {message.channel.name}")
            return

        applicant_info[message.channel.id] = {"id": app_user.id, "mention": mention_str}

        third_msg = third_msg_template.replace("{mention}", mention_str)

        # تأخير عشوائي قبل الأولى
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        await asyncio.sleep(delay)

        # الرسالة الأولى
        for attempt in range(3):
            try:
                await human_send(channel, first_msg)
                print(f"📨 [{channel.guild.name}] تم الإرسال الأول في {channel.name}")
                break
            except discord.errors.HTTPException as e:
                if e.status == 429:
                    retry_after = e.retry_after
                    print(f"⏳ Rate limit، انتظر {retry_after} ثانية...")
                    await asyncio.sleep(retry_after + 0.5)
                else:
                    print(f"❌ فشل الإرسال الأول: {e}")
                    break

        # انتظار ثانية واحدة فقط بين الأولى والثانية
        await asyncio.sleep(1)

        # الرسالة الثانية
        for attempt in range(3):
            try:
                await human_send(channel, second_msg)
                print(f"📨2 [{channel.guild.name}] تم الإرسال الثاني في {channel.name}")
                break
            except discord.errors.HTTPException as e:
                if e.status == 429:
                    retry_after = e.retry_after
                    print(f"⏳ Rate limit للرسالة الثانية، انتظر {retry_after} ثانية...")
                    await asyncio.sleep(retry_after + 0.5)
                else:
                    print(f"❌ فشل الإرسال الثاني: {e}")
                    break

        # انتظار ثانيتين ثم 5 ثوانٍ كتابة للرسالة الثالثة
        await asyncio.sleep(2)

        for attempt in range(3):
            try:
                async with channel.typing():
                    await asyncio.sleep(5)
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

        active_tests[channel.id] = test_type

        # بدء مهمة المراقبة
        task = asyncio.create_task(
            monitor_test(channel, test_type, app_user.id, mention_str)
        )
        close_tasks[channel.id] = task

        # بدء مهمة التذكير الدورية
        if test_type == "edit":
            dur = EDIT_TEST_DURATION_SEC
        elif test_type == "translate":
            dur = TRANSLATE_TEST_DURATION_SEC
        else:
            dur = WHITENING_TEST_DURATION_SEC

        reminder_task = asyncio.create_task(
            periodic_reminder(channel.id, mention_str, dur, test_type)
        )
        reminder_tasks[channel.id] = reminder_task

        return

    # ===== مراقبة رسائل المقدم وروابط النتيجة =====
    if message.channel.id in active_tests:
        applicant = applicant_info.get(message.channel.id)
        if applicant and message.author.id == applicant["id"]:
            applicant_spoke.add(message.channel.id)

        test_type = active_tests[message.channel.id]
        content = message.content

        # تحقق من رابط درايف قوقل (للتحرير)
        if test_type == "edit" and re.search(r'https?://drive\.google\.com/', content):
            if message.channel.id not in link_submitted:
                link_submitted.add(message.channel.id)
                if message.channel.id in close_tasks:
                    close_tasks[message.channel.id].cancel()
                if message.channel.id in reminder_tasks:
                    reminder_tasks[message.channel.id].cancel()
                await message.channel.send("<@1202583085330333736>")
                print(f"🔔 تم منشن مشرف التحرير في {message.channel.name} - تم إلغاء الإغلاق التلقائي")

        # تحقق من رابط مستندات قوقل (للترجمة)
        elif test_type == "translate" and re.search(r'https?://docs\.google\.com/', content):
            if message.channel.id not in link_submitted:
                link_submitted.add(message.channel.id)
                if message.channel.id in close_tasks:
                    close_tasks[message.channel.id].cancel()
                if message.channel.id in reminder_tasks:
                    reminder_tasks[message.channel.id].cancel()
                await message.channel.send("<@1216084628453200015>")
                print(f"🔔 تم منشن مشرف الترجمة في {message.channel.name} - تم إلغاء الإغلاق التلقائي")

        # تحقق من رابط درايف قوقل (للتبييض)
        elif test_type == "whitening" and re.search(r'https?://drive\.google\.com/', content):
            if message.channel.id not in link_submitted:
                link_submitted.add(message.channel.id)
                if message.channel.id in close_tasks:
                    close_tasks[message.channel.id].cancel()
                if message.channel.id in reminder_tasks:
                    reminder_tasks[message.channel.id].cancel()
                await message.channel.send("<@1334530342899421287>")
                print(f"🔔 تم منشن مشرف التبييض في {message.channel.name} - تم إلغاء الإغلاق التلقائي")

@bot.event
async def on_command_error(ctx, error):
    print(f"⚠️ خطأ: {error}")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ التوكن غير موجود! ضع DISCORD_TOKEN في ملف .env")
    else:
        bot.run(TOKEN)