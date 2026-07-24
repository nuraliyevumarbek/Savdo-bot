from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from states import Payment
from keyboards import tariffs_kb, payment_review_kb, main_menu_kb
from config import PAYMENT_CARD_NUMBER, PAYMENT_CARD_OWNER, SUPER_ADMINS

router = Router()


@router.message(F.text == "💳 Obuna")
async def show_tariffs(message: Message):
    user = await db.get_user(message.from_user.id)
    tariffs = await db.get_active_tariffs()

    status = "❌ Faol emas"
    if user["subscription_end"]:
        status = f"tugash sanasi: {user['subscription_end'][:10]}"

    await message.answer(
        f"💳 <b>Obuna holati:</b> {status}\n\n"
        f"Quyidagi tariflardan birini tanlang:",
        reply_markup=tariffs_kb(tariffs),
    )


@router.callback_query(F.data.startswith("tariff_"))
async def choose_tariff(callback: CallbackQuery, state: FSMContext):
    tariff_id = int(callback.data.split("_")[1])
    tariff = await db.get_tariff(tariff_id)
    await state.update_data(tariff_id=tariff_id)

    await callback.message.answer(
        f"Siz <b>{tariff['name']}</b> tarifini tanladingiz — {tariff['price']:,} so'm.\n\n"
        f"To'lovni quyidagi kartaga o'tkazing:\n"
        f"💳 <code>{PAYMENT_CARD_NUMBER}</code>\n"
        f"👤 {PAYMENT_CARD_OWNER}\n\n"
        f"To'lov chekining rasmini (screenshot) shu yerga yuboring 📸".replace(",", " ")
    )
    await state.set_state(Payment.waiting_screenshot)
    await callback.answer()


@router.message(Payment.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = await db.get_user(message.from_user.id)
    tariff = await db.get_tariff(data["tariff_id"])

    payment_id = await db.create_payment(
        user_id=user["id"],
        tariff_id=tariff["id"],
        amount=tariff["price"],
        screenshot_file_id=message.photo[-1].file_id,
    )

    await message.answer(
        "✅ To'lov cheki qabul qilindi! Admin tomonidan tekshirilgach, "
        "obunangiz avtomatik faollashadi. Iltimos, kuting.",
        reply_markup=main_menu_kb(),
    )
    await state.clear()

    # Barcha super-adminlarga yuborish
    caption = (
        f"💰 <b>Yangi to'lov</b>\n"
        f"Foydalanuvchi: {user['full_name']} (@{user['username']})\n"
        f"Tarif: {tariff['name']} — {tariff['price']:,} so'm\n"
        f"ID: {payment_id}".replace(",", " ")
    )
    for admin_id in SUPER_ADMINS:
        try:
            await bot.send_photo(
                admin_id, message.photo[-1].file_id, caption=caption,
                reply_markup=payment_review_kb(payment_id),
            )
        except Exception:
            pass


@router.message(Payment.waiting_screenshot)
async def receive_screenshot_invalid(message: Message):
    await message.answer("Iltimos, to'lov chekining rasmini (screenshot/photo) yuboring.")


@router.callback_query(F.data.startswith("pay_ok_"))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    payment_id = int(callback.data.split("_")[2])
    payment = await db.get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        await callback.answer("Bu to'lov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    tariff = await db.get_tariff(payment["tariff_id"])
    new_end = await db.extend_subscription(payment["user_id"], tariff["duration_days"])
    await db.review_payment(payment_id, "approved")

    user = await db.get_user_by_id(payment["user_id"])
    await bot.send_message(
        user["telegram_id"],
        f"✅ To'lovingiz tasdiqlandi!\n"
        f"Obunangiz {new_end.strftime('%d.%m.%Y')} sanagacha uzaytirildi.",
    )
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ TASDIQLANDI"
    )
    await callback.answer("Tasdiqlandi ✅")


@router.callback_query(F.data.startswith("pay_no_"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    payment_id = int(callback.data.split("_")[2])
    payment = await db.get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        await callback.answer("Bu to'lov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await db.review_payment(payment_id, "rejected")
    user = await db.get_user_by_id(payment["user_id"])
    await bot.send_message(
        user["telegram_id"],
        "❌ To'lovingiz rad etildi. Chek noto'g'ri yoki summa mos kelmadi. "
        "Qayta urinib ko'ring yoki «🆘 Yordam» orqali admin bilan bog'laning.",
    )
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ RAD ETILDI"
    )
    await callback.answer("Rad etildi ❌")
