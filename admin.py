from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from states import AdminBroadcast, AdminTariffAdd, AdminPromoAdd, AdminTicketReply
from keyboards import (
    admin_menu_kb, main_menu_kb, users_list_kb, user_manage_kb,
    broadcast_target_kb, cancel_kb,
)
from config import SUPER_ADMINS

router = Router()


def is_admin(user) -> bool:
    return bool(user) and (user["role"] in ("admin", "super_admin") or user["telegram_id"] in SUPER_ADMINS)


@router.message(Command("admin"))
async def open_admin(message: Message):
    user = await db.get_user(message.from_user.id)
    if not is_admin(user):
        await message.answer("⛔️ Sizda admin huquqi yo'q.")
        return
    await message.answer("👑 Admin panelga xush kelibsiz!", reply_markup=admin_menu_kb())


@router.message(F.text == "⬅️ Foydalanuvchi rejimi")
async def back_to_user(message: Message):
    await message.answer("Foydalanuvchi rejimiga o'tildi.", reply_markup=main_menu_kb())


# =====================================================================
#  DASHBOARD
# =====================================================================

@router.message(F.text == "📊 Dashboard")
async def dashboard(message: Message):
    user = await db.get_user(message.from_user.id)
    if not is_admin(user):
        return
    total_users = await db.count_users()
    active_subs = await db.count_active_subscriptions()
    pending = await db.get_pending_payments()
    tickets = await db.get_open_tickets()

    await message.answer(
        f"📊 <b>Dashboard</b>\n\n"
        f"👥 Jami foydalanuvchilar: {total_users}\n"
        f"✅ Faol obunalar: {active_subs}\n"
        f"💰 Kutilayotgan to'lovlar: {len(pending)}\n"
        f"🆘 Ochiq murojaatlar: {len(tickets)}"
    )


# =====================================================================
#  FOYDALANUVCHILAR RO'YXATI VA BOSHQARUVI
# =====================================================================

@router.message(F.text == "👥 Foydalanuvchilar")
async def list_users(message: Message):
    user = await db.get_user(message.from_user.id)
    if not is_admin(user):
        return
    users = await db.get_all_users()
    if not users:
        await message.answer("Foydalanuvchilar yo'q.")
        return
    await message.answer(
        f"👥 Jami: {len(users)} ta. Boshqarish uchun tanlang:",
        reply_markup=users_list_kb(users, page=0),
    )


@router.callback_query(F.data.startswith("admin_users_page_"))
async def users_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    users = await db.get_all_users()
    await callback.message.edit_reply_markup(reply_markup=users_list_kb(users, page=page))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_"))
