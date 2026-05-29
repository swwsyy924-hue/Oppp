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
# 🧠 تحكم عن بعد (إعدادات جديدة)
# ═══════════════════════════════════════
OWNER_ID = int(os.getenv("OWNER_ID"))
CONTROL_CHANNEL_ID = int(os.getenv("CONTROL_CHANNEL_ID"))

# ═══════════════════════════════════════
# 🔧 أوضاع التقديم (True = مفتوح, False = مغلق)
# ═══════════════════════════════════════
EDIT_WHITENING_OPEN = False   # المسار المدمج (تحرير + تبييض)
TRANSLATE_OPEN = False       # الترجمة (مستقلة)

# مدد الاختبارات بالثواني
EDIT_TEST_DURATION_SEC = 4 * 3600       # 4 ساعات (مرحلة التحرير)
TRANSLATE_TEST_DURATION_SEC = 2 * 3600  # ساعتان (الترجمة)
WHITENING_TEST_DURATION_SEC = 3 * 3600  # 3 ساعات (مرحلة التبييض)

# مدة إغلاق التكتات المغلقة تلقائياً
CLOSED_TICKET_CLOSE_DELAY = 900  # 15 دقيقة

# الرابط الثابت لشات المعلومات
INFO_CHANNEL_LINK = "https://discord.com/channels/1202306392757915688/1202559461433286716"

# إحصائيات بسيطة (عدادات)
stats = {"opened": 0, "closed": 0, "success": 0, "failed": 0}

# الرسائل حسب الكلمة
FIRST_MSG_EDIT = "اسم اختبار تحرير"
SECOND_MSG_EDIT = "اختبار تحرير"

FIRST_MSG_TRANS = "اسم اختبار ترجمة"
SECOND_MSG_TRANS = "اختبار ترجمة"

FIRST_MSG_WHITENING = "اسم اختبار تحرير + تبييض"
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

# رسالة الفشل (عند انتهاء الوقت دون إرسال الرابط)
FAIL_MSG = (
    "{mention} انتهى وقت الاختبار للأسف 🤷‍♂️.\n"
    "لقد فشلت في الاختبار. سيتم إغلاق التكت بعد ساعة."
)

# مجموعة القنوات المنتظرة لأول رسالة
pending_channels = set()

# قاموس لتتبع القنوات النشطة ونوع الاختبار ومعلومات المقدم
active_tests = {}          # channel_id -> "edit" أو "translate" أو "whitening" أو "combined"
applicant_info = {}        # channel_id -> {"id": int, "mention": str}
applicant_spoke = set()    # قنوات أرسل فيها المقدم رسالة واحدة على الأقل
link_submitted = set()     # قنوات أرسل فيها المقدم رابط الاختبار (للمرحلة الحالية)

# قاموس لتخزين المرحلة الحالية للمسار المدمج
test_phase = {}            # channel_id -> "whitening" أو "edit"

# قاموس لتخزين مهام الإغلاق التلقائي
close_tasks = {}

# قاموس لتخزين مهام التذكير الدورية
reminder_tasks = {}

# إعداد الـ proxy إذا وجد
proxy = None
if PROXY_URL:
    proxy = PROXY_URL

bot = commands.Bot(command_prefix="!", self_bot=True, proxy=proxy)

# --- دالة حساب وقت الكتابة بناءً على عدد الكلمات ---
def get_typing_duration(text):
    """حساب مدة محاكاة الكتابة بناءً على عدد الكلمات (0.35 ثانية لكل كلمة)"""
    word_count = len(text.split())
    duration = word_count * 0.35
    return max(1.5, min(duration, 8.0))  # بين 1.5 و 8 ثوانٍ

# دالة مساعدة: إرسال رسالة مع محاكاة الكتابة البشرية الذكية
async def human_send_smart(channel, content):
    """يُظهر حالة الكتابة لمدة تتناسب مع طول الرسالة ثم يرسلها"""
    duration = get_typing_duration(content)
    async with channel.typing():
        await asyncio.sleep(duration)
    await channel.send(content)

