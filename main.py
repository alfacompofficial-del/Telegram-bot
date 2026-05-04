import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import LabeledPrice, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
API_TOKEN = '8201479243:AAGaU4CMJDCbBj7X6BrnAjxJtg-Omv9S0Oo'
ADMIN_1 = "@Bilol_77728"
ADMIN_2 = "@abdulloh2012_a"
GROUP_ID = -1003903136498
MIN_STARS = 50
COMMISSION_PER_ADMIN = 0.05  # 5% одному админу (итого 10%)

# Каталог подарков (цена указана БЕЗ комиссии)
GIFTS = {
    "candy": {"name": "🍬 Коробка конфет", "price": 50},
    "bear": {"name": "🧸 Плюшевый медведь", "price": 100},
    "car": {"name": "🏎 Игрушечный спорткар", "price": 250},
    "diamond": {"name": "💎 Виртуальный бриллиант", "price": 1000}
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


class Transfer(StatesGroup):
    waiting_for_amount = State()


# --- 1. СТАРТ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type in ["group", "supergroup"]:
        builder = InlineKeyboardBuilder()
        builder.button(text="Перейти к боту 🤖", url=f"https://t.me/{(await bot.get_me()).username}?start=start")
        await message.answer("Переводы и подарки оформляются в ЛС:", reply_markup=builder.as_markup())
        return

    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="⭐️ Перевести звёзды",
                                  request_user=types.KeyboardButtonRequestUser(request_id=1))],
            [types.KeyboardButton(text="🎁 Отправить подарок",
                                  request_user=types.KeyboardButtonRequestUser(request_id=2))]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите действие. Комиссия 10% (по 5% админам) действует на всё.", reply_markup=kb)


# --- 2. ВЫБОР ПОЛУЧАТЕЛЯ ---
@dp.message(F.user_shared)
async def on_user_shared(message: types.Message, state: FSMContext):
    user_id = message.user_shared.user_id
    req_id = message.user_shared.request_id
    await state.update_data(recipient_id=user_id)

    if req_id == 1:
        await state.set_state(Transfer.waiting_for_amount)
        await message.answer(f"✅ Получатель: `{user_id}`\nСколько ⭐️ отправить?")
    elif req_id == 2:
        builder = InlineKeyboardBuilder()
        for gift_id, gift_data in GIFTS.items():
            # Показываем цену уже с учетом комиссии для прозрачности
            price_with_comm = int(gift_data["price"] * (1 + COMMISSION_PER_ADMIN * 2))
            builder.button(text=f'{gift_data["name"]} — {price_with_comm} ⭐️', callback_data=f"gift_{gift_id}")
        builder.adjust(1)
        await message.answer(f"🎁 Получатель: `{user_id}`\nВыберите подарок (цена с комиссией):",
                             reply_markup=builder.as_markup())


# --- 3A. ОПЛАТА ЗВЁЗД ---
@dp.message(Transfer.waiting_for_amount)
async def process_stars(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return
    stars = int(message.text)
    if stars < MIN_STARS: return await message.answer(f"Мин. {MIN_STARS}")

    comm = int(stars * COMMISSION_PER_ADMIN)
    total = stars + (comm * 2)
    data = await state.get_data()

    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Перевод звёзд",
        description=f"Отправка {stars} ⭐️ + комиссия",
        payload=f"stars|{data['recipient_id']}|{stars}",
        provider_token="", currency="XTR",
        prices=[LabeledPrice(label="Итого", amount=total)]
    )
    await state.clear()


# --- 3B. ОПЛАТА ПОДАРКА (С КОМИССИЕЙ) ---
@dp.callback_query(F.data.startswith("gift_"))
async def process_gift(call: types.CallbackQuery, state: FSMContext):
    gift_id = call.data.split("_")[1]
    gift = GIFTS[gift_id]

    # Считаем комиссию на подарок
    comm = int(gift['price'] * COMMISSION_PER_ADMIN)
    total = gift['price'] + (comm * 2)

    data = await state.get_data()

    await bot.send_invoice(
        chat_id=call.message.chat.id,
        title="Покупка подарка",
        description=f"Предмет: {gift['name']}\nЦена: {gift['price']} + Комиссия: {comm * 2}",
        payload=f"gift|{data['recipient_id']}|{gift_id}",
        provider_token="", currency="XTR",
        prices=[LabeledPrice(label=gift['name'], amount=total)]
    )
    await call.message.delete()
    await state.clear()


# --- 4. УСПЕШНАЯ ОПЛАТА ---
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)


@dp.message(F.successful_payment)
async def success(message: types.Message):
    parts = message.successful_payment.invoice_payload.split('|')
    mode, recipient = parts[0], parts[1]

    if mode == "gift":
        gift_name = GIFTS[parts[2]]["name"]
        # АНОНИМНЫЙ ОТЧЕТ (без имени отправителя)
        report = (
            f"🎁 **НОВЫЙ АНОНИМНЫЙ ПОДАРОК!**\n\n"
            f"👤 **Кому:** `{recipient}`\n"
            f"📦 **Подарок:** {gift_name}\n"
            f"📈 *Комиссия за покупку зачислена админам*"
        )
    else:
        amount = parts[2]
        # ОТКРЫТЫЙ ОТЧЕТ (с именем)
        report = (
            f"💸 **ПЕРЕВОД ЗВЁЗД**\n\n"
            f"👤 **От:** {message.from_user.full_name}\n"
            f"🎯 **Кому:** `{recipient}`\n"
            f"💰 **Сумма:** {amount} ⭐️\n"
            f"📈 *Комиссия 10% зачислена админам*"
        )

    await message.answer("✅ Всё готово! Отчет в группе.")
    await bot.send_message(GROUP_ID, report, parse_mode="Markdown")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