async def user_detail(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    u = await db.get_user_by_id(user_id)
    if not u:
        await callback.answer("Topilmadi", show_alert=True)
        return
    text = (
        f"👤 <b>{u['full_name']}</b> (@{u['username']})\n"
        f"📞 {u['phone']}\n"
        f"🏪 {u['shop_name']}\n"
        f"🎭 Rol: {u['role']}\n"
        f"📅 Obuna: {u['subscription_end'][:10] if u['subscription_end'] else 'yo‘q'}\n"
        f"🚫 Bloklangan: {'ha' if u['is_blocked'] else 'yo‘q'}"
    )
    await callback.message.answer(text, reply_markup=user_manage_kb(u))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_toggleblock_"))
async def toggle_block(callback: CallbackQuery, bot: Bot):
    tg_id = int(callback.data.split("_")[2])
    u = await db.get_user(tg_id)
    await db.set_block_status(tg_id, not u["is_blocked"])
    await callback.answer("Holat yangilandi ✅")
    try:
        msg = "🚫 Hisobingiz bloklandi." if not u["is_blocked"] else "✅ Blok olib tashlandi."
        await bot.send_message(tg_id, msg)
    except Exception:
        pass


@router.callback_query(F.data.startswith("admin_extend_"))
async def extend_user(callback: CallbackQuery, bot: Bot):
    _, _, user_id, days = callback.data.split("_")
    new_end = await db.extend_subscription(int(user_id), int(days))
    u = await db.get_user_by_id(int(user_id))
    await callback.answer(f"+{days} kun qo'shildi ✅")
    try:
        await bot.send_message(
            u["telegram_id"],
            f"🎁 Admin tomonidan obunangizga +{days} kun qo'shildi.\n"
            f"Yangi muddat: {new_end.strftime('%d.%m.%Y')}",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("admin_makeadmin_"))
async def make_admin(callback: CallbackQuery):
    tg_id = int(callback.data.split("_")[2])
    await db.set_role(tg_id, "admin")
    await callback.answer("Endi admin ✅")


# =====================================================================
#  TARIFLAR
# =====================================================================

@router.message(F.text == "🏷 Tariflar")
async def show_tariffs_admin(message: Message):
    user = await db.get_user(message.from_user.id)
    if not is_admin(user):
        return
    tariffs = await db.get_active_tariffs()
    lines = ["🏷 <b>Faol tariflar:</b>\n"]
    for t in tariffs:
        lines.append(f"• {t['name']} — {t['price']:,} so'm — {t['duration_days']} kun".replace(",", " "))
    lines.append("\nYangi tarif qo'shish uchun: /add_tariff")
    await message.answer("\n".join(lines))


@router.message(Command("add_tariff"))
async def add_tariff_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not is_admin(user):
        return
    await message.answer("Yangi tarif nomini kiriting (masalan: '6 oylik'):", reply_markup=cancel_kb())
    await state.set_state(AdminTariffAdd.waiting_name)


@router.message(AdminTariffAdd.waiting_name)
async def add_tariff_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Narxini kiriting (so'mda):")
    await state.set_state(AdminTariffAdd.waiting_price)


@router.message(AdminTariffAdd.waiting_price)
async def add_tariff_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat son kiriting.")
        return
    await state.update_data(price=int(message.text))
    await message.answer("Muddatini kiriting (kunlarda):")
    await state.set_state(AdminTariffAdd.waiting_days)


@router.message(AdminTariffAdd.waiting_days)
async def add_tariff_days(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat son kiriting.")
        return
    data = await state.get_data()
    await db.add_tariff(data["name"], data["price"], int(message.text))
    await message.answer(f"✅ «{data['name']}» tarifi qo'shildi.", reply_markup=admin_menu_kb())
    await state.clear()


# =====================================================================
#  PROMO-KODLAR
# =====================================================================

@router.message(F.text == "🎟 Promo-kodlar")
async def promo_menu(message: Message):
    user = await db.get_user(message.from_user.id)
    if not is_admin(user):
        return
    await message.answer("Yangi promo-kod yaratish uchun: /add_promo")


@router.message(Command("add_promo"))
async def add_promo_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not is_admin(user):
        return
    await message.answer("Promo-kod matnini kiriting (masalan: YANGI2026):", reply_markup=cancel_kb())
    await state.set_state(AdminPromoAdd.waiting_code)


@router.message(AdminPromoAdd.waiting_code)
async def add_promo_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await message.answer("Necha kun bonus beriladi?")
    await state.set_state(AdminPromoAdd.waiting_days)


@router.message(AdminPromoAdd.waiting_days)
async def add_promo_days(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat son kiriting.")
        return
    await state.update_data(days=int(message.text))
    await message.answer("Nechta foydalanuvchi ishlata oladi (limit)?")
    await state.set_state(AdminPromoAdd.waiting_limit)


@router.message(AdminPromoAdd.waiting_limit)
async def add_promo_limit(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat son kiriting.")
        return
    data = await state.get_data()
    await db.create_promo(data["code"], data["days"], int(message.text))
    await message.answer(f"✅ Promo-kod yaratildi: {data['code'].upper()}", reply_markup=admin_menu_kb())
    await state.clear()


# =====================================================================
#  BROADCAST (XABAR YUBORISH)
# =====================================================================

@router.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not is_admin(user):
        return
    await message.answer("Kimlarga yuboramiz?", reply_markup=broadcast_target_kb())


@router.callback_query(F.data.in_(["bcast_all", "bcast_active"]))
async def broadcast_choose_target(callback: CallbackQuery, state: FSMContext):
    await state.update_data(target=callback.data)
    await callback.message.answer("Xabar matnini yuboring:")
    await state.set_state(AdminBroadcast.waiting_message)
    await callback.answer()


@router.message(AdminBroadcast.waiting_message)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    users = await db.get_all_users()
    sent, failed = 0, 0
    for u in users:
        if data["target"] == "bcast_active":
            if not u["subscription_end"]:
                continue
        try:
            await bot.send_message(u["telegram_id"], message.text)
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"✅ Yuborildi: {sent} ta, xato: {failed} ta", reply_markup=admin_menu_kb())
    await state.clear()


# =====================================================================
#  MUROJAATLAR (SUPPORT)
# =====================================================================

@router.message(F.text == "🆘 Murojaatlar")
async def show_tickets(message: Message):
    user = await db.get_user(message.from_user.id)
    if not is_admin(user):
        return
    tickets = await db.get_open_tickets()
    if not tickets:
        await message.answer("Ochiq murojaatlar yo'q ✅")
        return
    for t in tickets[:10]:
        await message.answer(
            f"🆘 #{t['id']}\n{t['message']}\n\nJavob berish: /reply_{t['id']} <matn>"
        )


@router.message(F.text.regexp(r"^/reply_(\d+)\s+(.+)$"))
async def reply_ticket(message: Message, bot: Bot):
    user = await db.get_user(message.from_user.id)
    if not is_admin(user):
        return
    import re
    m = re.match(r"^/reply_(\d+)\s+(.+)$", message.text, re.DOTALL)
    ticket_id, reply_text = int(m.group(1)), m.group(2)
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await message.answer("Murojaat topilmadi.")
        return
    await db.answer_ticket(ticket_id, reply_text)
    applicant = await db.get_user_by_id(ticket["user_id"])
    await bot.send_message(applicant["telegram_id"], f"💬 <b>Admin javobi:</b>\n{reply_text}")
    await message.answer("✅ Javob yuborildi.")