# --- دالة استخراج الرابط من النص أو الإيمبدات (تغطي الحالتين) ---
def extract_link(message, pattern):
    """
    يحاول إيجاد رابط يطابق النمط في محتوى الرسالة أو في أي إيمبد مرفق.
    يعيد الرابط كسلسة إذا وُجد، وإلا None.
    """
    if message.content:
        match = re.search(pattern, message.content)
        if match:
            return match.group(0)
    for embed in message.embeds:
        for attr in ('title', 'description', 'url'):
            val = getattr(embed, attr, None)
            if val and isinstance(val, str):
                match = re.search(pattern, val)
                if match:
                    return match.group(0)
        for field in embed.fields:
            for sub_attr in ('name', 'value'):
                val = getattr(field, sub_attr, None)
                if val and isinstance(val, str):
                    match = re.search(pattern, val)
                    if match:
                        return match.group(0)
    return None

async def monitor_test(channel, duration, applicant_id, applicant_mention):
    """تراقب تقدم الاختبار بمدة معينة وتقرر الإغلاق أو إرسال رسالة الفشل"""
    await asyncio.sleep(duration)

    if channel.id in link_submitted:
        print(f"✅ تم تسليم الاختبار في {channel.name} - لن يتم الإغلاق التلقائي")
        return

    try:
        try:
            channel = await bot.fetch_channel(channel.id)
        except discord.NotFound:
            print(f"❌ القناة لم تعد موجودة، تخطي")
            return

        if channel.id not in applicant_spoke:
            print(f"⏰ لم يرسل المقدم أي رسالة في {channel.name} - إغلاق مباشر")
            await close_ticket(channel)
            return

        if channel.id not in link_submitted:
            print(f"⏰ انتهى الوقت دون رابط في {channel.name} - إرسال رسالة الفشل")
            fail_text = FAIL_MSG.replace("{mention}", applicant_mention)
            await human_send_smart(channel, fail_text)
            await asyncio.sleep(3600)
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

async def periodic_reminder(channel_id, applicant_mention, duration):
    """يرسل تذكيراً عند منتصف الوقت ثم كل ساعة للمُقدّم الذي لم يكتب أي شيء بعد"""
    half_duration = duration / 2
    await asyncio.sleep(half_duration)

    if channel_id in applicant_spoke or channel_id in link_submitted:
        return

    remaining = duration - half_duration
    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    if hours > 0:
        time_str = f"{hours} ساعة"
        if minutes > 0:
            time_str += f" و {minutes} دقيقة"
    else:
        time_str = f"{minutes} دقيقة"

    half_reminder = (
        f"# تنبيه {applicant_mention}\n\n"
        f"**بقت لك {time_str} حتى ينتهي الاختبار**\n\n"
        "> لازم تسرع بتسليم الاختبار قبل ما ينتهي الوقت 🫠\n\n"
        "بالتوفيق!"
    )
    try:
        channel = await bot.fetch_channel(channel_id)
        await human_send_smart(channel, half_reminder)
        print(f"🔔 تذكير منتصف الوقت في {channel.name}")
    except Exception as e:
        print(f"❌ فشل إرسال تذكير المنتصف: {e}")

    elapsed = half_duration
    interval = 3600
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
            f"**بقت لك {time_str} حتى ينتهي الاختبار**\n\n"
            "> لازم تسرع بتسليم الاختبار قبل ما ينتهي الوقت 🫠\n\n"
            "بالتوفيق!"
        )
        try:
            await human_send_smart(channel, reminder)
            print(f"🔔 تذكير دوري في {channel.name}")
        except Exception as e:
            print(f"❌ فشل إرسال التذكير: {e}")

async def auto_close_closed_ticket(channel, delay):
    """تغلق التكت المغلق بعد تأخير محدد (15 دقيقة)"""
    await asyncio.sleep(delay)
    try:
        try:
            channel = await bot.fetch_channel(channel.id)
        except discord.NotFound:
            return
        await close_ticket(channel)
        print(f"🔒 تم إغلاق التكت المغلق {channel.name} تلقائياً بعد 15 دقيقة")
    except Exception as e:
        print(f"❌ فشل إغلاق التكت المغلق {channel.name}: {e}")

