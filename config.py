import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CATEGORY_ID = int(os.getenv("CATEGORY_ID"))
OWNER_ID = int(os.getenv("OWNER_ID"))
PROXY_URL = os.getenv("PROXY_URL")
CONTROL_CHANNEL_ID = int(os.getenv("CONTROL_CHANNEL_ID", "0"))

DELAY_MIN = float(os.getenv("DELAY_MIN", "1"))
DELAY_MAX = float(os.getenv("DELAY_MAX", "3"))

EDIT_WHITENING_OPEN = True
TRANSLATE_OPEN = True

COMBINED_TEST_DURATION_SEC = 7 * 3600
TRANSLATE_TEST_DURATION_SEC = 2 * 3600
CLOSED_TICKET_CLOSE_DELAY = 900

INFO_CHANNEL_LINK = "https://discord.com/channels/1202306392757915688/1202559461433286716"

FIRST_MSG_TRANS = "اسم اختبار ترجمة"
SECOND_MSG_TRANS = "اختبار ترجمة"

FIRST_MSG_COMBINED = "اسم اختبار تحرير + تبييض"
SECOND_MSG_COMBINED = "اختبار تحرير"

THIRD_MSG_TRANS = (
    "# شكراً لتقديمك يا {mention}\n\n"
    "**اختبارك الانجليزي يبدأ من هذه اللحظة**\n\n"
    "> أمامك **ساعتان** فقط لإنهاء الاختبار كاملاً\n\n"
    "- يرجى قراءة التعليمات جيداً قبل البدء\n"
    "- التسليم عبر رابط **Google Docs** فقط\n\n"
    "**بالتوفيق!**\n\n"
    "-# ملاحظة: أي سؤال أو استفسار بخصوص الاختبار اسأل في التكت وانتظرني أو انتظر قدوم الإدارة"
)

THIRD_MSG_COMBINED = (
    "# شكراً لتقديمك يا {mention}\n\n"
    "**اختبارك يبدأ من هذه اللحظة** ⏳\n\n"
    "> أمامك **7 ساعات** فقط لإنهاء الاختبار كاملاً\n\n"
    "---\n\n"
    "## 📋 التعليمات – اقرأها جيداً قبل البدء\n\n"
    "1. عند فتح رابط الاختبار، ستجد عنصرين:\n"
    "   - مجلد باسم **\"سحب\"**\n"
    "   - ملف الترجمة (موجود تحت المجلد مباشرة)\n\n"
    "2. ابدأ **بحفظ ملف الترجمة** لديك أولاً، ثم ادخل إلى مجلد **\"سحب\"**\n\n"
    "3. داخل مجلد السحب، ستجد الصور المطلوب تبييضها وتحريرها – قم **بتحميلها جميعاً** كخطوة أولى\n\n"
    "4. بعدها ابدأ العمل بالطريقة التي تفضلها:\n"
    "   - تبييض كل الصور دفعة واحدة ثم التحرير\n"
    "   - أو معالجة كل صورة خطوة بخطوة\n\n"
    "---\n\n"
    "## 📤 التسليم\n\n"
    "- عندما تنتهي **قبل انتهاء الوقت**، سلّم عملك عبر **رابط Google Drive واحد** يحتوي على:\n"
    "  - صور الاختبار بعد التبييض والتحرير\n\n"
    "**بالتوفيق!** 🍀\n\n"
    "---\n\n"
    "-# ملاحظة: أي سؤال أو استفسار بخصوص الاختبار اسأل في التكت وانتظرني أو انتظر قدوم الإدارة"
)

FAIL_MSG = (
    "{mention} انتهى وقت الاختبار للأسف 🤷‍♂️.\n"
    "لقد فشلت في الاختبار. سيتم إغلاق التكت بعد ساعة."
)