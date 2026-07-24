from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_phone = State()
    waiting_shop_name = State()


class ProductAdd(StatesGroup):
    waiting_name = State()
    waiting_category = State()
    waiting_price = State()
    waiting_quantity = State()
    waiting_code_choice = State()


class StockMove(StatesGroup):
    waiting_code = State()          # skanerlash yoki qo'lda kiritish
    waiting_quantity = State()
    waiting_new_product_decision = State()


class Payment(StatesGroup):
    waiting_screenshot = State()


class Support(StatesGroup):
    waiting_message = State()


class PromoEnter(StatesGroup):
    waiting_code = State()


class CodeGen(StatesGroup):
    waiting_product_name = State()


# ---- Admin FSM holatlari ----

class AdminBroadcast(StatesGroup):
    waiting_message = State()


class AdminTariffAdd(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_days = State()


class AdminPromoAdd(StatesGroup):
    waiting_code = State()
    waiting_days = State()
    waiting_limit = State()


class AdminTicketReply(StatesGroup):
    waiting_reply = State()