# دالة بدء مرحلة التبييض (المدمج)
async def start_whitening_phase(channel, mention_str):
    """تبدأ مرحلة التبييض في المسار المدمج"""
    first_msg = FIRST_MSG_WHITENING
    second_msg = SECOND_MSG_WHITENING
    third_msg = THIRD_MSG_WHITENING.replace("{mention}", mention_str)

    await asyncio.sleep(random.uniform(1.0, 2.0))

    await human_send_smart(channel, first_msg)
    print(f"📨 [تبييض] [{channel.guild.name}] تم الإرسال الأول في {channel.name}")

    await asyncio.sleep(1)

    await human_send_smart(channel, second_msg)
    print(f"📨2 [تبييض] [{channel.guild.name}] تم الإرسال الثاني في {channel.name}")

    await asyncio.sleep(2)

    await human_send_smart(channel, third_msg)
    print(f"📨3 [تبييض] [{channel.guild.name}] تم الإرسال الثالث في {channel.name}")

    active_tests[channel.id] = "combined"
    test_phase[channel.id] = "whitening"
    link_submitted.discard(channel.id)

    task = asyncio.create_task(
        monitor_test(channel, WHITENING_TEST_DURATION_SEC, None, mention_str)
    )
    close_tasks[channel.id] = task
    reminder_task = asyncio.create_task(
        periodic_reminder(channel.id, mention_str, WHITENING_TEST_DURATION_SEC)
    )
    reminder_tasks[channel.id] = reminder_task

# دالة بدء مرحلة التحرير (بعد قبول التبييض)
async def start_edit_phase(channel, mention_str):
    """تبدأ مرحلة التحرير بعد الأمر مباشرة (بدون اسم)"""
    second_msg = SECOND_MSG_EDIT
    third_msg = THIRD_MSG_EDIT.replace("{mention}", mention_str)

    await asyncio.sleep(1.5)

    await human_send_smart(channel, second_msg)
    print(f"📨2 [تحرير] [{channel.guild.name}] تم الإرسال الثاني في {channel.name}")

    await asyncio.sleep(2)

    await human_send_smart(channel, third_msg)
    print(f"📨3 [تحرير] [{channel.guild.name}] تم الإرسال الثالث في {channel.name}")

    test_phase[channel.id] = "edit"
    link_submitted.discard(channel.id)

    task = asyncio.create_task(
        monitor_test(channel, EDIT_TEST_DURATION_SEC, None, mention_str)
    )
    close_tasks[channel.id] = task
    reminder_task = asyncio.create_task(
        periodic_reminder(channel.id, mention_str, EDIT_TEST_DURATION_SEC)
    )
    reminder_tasks[channel.id] = reminder_task

