from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import database as db
from states import Support
from keyboards import main_menu_kb, cancel_kb
from config import SUPER_ADMINS

router = Router()


@router.message(F.text == "🆘 Yordam")
async def ask_support(message: Message, state: FSMContext):
    await message.answer(
        "Savolingiz yoki muammoingizni yozing, admin tez orada javob beradi:",
        reply_markup=cancel_kb(),
    )
    await state.set_state(Support.waiting_message)


@router.message(Support.waiting_message, F.text == "⬅️ Bekor qilish")
async def cancel_support(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())


@router.message(Support.waiting_message)
async def send_support(message: Message, state: FSMContext, bot: Bot):
    user = await db.get_user(message.from_user.id)
    ticket_id = await db.create_ticket(user["id"], message.text)
    await message.answer(
        "✅ Murojaatingiz qabul qilindi. Tez orada javob beramiz.",
        reply_markup=main_menu_kb(),
    )
    await state.clear()

    for admin_id in SUPER_ADMINS:
        try:
            await bot.send_message(
                admin_id,
                f"🆘 <b>Yangi murojaat #{ticket_id}</b>\n"
                f"Foydalanuvchi: {user['full_name']} (@{user['username']})\n\n"
                f"{message.text}\n\n"
                f"Javob berish uchun: /reply_{ticket_id}",
            )
        except Exception:
            pass
