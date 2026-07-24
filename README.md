# 🏪 Savdo Bot — Telegram orqali kirim-chiqim, QR/shtrix-kod, admin panel

## Imkoniyatlar
- 📦 Kirim / 📤 Chiqim — mahsulot kodini skanerlab yoki yozib qayd qilish
- 🏷 Har bir mahsulot uchun QR kod va shtrix-kod (Code128) yaratish va chop etish
- 📷 Kamera orqali olingan rasmdan QR/shtrix-kodni avtomatik o'qish (pyzbar)
- 🗂 Ombor holati, 📊 Kirim/chiqim hisobot
- 💳 Oylik obuna: tarif tanlash → chek screenshot yuborish → admin tasdiqlaydi
- 🎁 Referal tizimi (do'stni taklif qilib bonus kun olish)
- 🎟 Promo-kodlar (/promo)
- 📢 Admin broadcast (hammaga / faqat faol obunalilarga)
- 🆘 Support/murojaat bo'limi
- ⏰ Obuna tugashidan 1 kun oldin avtomatik ogohlantirish
- 👑 To'liq admin panel: Dashboard, foydalanuvchilar, tariflar, bloklash

## O'rnatish

```bash
cd savdo_bot
python3 -m venv venv
source venv/bin/activate        # Windowsda: venv\Scripts\activate
pip install -r requirements.txt
```

### pyzbar uchun qo'shimcha (rasmdan kod o'qish uchun)
- **Ubuntu/Debian:** `sudo apt-get install libzbar0`
- **Windows:** qo'shimcha o'rnatish shart emas (DLL paket bilan keladi)
- **macOS:** `brew install zbar`

### Sozlash
`.env.example` faylini `.env` deb nusxalang va to'ldiring:

```bash
cp .env.example .env
```

- `BOT_TOKEN` — @BotFather dan olingan token
- `SUPER_ADMINS` — sizning Telegram ID raqamingiz (bir nechta bo'lsa vergul bilan). ID ni bilish uchun @userinfobot ga yozing.
- `PAYMENT_CARD_NUMBER`, `PAYMENT_CARD_OWNER` — to'lov qabul qilinadigan karta

### Ishga tushirish

```bash
python bot.py
```

## Foydalanish oqimi

1. Foydalanuvchi `/start` bosadi → telefon raqami va do'kon nomini kiritadi → 3 kunlik bepul sinov beriladi.
2. **Kirim qilish**: mahsulot kodini yozadi/skanerlaydi → topilmasa, yangi mahsulot sifatida qo'shish so'raladi (nomi, kategoriyasi, narxi, miqdori) → avtomatik ichki kod yaratiladi → QR yoki shtrix-kod chop etish taklif qilinadi.
3. **Chiqim qilish**: xuddi shunday, lekin ombordan ayiradi (yetarli bo'lmasa xato beradi).
4. **QR/Shtrix yaratish**: istalgan vaqt mahsulot nomini yozib, kodini qayta chop etish mumkin — buni chop etib, mahsulotga yopishtirish mumkin, keyingi safar shtrix-kod skaneridan o'tkazsa ham tanийdi (chunki bot ichki kodni ham, tashqi shtrix-kodni ham bir xil maydonga yozadi — agar haqiqiy fabrika shtrix-kodini ishlatmoqchi bo'lsangiz, mahsulot qo'shishda o'sha kodni "kod" sifatida kiritishingiz mumkin).
5. **Obuna**: tarif tanlaydi → kartaga to'lov qiladi → chek rasmini yuboradi → barcha adminlarga tasdiqlash tugmalari bilan yuboriladi → admin tasdiqlasa, obuna avtomatik uzaytiriladi.
6. **Admin panel**: `/admin` buyrug'i (yoki `.env` dagi SUPER_ADMINS uchun avtomatik) orqali ochiladi.

## Haqiqiy shtrix-kod skaner apparati bilan ishlash
Ko'pchilik USB/Bluetooth shtrix-kod skanerlari klaviatura kabi ishlaydi — ya'ni skanerlangan kod matn sifatida "yoziladi" va Enter bosiladi. Shuning uchun bot allaqachon **matn kiritish** orqali kodni qabul qiladi (StockMove.waiting_code holatida) — telefon/kompyuterga ulangan fizik skanerdan foydalansangiz ham, kod avtomatik shu maydonga tushadi va qidiriladi. Qo'shimcha sozlash shart emas.

## Keyingi rivojlantirish g'oyalari
- PostgreSQL ga o'tish (ko'p foydalanuvchi/yuqori yuklama uchun)
- To'lovni Payme/Click API orqali avtomatlashtirish
- Excel/PDF hisobot eksporti
- Har bir do'kon uchun bir nechta xodim (kassir) qo'shish huquqi tizimi
- Web-based admin dashboard (Flask/FastAPI) — grafik statistikalar bilan