# ═══════════════════════════════════════
# 🎮 معالجة أوامر التحكم عن بعد
# ═══════════════════════════════════════
async def process_control_command(message):
    global EDIT_WHITENING_OPEN, TRANSLATE_OPEN, EDIT_TEST_DURATION_SEC, TRANSLATE_TEST_DURATION_SEC
    global WHITENING_TEST_DURATION_SEC, CLOSED_TICKET_CLOSE_DELAY, INFO_CHANNEL_LINK
    global stats
    parts = message.content.split()
    cmd = parts[0].lower() if parts else ""
    args = parts[1:] if len(parts) > 1 else []

    try:
        # --- فتح / إغلاق التخصصات ---
        if cmd == "!open_edit":
            EDIT_WHITENING_OPEN = True
            await message.channel.send("✅ **تحرير + تبييض:** تم فتح التقديم.")
        elif cmd == "!close_edit":
            EDIT_WHITENING_OPEN = False
            await message.channel.send("🔒 **تحرير + تبييض:** تم إغلاق التقديم.")
        elif cmd == "!open_translate":
            TRANSLATE_OPEN = True
            await message.channel.send("✅ **ترجمة:** تم فتح التقديم.")
        elif cmd == "!close_translate":
            TRANSLATE_OPEN = False
            await message.channel.send("🔒 **ترجمة:** تم إغلاق التقديم.")
        elif cmd == "!toggle_edit":
            EDIT_WHITENING_OPEN = not EDIT_WHITENING_OPEN
            state = "مفتوح" if EDIT_WHITENING_OPEN else "مغلق"
            await message.channel.send(f"🔄 **تحرير + تبييض:** أصبح {state}.")
        elif cmd == "!toggle_translate":
            TRANSLATE_OPEN = not TRANSLATE_OPEN
            state = "مفتوح" if TRANSLATE_OPEN else "مغلق"
            await message.channel.send(f"🔄 **ترجمة:** أصبحت {state}.")

        # --- عرض الحالة ---
        elif cmd == "!status":
            edit_icon = "🟢" if EDIT_WHITENING_OPEN else "🔴"
            trans_icon = "🟢" if TRANSLATE_OPEN else "🔴"
            active = len(active_tests)
            txt = (
                f"**📊 حالة النظام**\n"
                f"{edit_icon} **تحرير + تبييض:** {'مفتوح' if EDIT_WHITENING_OPEN else 'مغلق'}\n"
                f"{trans_icon} **ترجمة:** {'مفتوح' if TRANSLATE_OPEN else 'مغلق'}\n"
                f"📁 **تكتات نشطة:** {active}"
            )
            await message.channel.send(txt)

        # --- عرض التكتات النشطة ---
        elif cmd == "!list_active":
            if not active_tests:
                await message.channel.send("ℹ️ لا توجد تكتات نشطة حاليًا.")
            else:
                lines = []
                for idx, (ch_id, ttype) in enumerate(active_tests.items(), 1):
                    ment = applicant_info.get(ch_id, {}).get("mention", "غير معروف")
                    phase = test_phase.get(ch_id, "-")
                    if ttype == "combined":
                        phase_name = "تبييض" if phase == "whitening" else "تحرير"
                        ttype_display = f"تحرير+تبييض ({phase_name})"
                    else:
                        ttype_display = "ترجمة"
                    lines.append(f"{idx}. <#{ch_id}> | {ment} | {ttype_display}")
                await message.channel.send("**📋 التكتات النشطة:**\n" + "\n".join(lines))

        # --- إغلاق تكت محدد ---
        elif cmd == "!force_close":
            if args:
                ch_id = int(args[0])
                ch = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
                await close_ticket(ch)
                await message.channel.send(f"🗑️ جارٍ إغلاق تكت {ch.name}.")
            else:
                await message.channel.send("❗ استخدم `!force_close <معرف القناة>`")

        # --- إرسال فشل لتكت محدد ---
        elif cmd == "!force_fail":
            if args:
                ch_id = int(args[0])
                ch = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
                mention = applicant_info.get(ch_id, {}).get("mention", "")
                await human_send_smart(ch, FAIL_MSG.replace("{mention}", mention))
                await message.channel.send(f"⛔ تم إرسال إشعار الفشل لتكت {ch.name}.")
            else:
                await message.channel.send("❗ استخدم `!force_fail <معرف القناة>`")

        # --- نقل المسار المدمج للمرحلة التالية ---
        elif cmd == "!force_next":
            if args:
                ch_id = int(args[0])
                if test_phase.get(ch_id) == "whitening":
                    mention = applicant_info.get(ch_id, {}).get("mention", "")
                    ch = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
                    await start_edit_phase(ch, mention)
                    await message.channel.send(f"⏭️ تم نقل تكت {ch.name} إلى مرحلة التحرير.")
                else:
                    await message.channel.send("❌ التكت ليس في مرحلة التبييض.")
            else:
                await message.channel.send("❗ استخدم `!force_next <معرف القناة>`")

        # --- تذكير فوري ---
        elif cmd == "!remind":
            if args:
                ch_id = int(args[0])
                mention = applicant_info.get(ch_id, {}).get("mention", "")
                ch = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
                await human_send_smart(ch, f"# تذكير {mention}\n\nيرجى تسليم الاختبار قبل انتهاء الوقت.")
                await message.channel.send(f"🔔 تم إرسال تذكير في تكت {ch.name}.")
            else:
                await message.channel.send("❗ استخدم `!remind <معرف القناة>`")

        # --- ضبط المدد ---
        elif cmd == "!set_edit_time":
            if args:
                EDIT_TEST_DURATION_SEC = int(args[0]) * 3600
                await message.channel.send(f"⏱️ مدة التحرير أصبحت **{args[0]}** ساعة.")
            else:
                await message.channel.send("❗ استخدم `!set_edit_time <عدد الساعات>`")
        elif cmd == "!set_whitening_time":
            if args:
                WHITENING_TEST_DURATION_SEC = int(args[0]) * 3600
                await message.channel.send(f"⏱️ مدة التبييض أصبحت **{args[0]}** ساعة.")
            else:
                await message.channel.send("❗ استخدم `!set_whitening_time <عدد الساعات>`")
        elif cmd == "!set_translate_time":
            if args:
                TRANSLATE_TEST_DURATION_SEC = int(args[0]) * 3600
                await message.channel.send(f"⏱️ مدة الترجمة أصبحت **{args[0]}** ساعة.")
            else:
                await message.channel.send("❗ استخدم `!set_translate_time <عدد الساعات>`")
        elif cmd == "!set_close_delay":
            if args:
                CLOSED_TICKET_CLOSE_DELAY = int(args[0]) * 60
                await message.channel.send(f"⏲️ تأخير الإغلاق أصبح **{args[0]}** دقيقة.")
            else:
                await message.channel.send("❗ استخدم `!set_close_delay <عدد الدقائق>`")
        elif cmd == "!set_info_link":
            if args:
                INFO_CHANNEL_LINK = args[0]
                await message.channel.send(f"🔗 رابط المعلومات تم تحديثه.")
            else:
                await message.channel.send("❗ استخدم `!set_info_link <الرابط الجديد>`")

        # --- عرض الإعدادات ---
        elif cmd == "!show_settings":
            txt = (
                f"**⚙️ الإعدادات الحالية**\n"
                f"**تحرير + تبييض:** {'مفتوح' if EDIT_WHITENING_OPEN else 'مغلق'}\n"
                f"**ترجمة:** {'مفتوح' if TRANSLATE_OPEN else 'مغلق'}\n"
                f"**مدة التحرير:** {EDIT_TEST_DURATION_SEC//3600} ساعة\n"
                f"**مدة التبييض:** {WHITENING_TEST_DURATION_SEC//3600} ساعة\n"
                f"**مدة الترجمة:** {TRANSLATE_TEST_DURATION_SEC//3600} ساعة\n"
                f"**تأخير إغلاق التكت المغلق:** {CLOSED_TICKET_CLOSE_DELAY//60} دقيقة\n"
                f"**رابط المعلومات:** {INFO_CHANNEL_LINK}"
            )
            await message.channel.send(txt)

        # --- إرسال رسالة مخصصة ---
        elif cmd == "!say":
            if len(args) >= 2:
                ch_id = int(args[0])
                text = " ".join(args[1:])
                ch = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
                await human_send_smart(ch, text)
                await message.channel.send(f"💬 تم الإرسال في <#{ch_id}>.")
            else:
                await message.channel.send("❗ استخدم `!say <معرف القناة> <النص>`")

        # --- أوامر عامة ---
        elif cmd == "!ping":
            await message.channel.send("🏓 البوت يعمل!")
        elif cmd == "!stats":
            txt = (
                f"**📈 إحصائيات**\n"
                f"تكتات مفتوحة: {stats['opened']}\n"
                f"تكتات مغلقة: {stats['closed']}\n"
                f"ناجحة: {stats['success']}\n"
                f"فاشلة: {stats['failed']}"
            )
            await message.channel.send(txt)
        elif cmd == "!close_all":
            count = len(active_tests)
            for ch_id in list(active_tests.keys()):
                ch = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
                await close_ticket(ch)
            await message.channel.send(f"🔒 جارٍ إغلاق {count} تكت.")
        elif cmd == "!reload":
            load_dotenv(override=True)
            await message.channel.send("🔄 تم إعادة تحميل ملف البيئة.")
        elif cmd == "!shutdown":
            await message.channel.send("🛑 جارٍ إيقاف التشغيل...")
            await bot.close()

        # --- مساعدة محسنة (بدون Embed) ---
        elif cmd == "!help":
            help_txt = (
                "**📚 دليل الأوامر**\n"
                "جميع الأوامر تبدأ بـ `!` وتستخدم في قناة التحكم المخصصة.\n\n"
                "**🔧 التحكم بالتخصصات**\n"
                "`!open_edit` – فتح تقديم تحرير + تبييض\n"
                "`!close_edit` – إغلاق تقديم تحرير + تبييض\n"
                "`!open_translate` – فتح تقديم الترجمة\n"
                "`!close_translate` – إغلاق تقديم الترجمة\n"
                "`!toggle_edit` – تبديل حالة تحرير + تبييض\n"
                "`!toggle_translate` – تبديل حالة الترجمة\n\n"
                "**📋 المراقبة والمتابعة**\n"
                "`!status` – عرض حالة التقديمات والتكتات\n"
                "`!list_active` – عرض التكتات النشطة\n"
                "`!stats` – إحصائيات عامة\n\n"
                "**🎫 إدارة التكتات**\n"
                "`!force_close <id>` – إغلاق تكت محدد\n"
                "`!force_fail <id>` – إرسال فشل لتكت محدد\n"
                "`!force_next <id>` – نقل تكت مدمج لمرحلة التحرير\n"
                "`!remind <id>` – إرسال تذكير فوري\n"
                "`!close_all` – إغلاق جميع التكتات\n\n"
                "**⚙️ الإعدادات**\n"
                "`!set_edit_time <ساعات>` – ضبط مدة التحرير\n"
                "`!set_whitening_time <ساعات>` – ضبط مدة التبييض\n"
                "`!set_translate_time <ساعات>` – ضبط مدة الترجمة\n"
                "`!set_close_delay <دقائق>` – ضبط تأخير إغلاق التكت المغلق\n"
                "`!set_info_link <رابط>` – تغيير رابط المعلومات\n"
                "`!show_settings` – عرض الإعدادات الحالية\n\n"
                "**🛠️ عام**\n"
                "`!ping` – اختبار الاتصال\n"
                "`!say <id> <نص>` – إرسال رسالة عبر الحساب\n"
                "`!reload` – إعادة تحميل متغيرات البيئة\n"
                "`!shutdown` – إيقاف البوت"
            )
            await message.channel.send(help_txt)

        else:
            await message.channel.send("❓ أمر غير معروف. استخدم `!help` لعرض الأوامر.")

    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {e}")


