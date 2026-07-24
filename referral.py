from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import database as db
from states import PromoEnter

router = Router()


@router.message(F.text == "🎁 Referal")
async def referral_info(message: Message):
    user = await db.get_user(message.from_user.id)
    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user['referral_code']}"
    count = await db.get_referral_stats(user["id"])

    await message.answer(
        f"🎁 <b>Referal tizimi</b>\n\n"
        f"Do'stingizni taklif qiling — u ro'yxatdan o'tsa, sizga bonus kunlar qo'shiladi!\n\n"
        f"🔗 Sizning havolangiz:\n{link}\n\n"
        f"👥 Siz orqali qo'shilganlar: {count} kishi\n\n"
        f"🎟 Promo-kodingiz bormi? /promo buyrug'i orqali kiriting."
    )


@router.message(Command("promo"))
async def ask_promo(message: Message, state: FSMContext):
    await message.answer("Promo-kodni kiriting:")
    await state.set_state(PromoEnter.waiting_code)


@router.message(PromoEnter.waiting_code)
async def apply_promo(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    promo = await db.get_promo(code)
    user = await db.get_user(message.from_user.id)

    if not promo or not promo["is_active"]:
        await message.answer("❌ Bunday promo-kod topilmadi yoki faol emas.")
        await state.clear()
        return

    if promo["used_count"] >= promo["usage_limit"]:
        await message.answer("❌ Bu promo-kodning limiti tugagan.")
        await state.clear()
        return

    if await db.has_used_promo(promo["id"], user["id"]):
        await message.answer("❌ Siz bu promo-kodni allaqachon ishlatgansiz.")
        await state.clear()
        return

    await db.use_promo(promo["id"], user["id"])
    new_end = await db.extend_subscription(user["id"], promo["bonus_days"])
    await message.answer(
        f"✅ Promo-kod qabul qilindi! +{promo['bonus_days']} kun qo'shildi.\n"
        f"Obunangiz {new_end.strftime('%d.%m.%Y')} sanagacha amal qiladi."
    )
    await state.clear()
