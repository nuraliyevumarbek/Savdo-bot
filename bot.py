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
from utils.webapp_auth import validate_init_data, extract_telegram_id
from utils.codes import gen_internal_code

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


# =====================================================================
#  MINI APP UCHUN API
# =====================================================================

async def _authed_user(request):
    if request.method == "GET":
        init_data = request.rel_url.query.get("init_data", "")
        body = {}
    else:
        body = await request.json()
        init_data = body.get("init_data", "")

    parsed = validate_init_data(init_data, BOT_TOKEN)
    if not parsed:
        return None, None, {}
    tg_id = extract_telegram_id(parsed)
    if not tg_id:
        return None, None, {}
    user = await db.get_user(tg_id)
    return user, tg_id, body


async def api_dashboard(request):
    user, tg_id, _ = await _authed_user(request)
    if not user:
        return web.json_response({"error": "Ruxsat yo'q, /start bosing"}, status=401)

    import datetime
    active = False
    if user["subscription_end"]:
        try:
            active = datetime.datetime.fromisoformat(user["subscription_end"]) > datetime.datetime.now()
        except ValueError:
            pass

    kirim_sum, chiqim_sum = await db.get_summary(user["id"])
    return web.json_response({
        "full_name": user["full_name"],
        "shop_name": user["shop_name"],
        "subscription_active": active,
        "subscription_end": user["subscription_end"][:10] if user["subscription_end"] else None,
        "kirim_sum": kirim_sum,
        "chiqim_sum": chiqim_sum,
    })


async def api_products(request):
    user, tg_id, _ = await _authed_user(request)
    if not user:
        return web.json_response({"error": "Ruxsat yo'q"}, status=401)
    products_list = await db.list_products(user["id"])
    return web.json_response({
        "products": [
            {"id": p["id"], "name": p["name"], "price": p["price"],
             "quantity": p["quantity"], "barcode": p["barcode"]}
            for p in products_list
        ]
    })


async def api_lookup(request):
    user, tg_id, body = await _authed_user(request)
    if not user:
        return web.json_response({"error": "Ruxsat yo'q"}, status=401)
    code = body.get("code", "").strip()
    product = await db.get_product_by_code(user["id"], code)
    if not product:
        found = await db.list_products(user["id"], search=code)
        product = found[0] if found else None
    if not product:
        return web.json_response({"found": False})
    return web.json_response({
        "found": True,
        "product": {"id": product["id"], "name": product["name"],
                     "price": product["price"], "quantity": product["quantity"]},
    })


async def api_move(request):
    user, tg_id, body = await _authed_user(request)
    if not user:
        return web.json_response({"error": "Ruxsat yo'q"}, status=401)

    product_id = body.get("product_id")
    move_type = body.get("type")
    qty = int(body.get("quantity", 0))

    if move_type not in ("kirim", "chiqim") or qty <= 0:
        return web.json_response({"error": "Noto'g'ri ma'lumot"}, status=400)

    product = await db.get_product(product_id)
    if not product or product["owner_id"] != user["id"]:
        return web.json_response({"error": "Mahsulot topilmadi"}, status=404)

    if move_type == "chiqim" and qty > product["quantity"]:
        return web.json_response({"error": "Omborda yetarli mahsulot yo'q"}, status=400)

    await db.add_transaction(user["id"], product_id, move_type, qty, product["price"])
    return web.json_response({"ok": True})


async def api_new_product(request):
    user, tg_id, body = await _authed_user(request)
    if not user:
        return web.json_response({"error": "Ruxsat yo'q"}, status=401)

    code = body.get("code", "").strip() or gen_internal_code()
    name = body.get("name", "").strip()
    price = int(body.get("price", 0))
    qty = int(body.get("quantity", 0))

    if not name or price <= 0:
        return web.json_response({"error": "Ma'lumotlarni to'liq kiriting"}, status=400)

    await db.add_product(user["id"], name, None, code, code, price, qty)
    return web.json_response({"ok": True})


async def health(request):
    """Render/UptimeRobot bot 'tirikligini' tekshirishi uchun oddiy endpoint."""
    return web.Response(text="Savdo Bot ishlab turibdi ✅")


async def run_web_server():
    """Render Web Service + Mini App + API."""
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/api/dashboard", api_dashboard)
    app.router.add_get("/api/products", api_products)
    app.router.add_post("/api/lookup", api_lookup)
    app.router.add_post("/api/move", api_move)
    app.router.add_post("/api/products/new", api_new_product)
    app.router.add_static("/", path=os.path.join(os.path.dirname(__file__), "static"), name="static")

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server {port}-portda ishga tushdi (Mini App + API)")


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

