import os
from dotenv import load_dotenv

load_dotenv()

# --- Asosiy sozlamalar ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "SIZNING_BOT_TOKENINGIZ")

# Bosh admin(lar) telegram ID lari (vergul bilan ajratib bir nechta yozish mumkin)
SUPER_ADMINS = [int(x) for x in os.getenv("SUPER_ADMINS", "").split(",") if x.strip().isdigit()]

# Ma'lumotlar bazasi fayli
DB_PATH = os.getenv("DB_PATH", "savdo_bot.db")

# Sinov (trial) muddati - kunlarda, ro'yxatdan o'tgan har bir yangi foydalanuvchiga
TRIAL_DAYS = 3

# Referal bonusi - kunlarda (do'stni taklif qilsa necha kun bonus beriladi)
REFERRAL_BONUS_DAYS = 5

# To'lov uchun karta raqami (admin qo'lda tasdiqlaganda foydalanuvchiga ko'rsatiladi)
PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "8600 XXXX XXXX XXXX")
PAYMENT_CARD_OWNER = os.getenv("PAYMENT_CARD_OWNER", "F.I.Sh.")

# QR/barcode fayllar saqlanadigan papka
MEDIA_DIR = "media"
QR_DIR = os.path.join(MEDIA_DIR, "qr_codes")
BARCODE_DIR = os.path.join(MEDIA_DIR, "barcodes")

for d in (MEDIA_DIR, QR_DIR, BARCODE_DIR):
    os.makedirs(d, exist_ok=True)
