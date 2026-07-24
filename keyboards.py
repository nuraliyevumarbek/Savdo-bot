from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from config import WEBAPP_URL


# ---------------- Foydalanuvchi asosiy menyusi ----------------

def main_menu_kb():
    kb = ReplyKeyboardBuilder()
    if WEBAPP_URL:
        kb.button(text="📱 Mini App ochish", web_app=WebAppInfo(url=WEBAPP_URL))
    kb.button(text="📦 Kirim qilish")
    kb.button(text="📤 Chiqim qilish")
    kb.button(text="🗂 Ombor")
    kb.button(text="📊 Hisobot")
    kb.button(text="🏷 QR/Shtrix yaratish")
    kb.button(text="📷 Kod skanerlash")
    kb.button(text="💳 Obuna")
    kb.button(text="🎁 Referal")
    kb.button(text="🆘 Yordam")
    kb.adjust(1, 2, 2, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


def contact_request_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📱 Raqamni yuborish", request_contact=True)
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def cancel_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="⬅️ Bekor qilish")
    return kb.as_markup(resize_keyboard=True)


# ---------------- Obuna / to'lov ----------------

def tariffs_kb(tariffs):
    kb = InlineKeyboardBuilder()
    for t in tariffs:
        kb.button(
            text=f"{t['name']} — {t['price']:,} so'm".replace(",", " "),
            callback_data=f"tariff_{t['id']}",
        )
    kb.adjust(1)
    return kb.as_markup()


def payment_review_kb(payment_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"pay_ok_{payment_id}")
    kb.button(text="❌ Rad etish", callback_data=f"pay_no_{payment_id}")
    kb.adjust(2)
    return kb.as_markup()


# ---------------- Kirim/Chiqim tur tanlash ----------------

def qr_barcode_choice_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔳 QR kod", callback_data="gen_qr")
    kb.button(text="📊 Shtrix-kod", callback_data="gen_barcode")
    kb.adjust(2)
    return kb.as_markup()


# ---------------- ADMIN PANEL ----------------

def admin_menu_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📊 Dashboard")
    kb.button(text="👥 Foydalanuvchilar")
    kb.button(text="💰 To'lovlar (kutilmoqda)")
    kb.button(text="🏷 Tariflar")
    kb.button(text="🎟 Promo-kodlar")
    kb.button(text="📢 Xabar yuborish")
    kb.button(text="🆘 Murojaatlar")
    kb.button(text="⬅️ Foydalanuvchi rejimi")
    kb.adjust(2, 2, 2, 1, 1)
    return kb.as_markup(resize_keyboard=True)


def users_list_kb(users, page=0, page_size=8):
    kb = InlineKeyboardBuilder()
    start = page * page_size
    chunk = users[start:start + page_size]
    for u in chunk:
        label = f"{u['full_name'] or u['username'] or u['telegram_id']}"
        kb.button(text=label, callback_data=f"admin_user_{u['id']}")
    kb.adjust(1)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_users_page_{page-1}"))
    if start + page_size < len(users):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_users_page_{page+1}"))
    if nav:
        kb.row(*nav)
    return kb.as_markup()


def user_manage_kb(user):
    kb = InlineKeyboardBuilder()
    block_text = "🔓 Blokdan chiqarish" if user["is_blocked"] else "🚫 Bloklash"
    kb.button(text=block_text, callback_data=f"admin_toggleblock_{user['telegram_id']}")
    kb.button(text="➕ 30 kun qo'shish", callback_data=f"admin_extend_{user['id']}_30")
    kb.button(text="👑 Admin qilish", callback_data=f"admin_makeadmin_{user['telegram_id']}")
    kb.adjust(1)
    return kb.as_markup()


def broadcast_target_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📣 Barchaga", callback_data="bcast_all")
    kb.button(text="✅ Faqat faol obunalilarga", callback_data="bcast_active")
    kb.adjust(1)
    return kb.as_markup()