# ═══════════════════════════════════════
# الأحداث الرئيسية (التلقائية)
# ═══════════════════════════════════════
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

    # ===== قناة التحكم =====
    if message.channel.id == CONTROL_CHANNEL_ID and message.author.id == OWNER_ID:
        await process_control_command(message)
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
        is_combined = False

        if "التحرير" in embed_text or "تبييض" in embed_text:
            is_combined = True
            is_open = EDIT_WHITENING_OPEN
            test_name = "اختبار تحرير + تبييض"
        elif "الترجمه الانجليزيه" in embed_text:
            test_type = "translate"
            is_open = TRANSLATE_OPEN
            if is_open:
                first_msg = FIRST_MSG_TRANS
                second_msg = SECOND_MSG_TRANS
                third_msg_template = THIRD_MSG_TRANS
            else:
                test_name = "اختبار الترجمة الانجليزية"
        else:
            print(f"❌ أول رسالة في {message.channel.name} لا تحتوي الكلمة المطلوبة في الإيمبد - تم التجاهل")
            return

        channel = message.channel

        # ---- استخراج المقدم ----
        applicant_mention = ""
        app_user = None
        if message.mentions:
            app_user = message.mentions[0]
            applicant_mention = app_user.mention
        else:
            raw_text = message.content if message.content else ""
            all_text = raw_text + " " + embed_text
            mentions = re.findall(r'<@!?(\d+)>', all_text)
            for uid in mentions:
                if uid != "1503165397585760428":
                    applicant_mention = f"<@{uid}>"
                    try:
                        app_user = await bot.fetch_user(int(uid))
                    except:
                        pass
                    break

        if app_user is None:
            print(f"❌ لم يتم العثور على المقدم في {message.channel.name}")
            return

        applicant_info[channel.id] = {"id": app_user.id, "mention": applicant_mention}

        # ---- إذا كان التقديم مغلقاً ----
        if not is_open:
            closed_msg = (
                f"# نعتذر منك 🙏\n\n"
                f"**{applicant_mention}، تقديم {test_name} مغلق حالياً**\n\n"
                f"> نرجو متابعة شات المعلومات لمعرفة آخر المستجدات:\n"
                f"> {INFO_CHANNEL_LINK}\n\n"
                f"- إذا كنت ترغب في التقديم على تخصص آخر **مفتوح**، يمكنك فتح تكت جديد.\n"
                f"- سيتم إغلاق هذا التكت تلقائياً بعد **15 دقيقة**.\n\n"
                f"-# شكراً لتفهمك"
            )
            await human_send_smart(channel, closed_msg)
            print(f"🚫 تم إرسال رسالة الإغلاق في {channel.name}")

            close_task = asyncio.create_task(
                auto_close_closed_ticket(channel, CLOSED_TICKET_CLOSE_DELAY)
            )
            close_tasks[channel.id] = close_task
            return

        # ---- التقديم مفتوح ----
        if is_combined:
            await start_whitening_phase(channel, applicant_mention)
        else:
            # اختبار ترجمة مستقل
            third_msg = third_msg_template.replace("{mention}", applicant_mention)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            await human_send_smart(channel, first_msg)
            await asyncio.sleep(1)
            await human_send_smart(channel, second_msg)
            await asyncio.sleep(2)
            await human_send_smart(channel, third_msg)

            active_tests[channel.id] = test_type
            task = asyncio.create_task(
                monitor_test(channel, TRANSLATE_TEST_DURATION_SEC, app_user.id, applicant_mention)
            )
            close_tasks[channel.id] = task
            reminder_task = asyncio.create_task(
                periodic_reminder(channel.id, applicant_mention, TRANSLATE_TEST_DURATION_SEC)
            )
            reminder_tasks[channel.id] = reminder_task

        return

    # ===== مراقبة رسائل المقدم وروابط النتيجة + أوامر المشرفين =====
    if message.channel.id in active_tests:
        applicant = applicant_info.get(message.channel.id)
        if applicant and message.author.id == applicant["id"]:
            applicant_spoke.add(message.channel.id)

        test_type = active_tests[message.channel.id]
        content = message.content

        # --- المسار المدمج ---
        if test_type == "combined":
            phase = test_phase.get(message.channel.id)
            # أمر "اكمل <@930731511081213963>"
            if (phase == "whitening" 
                and "اكمل" in content 
                and "<@930731511081213963>" in content):
                if message.channel.id not in link_submitted:
                    await message.channel.send(" انتظر بالبداية يسلم اختبار التبييض وعود اكمل")
                    return
                if message.channel.id in close_tasks:
                    close_tasks[message.channel.id].cancel()
                if message.channel.id in reminder_tasks:
                    reminder_tasks[message.channel.id].cancel()
                await start_edit_phase(message.channel, applicant["mention"])
                return

            # رابط درايف - تبييض (يغطي الرابط بمفرده أو مع نص)
            if phase == "whitening":
                extracted = extract_link(message, r'https?://drive\.google\.com/[^\s]+')
                if extracted and message.channel.id not in link_submitted:
                    link_submitted.add(message.channel.id)
                    if message.channel.id in close_tasks:
                        close_tasks[message.channel.id].cancel()
                    if message.channel.id in reminder_tasks:
                        reminder_tasks[message.channel.id].cancel()
                    await message.channel.send("<@1334530342899421287>")
                    print(f"🔔 [تبييض] تم منشن المشرف في {message.channel.name}")
                    return

            # رابط درايف - تحرير
            if phase == "edit":
                extracted = extract_link(message, r'https?://drive\.google\.com/[^\s]+')
                if extracted and message.channel.id not in link_submitted:
                    link_submitted.add(message.channel.id)
                    if message.channel.id in close_tasks:
                        close_tasks[message.channel.id].cancel()
                    if message.channel.id in reminder_tasks:
                        reminder_tasks[message.channel.id].cancel()
                    await message.channel.send("<@1202583085330333736>")
                    print(f"🔔 [تحرير] تم منشن المشرف في {message.channel.name}")
                    return

        # --- الاختبارات المستقلة (ترجمة) ---
        if test_type == "translate":
            extracted = extract_link(message, r'https?://docs\.google\.com/[^\s]+')
            if extracted and message.channel.id not in link_submitted:
                link_submitted.add(message.channel.id)
                if message.channel.id in close_tasks:
                    close_tasks[message.channel.id].cancel()
                if message.channel.id in reminder_tasks:
                    reminder_tasks[message.channel.id].cancel()
                await message.channel.send("<@1216084628453200015>")
                print(f"🔔 تم منشن مشرف الترجمة في {message.channel.name}")

@bot.event
async def on_command_error(ctx, error):
    print(f"⚠️ خطأ: {error}")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ التوكن غير موجود! ضع DISCORD_TOKEN في ملف .env")
    else:
        bot.run(TOKEN)