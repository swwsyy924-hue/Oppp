import discord
import asyncio
import random
import config
from state import *
from utils import human_send_smart, get_typing_duration, extract_link

async def monitor_test(bot, channel, duration, applicant_id, applicant_mention):
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
            await close_ticket(bot, channel)
            return

        if channel.id not in link_submitted:
            print(f"⏰ انتهى الوقت دون رابط في {channel.name} - إرسال رسالة الفشل")
            fail_text = config.FAIL_MSG.replace("{mention}", applicant_mention)
            await human_send_smart(channel, fail_text)
            await asyncio.sleep(3600)
            await close_ticket(bot, channel)
            return

    except Exception as e:
        print(f"❌ خطأ في monitor_test: {e}")

async def close_ticket(bot, channel):
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

async def periodic_reminder(bot, channel_id, applicant_mention, duration):
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

async def auto_close_closed_ticket(bot, channel, delay):
    """تغلق التكت المغلق بعد تأخير محدد (15 دقيقة)"""
    await asyncio.sleep(delay)
    try:
        try:
            channel = await bot.fetch_channel(channel.id)
        except discord.NotFound:
            return
        await close_ticket(bot, channel)
        print(f"🔒 تم إغلاق التكت المغلق {channel.name} تلقائياً بعد 15 دقيقة")
    except Exception as e:
        print(f"❌ فشل إغلاق التكت المغلق {channel.name}: {e}")

async def start_combined_test(bot, channel, mention_str):
    """تبدأ الاختبار المدمج (تحرير + تبييض) كمرحلة واحدة"""
    first_msg = config.FIRST_MSG_COMBINED
    second_msg = config.SECOND_MSG_COMBINED
    third_msg = config.THIRD_MSG_COMBINED.replace("{mention}", mention_str)

    await asyncio.sleep(random.uniform(1.0, 2.0))

    await human_send_smart(channel, first_msg)
    print(f"📨 [تحرير+تبييض] [{channel.guild.name}] تم الإرسال الأول في {channel.name}")

    await asyncio.sleep(1)

    await human_send_smart(channel, second_msg)
    print(f"📨2 [تحرير+تبييض] [{channel.guild.name}] تم الإرسال الثاني في {channel.name}")

    await asyncio.sleep(2)

    await human_send_smart(channel, third_msg)
    print(f"📨3 [تحرير+تبييض] [{channel.guild.name}] تم الإرسال الثالث في {channel.name}")

    active_tests[channel.id] = "combined"
    link_submitted.discard(channel.id)

    task = asyncio.create_task(
        monitor_test(bot, channel, config.COMBINED_TEST_DURATION_SEC, None, mention_str)
    )
    close_tasks[channel.id] = task
    reminder_task = asyncio.create_task(
        periodic_reminder(bot, channel.id, mention_str, config.COMBINED_TEST_DURATION_SEC)
    )
    reminder_tasks[channel.id] = reminder_task