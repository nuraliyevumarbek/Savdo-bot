from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import database as db
from states import Registration
from keyboards import main_menu_kb, contact_request_kb, admin_menu_kb
from config import REFERRAL_BONUS_DAYS

router = Router()


@router.message(CommandStart(deep_link=True))
async def start_with_ref(message: Message, command: CommandObject, state: FSMContext):
    ref_code = command.args
    await _start_flow(message, state, ref_code)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await _start_flow(message, state, None)


async def _start_flow(message: Message, state: FSMContext, ref_code):
    user = await db.get_user(message.from_user.id)

    if user and user["is_registered"]:
        if user["role"] in ("admin", "super_admin"):
            await message.answer(
                f"Xush kelibsiz, {user['full_name']}! 👑\nAdmin panel faol.",
                reply_markup=admin_menu_kb(),
            )
        else:
            await message.answer(
                f"Xush kelibsiz, {user['full_name']}! 🏪 «{user['shop_name']}»",
                reply_markup=main_menu_kb(),
            )
        return

    if not user:
        user = await db.create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            referred_by_code=ref_code,
        )
        # Agar referal orqali kelgan bo'lsa - taklif qilganga bonus
        if user["referred_by"]:
            await db.extend_subscription(user["referred_by"], REFERRAL_BONUS_DAYS)
            referrer = await db.get_user_by_id(user["referred_by"])
            if referrer:
                try:
                    from bot import bot as _bot
                    await _bot.send_message(
                        referrer["telegram_id"],
                        f"🎉 Sizning taklifingiz bilan yangi foydalanuvchi qo'shildi!\n"
                        f"Sizga +{REFERRAL_BONUS_DAYS} kun bonus obuna qo'shildi.",
                    )
                except Exception:
                    pass

    await message.answer(
        "👋 Assalomu alaykum! <b>Savdo Bot</b>ga xush kelibsiz.\n\n"
        "Bu bot orqali siz do'koningiz kirim-chiqimini yuritishingiz, "
        "QR/shtrix-kod orqali mahsulotlarni tez qayd qilishingiz mumkin.\n\n"
        "Ro'yxatdan o'tish uchun telefon raqamingizni yuboring 👇",
        reply_markup=contact_request_kb(),
    )
    await state.set_state(Registration.waiting_phone)


@router.message(Registration.waiting_phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await message.answer(
        "Endi do'koningiz/biznesingiz nomini kiriting:\n(masalan: «Alisher do'koni»)"
    )
    await state.set_state(Registration.waiting_shop_name)


@router.message(Registration.waiting_phone)
async def get_phone_invalid(message: Message):
    await message.answer(
        "Iltimos, pastdagi «📱 Raqamni yuborish» tugmasi orqali raqamingizni yuboring."
    )


@router.message(Registration.waiting_shop_name)
async def get_shop_name(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.complete_registration(message.from_user.id, data["phone"], message.text.strip())
    await state.clear()
    await message.answer(
        f"✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n"
        f"Sizga 3 kunlik <b>bepul sinov</b> muddati taqdim etildi.\n\n"
        f"Quyidagi menyudan foydalaning 👇",
        reply_markup=main_menu_kb(),
    )
