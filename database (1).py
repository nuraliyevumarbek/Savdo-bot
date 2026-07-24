import aiosqlite
import datetime
import random
import string
from config import DB_PATH, TRIAL_DAYS

# ==========================================================
#  JADVALLARNI YARATISH
# ==========================================================

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    phone TEXT,
    shop_name TEXT,
    role TEXT DEFAULT 'user',           -- 'user' | 'admin' | 'super_admin'
    referral_code TEXT UNIQUE,
    referred_by INTEGER,                -- users.id
    subscription_end TEXT,              -- ISO sana
    is_blocked INTEGER DEFAULT 0,
    is_registered INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS tariffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price INTEGER NOT NULL,             -- so'mda
    duration_days INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,          -- users.id (do'kon egasi)
    name TEXT NOT NULL,
    category TEXT,
    barcode TEXT,
    qr_code TEXT UNIQUE,                -- ichki noyob QR kod matni
    price INTEGER NOT NULL,
    quantity INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    type TEXT NOT NULL,                 -- 'kirim' | 'chiqim'
    quantity INTEGER NOT NULL,
    price INTEGER NOT NULL,
    total INTEGER NOT NULL,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tariff_id INTEGER,
    amount INTEGER,
    screenshot_file_id TEXT,
    status TEXT DEFAULT 'pending',      -- 'pending' | 'approved' | 'rejected'
    admin_comment TEXT,
    created_at TEXT,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS promo_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    bonus_days INTEGER NOT NULL,
    usage_limit INTEGER DEFAULT 1,
    used_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS promo_usages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    promo_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    used_at TEXT
);

CREATE TABLE IF NOT EXISTS support_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    admin_reply TEXT,
    status TEXT DEFAULT 'open',         -- 'open' | 'answered' | 'closed'
    created_at TEXT,
    answered_at TEXT
);
"""

DEFAULT_TARIFFS = [
    ("1 oylik", 50000, 30),
    ("3 oylik", 130000, 90),
    ("12 oylik", 450000, 365),
]


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        cur = await db.execute("SELECT COUNT(*) FROM tariffs")
        (count,) = await cur.fetchone()
        if count == 0:
            for name, price, days in DEFAULT_TARIFFS:
                await db.execute(
                    "INSERT INTO tariffs (name, price, duration_days) VALUES (?,?,?)",
                    (name, price, days),
                )
        await db.commit()


def now_iso():
    return datetime.datetime.now().isoformat()


def gen_referral_code(length=7):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ==========================================================
#  FOYDALANUVCHILAR
# ==========================================================

async def get_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        return await cur.fetchone()


async def get_user_by_id(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return await cur.fetchone()


async def create_user(telegram_id, username, full_name, referred_by_code=None):
    trial_end = (datetime.datetime.now() + datetime.timedelta(days=TRIAL_DAYS)).isoformat()
    ref_code = gen_referral_code()
    referred_by_id = None

    async with aiosqlite.connect(DB_PATH) as db:
        if referred_by_code:
            cur = await db.execute(
                "SELECT id FROM users WHERE referral_code=?", (referred_by_code,)
            )
            row = await cur.fetchone()
            if row:
                referred_by_id = row[0]

        await db.execute(
            """INSERT INTO users
               (telegram_id, username, full_name, role, referral_code, referred_by,
                subscription_end, is_registered, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (telegram_id, username, full_name, "user", ref_code, referred_by_id,
             trial_end, 0, now_iso()),
        )
        await db.commit()
    return await get_user(telegram_id)


async def complete_registration(telegram_id, phone, shop_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET phone=?, shop_name=?, is_registered=1 WHERE telegram_id=?",
            (phone, shop_name, telegram_id),
        )
        await db.commit()


async def extend_subscription(user_id: int, days: int):
    user = await get_user_by_id(user_id)
    base = datetime.datetime.now()
    if user and user["subscription_end"]:
        try:
            cur_end = datetime.datetime.fromisoformat(user["subscription_end"])
            if cur_end > base:
                base = cur_end
        except ValueError:
            pass
    new_end = base + datetime.timedelta(days=days)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET subscription_end=? WHERE id=?", (new_end.isoformat(), user_id)
        )
        await db.commit()
    return new_end


async def is_subscription_active(telegram_id: int) -> bool:
    user = await get_user(telegram_id)
    if not user or not user["subscription_end"]:
        return False
    try:
        end = datetime.datetime.fromisoformat(user["subscription_end"])
    except ValueError:
        return False
    return end > datetime.datetime.now()


async def get_all_users(limit=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT * FROM users ORDER BY created_at DESC"
        if limit:
            q += f" LIMIT {limit}"
        cur = await db.execute(q)
        return await cur.fetchall()


async def count_users():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        (n,) = await cur.fetchone()
        return n


async def count_active_subscriptions():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM users WHERE subscription_end > ?", (now_iso(),)
        )
        (n,) = await cur.fetchone()
        return n


async def set_block_status(telegram_id: int, blocked: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_blocked=? WHERE telegram_id=?", (1 if blocked else 0, telegram_id)
        )
        await db.commit()


async def set_role(telegram_id: int, role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET role=? WHERE telegram_id=?", (role, telegram_id))
        await db.commit()


async def users_expiring_soon(days_ahead=1):
    """Ertaga (yoki N kun ichida) obunasi tugaydigan foydalanuvchilar."""
    target = (datetime.datetime.now() + datetime.timedelta(days=days_ahead)).date().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE substr(subscription_end,1,10)=?", (target,)
        )
        return await cur.fetchall()


# ==========================================================
#  MAHSULOTLAR / OMBOR
# ==========================================================

