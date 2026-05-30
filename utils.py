import re
import asyncio

def get_typing_duration(text):
    """حساب مدة محاكاة الكتابة بناءً على عدد الكلمات (0.35 ثانية لكل كلمة)"""
    word_count = len(text.split())
    duration = word_count * 0.35
    return max(1.5, min(duration, 8.0))  # بين 1.5 و 8 ثوانٍ

def extract_link(message, pattern):
    """
    يحاول إيجاد رابط يطابق النمط في محتوى الرسالة أو في أي إيمبد مرفق.
    يعيد الرابط كسلسلة إذا وُجد، وإلا None.
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

async def human_send_smart(channel, content):
    """يُظهر حالة الكتابة لمدة تتناسب مع طول الرسالة ثم يرسلها"""
    duration = get_typing_duration(content)
    async with channel.typing():
        await asyncio.sleep(duration)
    await channel.send(content)