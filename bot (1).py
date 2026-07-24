import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, SUPER_ADMINS
import database as db

from handlers import start, products, payments, referral, support, admin

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Handlerlarni ro'yxatdan o'tkazish (tartib muhim!)
dp.include_router(start.router)
dp.include_router(admin.router)
dp.include_router(payments.router)
dp.include_router(referral.router)
dp.include_router(support.router)
dp.include_router(products.router)


async def health(request):
    """Render/UptimeRobot bot 'tirikligini' tekshirishi uchun oddiy endpoint."""
    return web.Response(text="Savdo Bot ishlab turibdi ✅")


async def run_web_server():
    """Render Web Service sifatida ishlashi uchun minimal http server."""
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server {port}-portda ishga tushdi (health check uchun)")


async def subscription_reminder_task():
    """Har kuni obunasi ertaga tugaydigan foydalanuvchilarga ogohlantirish yuboradi."""
    while True:
        try:
            users = await db.users_expiring_soon(days_ahead=1)
            for u in users:
                try:
                    await bot.send_message(
                        u["telegram_id"],
                        "⏰ <b>Diqqat!</b> Obunangiz ertaga tugaydi.\n"
                        "Uzluksiz foydalanish uchun «💳 Obuna» bo'limidan yangilang.",
                    )
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"Reminder xatosi: {e}")
        await asyncio.sleep(24 * 60 * 60)  # har 24 soatda


async def ensure_super_admins():
    for admin_id in SUPER_ADMINS:
        user = await db.get_user(admin_id)
        if user:
            await db.set_role(admin_id, "super_admin")


async def main():
    await db.init_db()
    await ensure_super_admins()
    asyncio.create_task(subscription_reminder_task())
    asyncio.create_task(run_web_server())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
