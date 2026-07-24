import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

import database as db
from states import ProductAdd, StockMove, CodeGen
from keyboards import main_menu_kb, qr_barcode_choice_kb, cancel_kb
from utils.codes import (
    gen_internal_code, generate_qr_image, generate_barcode_image,
    read_code_from_image, qr_file_path, barcode_file_path_no_ext,
)
from middlewares_helpers import require_active_subscription

router = Router()


# =====================================================================
#  KIRIM / CHIQIM BOSHLASH
# =====================================================================

@router.message(F.text.in_(["📦 Kirim qilish", "📤 Chiqim qilish"]))
async def start_stock_move(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not await require_active_subscription(message, user):
        return

    move_type = "kirim" if "Kirim" in message.text else "chiqim"
    await state.update_data(move_type=move_type)
    await message.answer(
        "🔎 Mahsulot kodini kiriting, shtrix-kod/QR rasmini yuboring, "
        "yoki mahsulot nomini yozing:",
        reply_markup=cancel_kb(),
    )
    await state.set_state(StockMove.waiting_code)


@router.message(StockMove.waiting_code, F.text == "⬅️ Bekor qilish")
async def cancel_stock_move(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())


@router.message(StockMove.waiting_code, F.photo)
async def stock_move_by_photo(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    file = await message.bot.get_file(message.photo[-1].file_id)
    tmp_path = f"media/tmp_{message.from_user.id}.jpg"
    await message.bot.download_file(file.file_path, tmp_path)

    code = read_code_from_image(tmp_path)
    os.remove(tmp_path)

    if not code:
        await message.answer("❌ Kod aniqlanmadi. Yana aniqroq rasm yuboring yoki qo'lda kod kiriting.")
        return

    await _handle_code_lookup(message, state, user, code)


@router.message(StockMove.waiting_code)
async def stock_move_by_text(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    await _handle_code_lookup(message, state, user, message.text.strip())


async def _handle_code_lookup(message, state, user, code):
    product = await db.get_product_by_code(user["id"], code)

    if product:
        await state.update_data(product_id=product["id"], product_name=product["name"])
        data = await state.get_data()
        await message.answer(
            f"✅ Topildi: <b>{product['name']}</b>\n"
            f"Narxi: {product['price']:,} so'm\n"
            f"Hozirgi qoldiq: {product['quantity']} dona\n\n"
            f"{'Kirim' if data['move_type']=='kirim' else 'Chiqim'} qilinadigan miqdorni kiriting:".replace(",", " "),
            reply_markup=cancel_kb(),
        )
        await state.set_state(StockMove.waiting_quantity)
    else:
        # Yangi mahsulot sifatida qo'shish taklifi
        await state.update_data(new_code=code)
        await message.answer(
            f"⚠️ «{code}» kodli mahsulot topilmadi.\n"
            f"Yangi mahsulot sifatida qo'shishni xohlaysizmi?\n\n"
            f"Mahsulot nomini kiriting (yoki bekor qilish uchun ⬅️ tugmasini bosing):",
            reply_markup=cancel_kb(),
        )
        await state.set_state(ProductAdd.waiting_name)


@router.message(StockMove.waiting_quantity, F.text == "⬅️ Bekor qilish")
async def cancel_quantity(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())


@router.message(StockMove.waiting_quantity)
async def stock_move_quantity(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat son kiriting.")
        return

    data = await state.get_data()
    user = await db.get_user(message.from_user.id)
    product = await db.get_product(data["product_id"])
    qty = int(message.text)

    if data["move_type"] == "chiqim" and qty > product["quantity"]:
        await message.answer(
            f"❌ Omborda yetarli mahsulot yo'q! Qoldiq: {product['quantity']} dona."
        )
        return

    total = await db.add_transaction(user["id"], product["id"], data["move_type"], qty, product["price"])
    action = "Kirim" if data["move_type"] == "kirim" else "Chiqim"
    await message.answer(
        f"✅ {action} qilindi!\n"
        f"Mahsulot: {product['name']}\n"
        f"Miqdor: {qty} dona\n"
        f"Summa: {total:,} so'm".replace(",", " "),
        reply_markup=main_menu_kb(),
    )
    await state.clear()


# =====================================================================
#  YANGI MAHSULOT QO'SHISH (kod topilmaganda avtomatik boshlanadi)
# =====================================================================

@router.message(ProductAdd.waiting_name, F.text == "⬅️ Bekor qilish")
async def cancel_new_product(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())


@router.message(ProductAdd.waiting_name)
async def new_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Kategoriyasini kiriting (masalan: Ichimlik, Oziq-ovqat):")
    await state.set_state(ProductAdd.waiting_category)


@router.message(ProductAdd.waiting_category)
async def new_product_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text.strip())
    await message.answer("Narxini kiriting (so'mda, faqat son):")
    await state.set_state(ProductAdd.waiting_price)


@router.message(ProductAdd.waiting_price)
async def new_product_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat son kiriting.")
        return
    await state.update_data(price=int(message.text))
    await message.answer("Boshlang'ich miqdorini kiriting (dona):")
    await state.set_state(ProductAdd.waiting_quantity)


@router.message(ProductAdd.waiting_quantity)
async def new_product_quantity(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat son kiriting.")
        return

    data = await state.get_data()
    user = await db.get_user(message.from_user.id)
    internal_code = data.get("new_code") or gen_internal_code()

    product_id = await db.add_product(
        owner_id=user["id"],
        name=data["name"],
        category=data["category"],
        barcode=internal_code,
        qr_code=internal_code,
        price=data["price"],
        quantity=int(message.text),
    )
    await message.answer(
        f"✅ Yangi mahsulot qo'shildi: <b>{data['name']}</b>\n"
        f"Kodi: <code>{internal_code}</code>\n\n"
        f"Ushbu mahsulot uchun QR yoki shtrix-kod chop etishni xohlaysizmi?",
        reply_markup=qr_barcode_choice_kb(),
    )
    await state.update_data(last_product_code=internal_code)
    await state.clear()
    # kod chop etish tugmalari alohida callback orqali ishlaydi (pastda)


# =====================================================================
#  QR / SHTRIX-KOD YARATISH
# =====================================================================

@router.message(F.text == "🏷 QR/Shtrix yaratish")
async def gen_code_menu(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not await require_active_subscription(message, user):
        return
    products = await db.list_products(user["id"])
    if not products:
        await message.answer("Sizda hali mahsulot yo'q. Avval kirim orqali mahsulot qo'shing.")
        return
    text = "Kodi kerak bo'lgan mahsulot nomini yozing:\n\n"
    text += "\n".join(f"• {p['name']} — <code>{p['barcode']}</code>" for p in products[:20])
    await message.answer(text)
    await state.set_state(CodeGen.waiting_product_name)


@router.message(CodeGen.waiting_product_name)
async def maybe_generate_for_product(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    products = await db.list_products(user["id"], search=message.text.strip())
    if not products:
        await message.answer("Topilmadi. Qaytadan urinib ko'ring.")
        return
    product = products[0]
    await state.update_data(code_target=product["barcode"])
    await message.answer(f"«{product['name']}» uchun qaysi turdagi kod kerak?", reply_markup=qr_barcode_choice_kb())


@router.callback_query(F.data.in_(["gen_qr", "gen_barcode"]))
async def send_generated_code(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    code = data.get("code_target") or data.get("last_product_code")
    if not code:
        await callback.answer("Kod topilmadi, qaytadan urinib ko'ring.", show_alert=True)
        return

    if callback.data == "gen_qr":
        path = qr_file_path(code)
        generate_qr_image(code, path)
        caption = f"🔳 QR kod tayyor!\nKod: {code}"
    else:
        base = barcode_file_path_no_ext(code)
        path = generate_barcode_image(code, base)
        caption = f"📊 Shtrix-kod tayyor!\nKod: {code}"

    await callback.message.answer_photo(FSInputFile(path), caption=caption)
    await callback.answer()
    await state.clear()


# =====================================================================
#  KOD SKANERLASH (mustaqil, faqat ma'lumot ko'rish uchun)
# =====================================================================

@router.message(F.text == "📷 Kod skanerlash")
async def ask_scan(message: Message):
    await message.answer(
        "📷 Shtrix-kod yoki QR-kod rasmini yuboring — men uni o'qib, "
        "mahsulot ma'lumotini topib beraman.\n\n"
        "Yoki to'g'ridan-to'g'ri «📦 Kirim qilish» / «📤 Chiqim qilish» "
        "tugmasidan foydalanib, kodni u yerda skanerlashingiz mumkin."
    )


# =====================================================================
#  OMBOR RO'YXATI
# =====================================================================

@router.message(F.text == "🗂 Ombor")
async def show_warehouse(message: Message):
    user = await db.get_user(message.from_user.id)
    if not await require_active_subscription(message, user):
        return
    products = await db.list_products(user["id"])
    if not products:
        await message.answer("Omboringiz hozircha bo'sh.")
        return
    lines = ["🗂 <b>Ombordagi mahsulotlar:</b>\n"]
    for p in products:
        lines.append(f"• {p['name']} — {p['quantity']} dona — {p['price']:,} so'm".replace(",", " "))
    await message.answer("\n".join(lines))


# =====================================================================
#  HISOBOT
# =====================================================================

@router.message(F.text == "📊 Hisobot")
async def show_report(message: Message):
    user = await db.get_user(message.from_user.id)
    if not await require_active_subscription(message, user):
        return
    kirim_sum, chiqim_sum = await db.get_summary(user["id"])
    foyda = kirim_sum - chiqim_sum
    await message.answer(
        f"📊 <b>Umumiy hisobot</b>\n\n"
        f"📦 Kirim: {kirim_sum:,} so'm\n"
        f"📤 Chiqim: {chiqim_sum:,} so'm\n"
        f"💰 Farq: {foyda:,} so'm".replace(",", " ")
    )