async def add_product(owner_id, name, category, barcode, qr_code, price, quantity):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO products (owner_id, name, category, barcode, qr_code, price, quantity, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (owner_id, name, category, barcode, qr_code, price, quantity, now_iso()),
        )
        await db.commit()
        return cur.lastrowid


async def get_product_by_code(owner_id, code):
    """Barcode yoki ichki QR kod bo'yicha mahsulotni topadi."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM products WHERE owner_id=? AND (barcode=? OR qr_code=?)",
            (owner_id, code, code),
        )
        return await cur.fetchone()


async def get_product(product_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM products WHERE id=?", (product_id,))
        return await cur.fetchone()


async def list_products(owner_id, search=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if search:
            cur = await db.execute(
                "SELECT * FROM products WHERE owner_id=? AND name LIKE ? ORDER BY name",
                (owner_id, f"%{search}%"),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM products WHERE owner_id=? ORDER BY name", (owner_id,)
            )
        return await cur.fetchall()


async def update_stock(product_id, delta_qty):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE products SET quantity = quantity + ? WHERE id=?", (delta_qty, product_id)
        )
        await db.commit()


async def add_transaction(owner_id, product_id, ttype, quantity, price):
    total = quantity * price
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO transactions (owner_id, product_id, type, quantity, price, total, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (owner_id, product_id, ttype, quantity, price, total, now_iso()),
        )
        await db.commit()
    delta = quantity if ttype == "kirim" else -quantity
    await update_stock(product_id, delta)
    return total


async def get_report(owner_id, date_from=None, date_to=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT * FROM transactions WHERE owner_id=?"
        params = [owner_id]
        if date_from:
            q += " AND created_at >= ?"
            params.append(date_from)
        if date_to:
            q += " AND created_at <= ?"
            params.append(date_to)
        q += " ORDER BY created_at DESC"
        cur = await db.execute(q, params)
        return await cur.fetchall()


async def get_summary(owner_id, date_from=None):
    async with aiosqlite.connect(DB_PATH) as db:
        q_in = "SELECT COALESCE(SUM(total),0) FROM transactions WHERE owner_id=? AND type='kirim'"
        q_out = "SELECT COALESCE(SUM(total),0) FROM transactions WHERE owner_id=? AND type='chiqim'"
        params = [owner_id]
        if date_from:
            q_in += " AND created_at>=?"
            q_out += " AND created_at>=?"
            params.append(date_from)
        cur1 = await db.execute(q_in, params)
        (kirim_sum,) = await cur1.fetchone()
        cur2 = await db.execute(q_out, params)
        (chiqim_sum,) = await cur2.fetchone()
        return kirim_sum, chiqim_sum


# ==========================================================
#  TARIFLAR
# ==========================================================

async def get_active_tariffs():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tariffs WHERE is_active=1 ORDER BY price")
        return await cur.fetchall()


async def get_tariff(tariff_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tariffs WHERE id=?", (tariff_id,))
        return await cur.fetchone()


async def add_tariff(name, price, duration_days):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tariffs (name, price, duration_days) VALUES (?,?,?)",
            (name, price, duration_days),
        )
        await db.commit()


async def toggle_tariff(tariff_id, is_active):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tariffs SET is_active=? WHERE id=?", (is_active, tariff_id))
        await db.commit()


# ==========================================================
#  TO'LOVLAR
# ==========================================================

async def create_payment(user_id, tariff_id, amount, screenshot_file_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO payments (user_id, tariff_id, amount, screenshot_file_id, created_at)
               VALUES (?,?,?,?,?)""",
            (user_id, tariff_id, amount, screenshot_file_id, now_iso()),
        )
        await db.commit()
        return cur.lastrowid


async def get_payment(payment_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM payments WHERE id=?", (payment_id,))
        return await cur.fetchone()


async def get_pending_payments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM payments WHERE status='pending' ORDER BY created_at")
        return await cur.fetchall()


async def review_payment(payment_id, status, comment=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status=?, admin_comment=?, reviewed_at=? WHERE id=?",
            (status, comment, now_iso(), payment_id),
        )
        await db.commit()


# ==========================================================
#  PROMO-KODLAR
# ==========================================================

async def create_promo(code, bonus_days, usage_limit):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO promo_codes (code, bonus_days, usage_limit, created_at) VALUES (?,?,?,?)",
            (code.upper(), bonus_days, usage_limit, now_iso()),
        )
        await db.commit()


async def get_promo(code):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM promo_codes WHERE code=?", (code.upper(),))
        return await cur.fetchone()


async def use_promo(promo_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE promo_codes SET used_count = used_count + 1 WHERE id=?", (promo_id,)
        )
        await db.execute(
            "INSERT INTO promo_usages (promo_id, user_id, used_at) VALUES (?,?,?)",
            (promo_id, user_id, now_iso()),
        )
        await db.commit()


async def has_used_promo(promo_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM promo_usages WHERE promo_id=? AND user_id=?",
            (promo_id, user_id),
        )
        (n,) = await cur.fetchone()
        return n > 0


# ==========================================================
#  SUPPORT / MUROJAATLAR
# ==========================================================

async def create_ticket(user_id, message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO support_tickets (user_id, message, created_at) VALUES (?,?,?)",
            (user_id, message, now_iso()),
        )
        await db.commit()
        return cur.lastrowid


async def get_open_tickets():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM support_tickets WHERE status='open' ORDER BY created_at")
        return await cur.fetchall()


async def answer_ticket(ticket_id, reply):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE support_tickets SET admin_reply=?, status='answered', answered_at=? WHERE id=?",
            (reply, now_iso(), ticket_id),
        )
        await db.commit()


async def get_ticket(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM support_tickets WHERE id=?", (ticket_id,))
        return await cur.fetchone()


# ==========================================================
#  REFERALLAR
# ==========================================================

async def get_referral_stats(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,))
        (n,) = await cur.fetchone()
        return n
