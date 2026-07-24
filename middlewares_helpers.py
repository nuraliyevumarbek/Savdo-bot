import datetime
from aiogram.types import Message


async def require_active_subscription(message: Message, user) -> bool:
    """Obuna faolligini tekshiradi, faol bo'lmasa ogohlantirib False qaytaradi."""
    if not user:
        await message.answer("Iltimos, avval /start buyrug'ini bosing.")
        return False

    if user["is_blocked"]:
        await message.answer("🚫 Sizning hisobingiz bloklangan. Admin bilan bog'laning.")
        return False

    if not user["subscription_end"]:
        await message.answer("❗️ Obunangiz mavjud emas. «💳 Obuna» bo'limidan tarif tanlang.")
        return False

    try:
        end = datetime.datetime.fromisoformat(user["subscription_end"])
    except ValueError:
        end = None

    if not end or end < datetime.datetime.now():
        await message.answer(
            "⏰ Obuna muddatingiz tugagan!\n"
            "Davom etish uchun «💳 Obuna» bo'limidan tarif tanlab, to'lovni amalga oshiring."
        )
        return False

    return True
