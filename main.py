import discord
from discord.ext import commands
import asyncio
import random
import re
import config

# استيراد الإعدادات والثوابت
from config import *

# استيراد الحالة الداخلية
from state import *

# استيراد الأدوات المساعدة
from utils import get_typing_duration, extract_link, human_send_smart

# استيراد الدوال التلقائية (مراحل الاختبار، الإغلاق، التذكير)
from auto_handlers import (
    monitor_test,
    close_ticket,
    periodic_reminder,
    auto_close_closed_ticket,
    start_whitening_phase,
    start_edit_phase,
)

# استيراد معالج أوامر التحكم
from control_panel import process_control_command

# إعداد proxy إن وجد
proxy = None
if PROXY_URL:
    proxy = PROXY_URL

bot = commands.Bot(command_prefix="!", self_bot=True, proxy=proxy)

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
async def on_guild_channel_delete(channel):
    """عند حذف أي قناة من الفئة، نزيد العدادين مغلقة وفاشلة"""
    if channel.category_id == CATEGORY_ID and isinstance(channel, discord.TextChannel):
        stats['closed'] += 1
        stats['failed'] += 1

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # ===== قناة التحكم =====
    if message.channel.id == CONTROL_CHANNEL_ID and message.author.id == OWNER_ID:
        await process_control_command(message, bot)  # تم تمرير bot
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
                auto_close_closed_ticket(bot, channel, CLOSED_TICKET_CLOSE_DELAY)  # تم تمرير bot
            )
            close_tasks[channel.id] = close_task
            return

        # ---- التقديم مفتوح ----
        if is_combined:
            await start_whitening_phase(bot, channel, applicant_mention)  # تم تمرير bot
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
                monitor_test(bot, channel, TRANSLATE_TEST_DURATION_SEC, app_user.id, applicant_mention)  # تم تمرير bot
            )
            close_tasks[channel.id] = task
            reminder_task = asyncio.create_task(
                periodic_reminder(bot, channel.id, applicant_mention, TRANSLATE_TEST_DURATION_SEC)  # تم تمرير bot
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
                await start_edit_phase(bot, message.channel, applicant["mention"])  # تم تمرير bot
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