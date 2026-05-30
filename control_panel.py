import discord
import asyncio
from dotenv import load_dotenv

from config import *
from state import *
from utils import human_send_smart
from auto_handlers import close_ticket, start_edit_phase

async def process_control_command(message, self_bot):
    global EDIT_WHITENING_OPEN, TRANSLATE_OPEN, EDIT_TEST_DURATION_SEC, TRANSLATE_TEST_DURATION_SEC
    global WHITENING_TEST_DURATION_SEC, CLOSED_TICKET_CLOSE_DELAY, INFO_CHANNEL_LINK
    global stats

    parts = message.content.split()
    cmd = parts[0] if parts else ""
    args = parts[1:] if len(parts) > 1 else []

    try:
        # ── فتح / إغلاق التخصصات ──
        if cmd == "!فتح_دمج":
            EDIT_WHITENING_OPEN = True
            await message.channel.send("✅ **تحرير + تبييض:** تم فتح التقديم.")
        elif cmd == "!اغلاق_دمج":
            EDIT_WHITENING_OPEN = False
            await message.channel.send("🔒 **تحرير + تبييض:** تم إغلاق التقديم.")
        elif cmd == "!فتح_ترجمة":
            TRANSLATE_OPEN = True
            await message.channel.send("✅ **ترجمة:** تم فتح التقديم.")
        elif cmd == "!اغلاق_ترجمة":
            TRANSLATE_OPEN = False
            await message.channel.send("🔒 **ترجمة:** تم إغلاق التقديم.")
        elif cmd == "!تبديل_دمج":
            EDIT_WHITENING_OPEN = not EDIT_WHITENING_OPEN
            state = "مفتوح" if EDIT_WHITENING_OPEN else "مغلق"
            await message.channel.send(f"🔄 **تحرير + تبييض:** أصبح {state}.")
        elif cmd == "!تبديل_ترجمة":
            TRANSLATE_OPEN = not TRANSLATE_OPEN
            state = "مفتوح" if TRANSLATE_OPEN else "مغلق"
            await message.channel.send(f"🔄 **ترجمة:** أصبحت {state}.")

        # ── عرض الحالة ──
        elif cmd == "!الحالة":
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

        # ── عرض التكتات النشطة ──
        elif cmd == "!التكتات":
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

        # ── إغلاق تكت محدد ──
        elif cmd == "!اغلاق_تكت":
            if args:
                ch_id = int(args[0])
                ch = self_bot.get_channel(ch_id) or await self_bot.fetch_channel(ch_id)
                await close_ticket(self_bot, ch)
                await message.channel.send(f"🗑️ جارٍ إغلاق تكت {ch.name}.")
            else:
                await message.channel.send("❗ استخدم `!اغلاق_تكت <معرف القناة>`")

        # ── إرسال فشل لتكت محدد ──
        elif cmd == "!فشل_تكت":
            if args:
                ch_id = int(args[0])
                ch = self_bot.get_channel(ch_id) or await self_bot.fetch_channel(ch_id)
                mention = applicant_info.get(ch_id, {}).get("mention", "")
                await human_send_smart(ch, FAIL_MSG.replace("{mention}", mention))
                await message.channel.send(f"⛔ تم إرسال إشعار الفشل لتكت {ch.name}.")
            else:
                await message.channel.send("❗ استخدم `!فشل_تكت <معرف القناة>`")

        # ── نقل المسار المدمج للمرحلة التالية ──
        elif cmd == "!التالي":
            if args:
                ch_id = int(args[0])
                if test_phase.get(ch_id) == "whitening":
                    mention = applicant_info.get(ch_id, {}).get("mention", "")
                    ch = self_bot.get_channel(ch_id) or await self_bot.fetch_channel(ch_id)
                    await start_edit_phase(self_bot, ch, mention)
                    await message.channel.send(f"⏭️ تم نقل تكت {ch.name} إلى مرحلة التحرير.")
                else:
                    await message.channel.send("❌ التكت ليس في مرحلة التبييض.")
            else:
                await message.channel.send("❗ استخدم `!التالي <معرف القناة>`")

        # ── تذكير فوري ──
        elif cmd == "!تذكير":
            if args:
                ch_id = int(args[0])
                mention = applicant_info.get(ch_id, {}).get("mention", "")
                ch = self_bot.get_channel(ch_id) or await self_bot.fetch_channel(ch_id)
                await human_send_smart(ch, f"# تذكير {mention}\n\nيرجى تسليم الاختبار قبل انتهاء الوقت.")
                await message.channel.send(f"🔔 تم إرسال تذكير في تكت {ch.name}.")
            else:
                await message.channel.send("❗ استخدم `!تذكير <معرف القناة>`")

        # ── ضبط المدد ──
        elif cmd == "!وقت_التحرير":
            if args:
                EDIT_TEST_DURATION_SEC = int(args[0]) * 3600
                await message.channel.send(f"⏱️ مدة التحرير أصبحت **{args[0]}** ساعة.")
            else:
                await message.channel.send("❗ استخدم `!وقت_التحرير <عدد الساعات>`")
        elif cmd == "!وقت_التبييض":
            if args:
                WHITENING_TEST_DURATION_SEC = int(args[0]) * 3600
                await message.channel.send(f"⏱️ مدة التبييض أصبحت **{args[0]}** ساعة.")
            else:
                await message.channel.send("❗ استخدم `!وقت_التبييض <عدد الساعات>`")
        elif cmd == "!وقت_الترجمة":
            if args:
                TRANSLATE_TEST_DURATION_SEC = int(args[0]) * 3600
                await message.channel.send(f"⏱️ مدة الترجمة أصبحت **{args[0]}** ساعة.")
            else:
                await message.channel.send("❗ استخدم `!وقت_الترجمة <عدد الساعات>`")
        elif cmd == "!تأخير_الاغلاق":
            if args:
                CLOSED_TICKET_CLOSE_DELAY = int(args[0]) * 60
                await message.channel.send(f"⏲️ تأخير الإغلاق أصبح **{args[0]}** دقيقة.")
            else:
                await message.channel.send("❗ استخدم `!تأخير_الاغلاق <عدد الدقائق>`")
        elif cmd == "!رابط_المعلومات":
            if args:
                INFO_CHANNEL_LINK = args[0]
                await message.channel.send(f"🔗 رابط المعلومات تم تحديثه.")
            else:
                await message.channel.send("❗ استخدم `!رابط_المعلومات <الرابط الجديد>`")

        # ── عرض الإعدادات ──
        elif cmd == "!الاعدادات":
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

        # ── إرسال رسالة مخصصة ──
        elif cmd == "!قل":
            if len(args) >= 2:
                ch_id = int(args[0])
                text = " ".join(args[1:])
                ch = self_bot.get_channel(ch_id) or await self_bot.fetch_channel(ch_id)
                await human_send_smart(ch, text)
                await message.channel.send(f"💬 تم الإرسال في <#{ch_id}>.")
            else:
                await message.channel.send("❗ استخدم `!قل <معرف القناة> <النص>`")

        # ── أوامر عامة ──
        elif cmd == "!بينغ":
            await message.channel.send("🏓 البوت يعمل!")
        elif cmd == "!احصائيات":
            category = self_bot.get_channel(CATEGORY_ID)
            if category:
                all_channels = category.channels
                opened = sum(1 for ch in all_channels if isinstance(ch, discord.TextChannel))
                success = sum(1 for ch in all_channels if isinstance(ch, discord.TextChannel) and "ناجح" in ch.name)
            else:
                opened = 0
                success = 0
            failed = stats['failed']
            closed = stats['closed']
            txt = (
                f"**📈 إحصائيات**\n"
                f"تكتات مفتوحة: {opened}\n"
                f"ناجحة: {success}\n"
                f"مغلقة: {closed}\n"
                f"فاشلة: {failed}"
            )
            await message.channel.send(txt)
        elif cmd == "!اغلاق_الكل":
            count = len(active_tests)
            for ch_id in list(active_tests.keys()):
                ch = self_bot.get_channel(ch_id) or await self_bot.fetch_channel(ch_id)
                await close_ticket(self_bot, ch)
            await message.channel.send(f"🔒 جارٍ إغلاق {count} تكت.")
        elif cmd == "!اعادة_تحميل":
            load_dotenv(override=True)
            await message.channel.send("🔄 تم إعادة تحميل ملف البيئة.")
        elif cmd == "!ايقاف":
            await message.channel.send("🛑 جارٍ إيقاف التشغيل...")
            await self_bot.close()

        # ── مساعدة بالعربية ──
        elif cmd == "!مساعدة":
            help_txt = (
                "**📚 دليل الأوامر**\n"
                "جميع الأوامر تبدأ بـ `!` وتستخدم مع البوت.\n\n"
                "**🔧 التحكم بالتخصصات**\n"
                "`!فتح_دمج` – فتح تقديم تحرير + تبييض\n"
                "`!اغلاق_دمج` – إغلاق تقديم تحرير + تبييض\n"
                "`!فتح_ترجمة` – فتح تقديم الترجمة\n"
                "`!اغلاق_ترجمة` – إغلاق تقديم الترجمة\n"
                "`!تبديل_دمج` – تبديل حالة تحرير + تبييض\n"
                "`!تبديل_ترجمة` – تبديل حالة الترجمة\n\n"
                "**📋 المراقبة والمتابعة**\n"
                "`!الحالة` – عرض حالة التقديمات والتكتات\n"
                "`!التكتات` – عرض التكتات النشطة\n"
                "`!احصائيات` – إحصائيات عامة (مفتوحة/ناجحة/مغلقة/فاشلة)\n\n"
                "**🎫 إدارة التكتات**\n"
                "`!اغلاق_تكت <id>` – إغلاق تكت محدد\n"
                "`!فشل_تكت <id>` – إرسال فشل لتكت محدد\n"
                "`!التالي <id>` – نقل تكت مدمج لمرحلة التحرير\n"
                "`!تذكير <id>` – إرسال تذكير فوري\n"
                "`!اغلاق_الكل` – إغلاق جميع التكتات\n\n"
                "**⚙️ الإعدادات**\n"
                "`!وقت_التحرير <ساعات>` – ضبط مدة التحرير\n"
                "`!وقت_التبييض <ساعات>` – ضبط مدة التبييض\n"
                "`!وقت_الترجمة <ساعات>` – ضبط مدة الترجمة\n"
                "`!تأخير_الاغلاق <دقائق>` – ضبط تأخير إغلاق التكت المغلق\n"
                "`!رابط_المعلومات <رابط>` – تغيير رابط المعلومات\n"
                "`!الاعدادات` – عرض الإعدادات الحالية\n\n"
                "**🛠️ عام**\n"
                "`!بينغ` – اختبار الاتصال\n"
                "`!قل <id> <نص>` – إرسال رسالة عبر الحساب\n"
                "`!اعادة_تحميل` – إعادة تحميل متغيرات البيئة\n"
                "`!ايقاف` – إيقاف البوت"
            )
            await message.channel.send(help_txt)

        else:
            await message.channel.send("❓ أمر غير معروف. استخدم `!مساعدة` لعرض الأوامر.")

    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {e}")