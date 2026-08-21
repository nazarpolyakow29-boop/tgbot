import asyncio
import json
import os

from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
)
from aiogram.exceptions import TelegramRetryAfter


# ==========================================
# НАСТРОЙКИ
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Цена в Telegram Stars
PRICE = 6

# Файлы с пользователями и покупателями
USERS_FILE = "users.json"
BUYERS_FILE = "buyers.json"

# Telegram ID администратора
ADMIN_ID = 5800940022

# Порт для Render
PORT = int(os.getenv("PORT", 10000))

# Payload платежа
PAYMENT_PAYLOAD = "socially_exhausted_purchase"

# Текст, который получает покупатель после оплаты
ACCESS_TEXT = (
    "✅ Оплата успешно завершена!\n\n"
    "🎉 Спасибо за покупку!\n\n"
    "🔗 Ваш доступ:\n"
    "@socially_exhausted"
)


# ==========================================
# ПРОВЕРКА BOT TOKEN
# ==========================================

if not BOT_TOKEN:
    raise ValueError(
        "Ошибка: переменная окружения BOT_TOKEN не найдена!"
    )


# ==========================================
# СОЗДАНИЕ БОТА
# ==========================================

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()


# ==========================================
# РАБОТА С JSON
# ==========================================

def load_json(filename):

    if not os.path.exists(filename):
        return []

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if isinstance(data, list):
                return data

            return []

    except (
        json.JSONDecodeError,
        FileNotFoundError,
        OSError
    ):

        return []


def save_json(filename, data):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# ==========================================
# USERS
# ==========================================

def load_users():

    return load_json(
        USERS_FILE
    )


def save_users(users):

    save_json(
        USERS_FILE,
        users
    )


# ==========================================
# BUYERS
# ==========================================

def load_buyers():

    return load_json(
        BUYERS_FILE
    )


def save_buyers(buyers):

    save_json(
        BUYERS_FILE,
        buyers
    )


# ==========================================
# КНОПКА ПОКУПКИ
# ==========================================

def get_buy_keyboard():

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text=f"⭐ Купить доступ — {PRICE} Stars",

                    callback_data="buy_access"

                )

            ]

        ]

    )


# ==========================================
# КНОПКА ПОЛУЧЕНИЯ ДОСТУПА
# ==========================================

def get_access_keyboard():

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="🔗 Получить доступ",

                    callback_data="get_access"

                )

            ]

        ]

    )


# ==========================================
# /START
# ==========================================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id

    # --------------------------------------
    # СОХРАНЯЕМ ПОЛЬЗОВАТЕЛЯ
    # --------------------------------------

    users = load_users()

    if user_id not in users:

        users.append(user_id)

        save_users(users)

        print(
            f"Новый пользователь: {user_id}"
        )

    # --------------------------------------
    # ПРОВЕРЯЕМ ПОКУПКУ
    # --------------------------------------

    buyers = load_buyers()

    if user_id in buyers:

        await message.answer(

            "✅ Вы уже приобрели доступ.\n\n"
            "Нажмите кнопку ниже, чтобы "
            "получить его снова.",

            reply_markup=get_access_keyboard()

        )

        return

    # --------------------------------------
    # НОВЫЙ ПОЛЬЗОВАТЕЛЬ
    # --------------------------------------

    await message.answer(

        "👋 Добро пожаловать!\n\n"

        f"🔐 Доступ к материалу: ⭐ {PRICE} Stars\n\n"

        "После оплаты вы получите доступ "
        "автоматически.\n\n"

        "Нажмите кнопку ниже для покупки.",

        reply_markup=get_buy_keyboard()

    )


# ==========================================
# /USERS
# ==========================================

@dp.message(Command("users"))
async def users_count(message: Message):

    # Только администратор

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ У вас нет доступа к этой команде."
        )

        return

    users = load_users()

    buyers = load_buyers()

    await message.answer(

        "📊 Статистика бота\n\n"

        f"👥 Всего пользователей: {len(users)}\n"

        f"💰 Покупателей: {len(buyers)}"

    )


# ==========================================
# ПОКУПКА
# ==========================================

@dp.callback_query(F.data == "buy_access")
async def buy_access(
    callback: CallbackQuery
):

    try:

        await callback.message.answer_invoice(

            title="🔐 Доступ",

            description=(
                "Покупка доступа к материалу"
            ),

            payload=PAYMENT_PAYLOAD,

            # Для Telegram Stars оставляем пустым
            provider_token="",

            currency="XTR",

            prices=[

                LabeledPrice(

                    label="Доступ",

                    amount=PRICE

                )

            ]

        )

        await callback.answer()

    except Exception as error:

        print(
            f"Ошибка создания счёта: {error}"
        )

        await callback.answer(

            "❌ Не удалось создать оплату.",

            show_alert=True

        )


# ==========================================
# PRE-CHECKOUT
# ==========================================

@dp.pre_checkout_query()
async def process_pre_checkout(
    pre_checkout_query: PreCheckoutQuery
):

    # Проверяем payload

    if (
        pre_checkout_query.invoice_payload
        != PAYMENT_PAYLOAD
    ):

        await pre_checkout_query.answer(

            ok=False,

            error_message="Неверный платёж."

        )

        return

    # Подтверждаем платёж

    await pre_checkout_query.answer(
        ok=True
    )


# ==========================================
# УСПЕШНАЯ ОПЛАТА
# ==========================================

@dp.message(F.successful_payment)
async def successful_payment(
    message: Message
):

    payment = message.successful_payment

    user_id = message.from_user.id

    # --------------------------------------
    # ПРОВЕРЯЕМ PAYLOAD
    # --------------------------------------

    if payment.invoice_payload != PAYMENT_PAYLOAD:

        print(

            f"Неизвестный payload "
            f"от пользователя {user_id}: "
            f"{payment.invoice_payload}"

        )

        await message.answer(
            "❌ Ошибка платежа."
        )

        return

    # --------------------------------------
    # ДОБАВЛЯЕМ ПОКУПАТЕЛЯ
    # --------------------------------------

    buyers = load_buyers()

    if user_id not in buyers:

        buyers.append(user_id)

        save_buyers(
            buyers
        )

        print(
            f"Новый покупатель: {user_id}"
        )

    # --------------------------------------
    # ОТПРАВЛЯЕМ ТЕКСТ
    # --------------------------------------

    await message.answer(
        ACCESS_TEXT,
        reply_markup=get_access_keyboard()
    )


# ==========================================
# ПОВТОРНО ПОЛУЧИТЬ ДОСТУП
# ==========================================

@dp.callback_query(F.data == "get_access")
async def get_access(
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    # --------------------------------------
    # ПРОВЕРЯЕМ ПОКУПКУ
    # --------------------------------------

    buyers = load_buyers()

    if user_id not in buyers:

        await callback.answer(

            "Сначала необходимо купить доступ.",

            show_alert=True

        )

        return

    # --------------------------------------
    # ОТПРАВЛЯЕМ ТЕКСТ
    # --------------------------------------

    await callback.message.answer(
        ACCESS_TEXT
    )

    await callback.answer()


# ==========================================
# /BROADCAST
# ==========================================

@dp.message(Command("broadcast"))
async def broadcast(
    message: Message
):

    # --------------------------------------
    # ПРОВЕРЯЕМ АДМИНИСТРАТОРА
    # --------------------------------------

    if message.from_user.id != ADMIN_ID:

        await message.answer(

            "❌ У вас нет доступа "
            "к этой команде."

        )

        return

    # --------------------------------------
    # ПОЛУЧАЕМ ТЕКСТ
    # --------------------------------------

    text = message.text or ""

    broadcast_text = text[
        len("/broadcast"):
    ].strip()

    # --------------------------------------
    # ЕСЛИ ТЕКСТ НЕ УКАЗАН
    # --------------------------------------

    if not broadcast_text:

        users = load_users()

        await message.answer(

            "📢 Рассылка\n\n"

            f"👥 Получателей: {len(users)}\n\n"

            "Использование:\n\n"

            "/broadcast Ваш текст"

        )

        return

    # --------------------------------------
    # ЗАГРУЖАЕМ ПОЛЬЗОВАТЕЛЕЙ
    # --------------------------------------

    users = load_users()

    await message.answer(

        "📢 Начинаю рассылку.\n\n"

        f"👥 Получателей: {len(users)}"

    )

    success = 0

    failed = 0

    # --------------------------------------
    # РАССЫЛКА
    # --------------------------------------

    for user_id in users:

        try:

            await bot.send_message(

                chat_id=user_id,

                text=broadcast_text

            )

            success += 1

            await asyncio.sleep(
                0.1
            )

        except TelegramRetryAfter as error:

            print(

                f"Telegram попросил "
                f"подождать {error.retry_after} сек."

            )

            await asyncio.sleep(
                error.retry_after
            )

            try:

                await bot.send_message(

                    chat_id=user_id,

                    text=broadcast_text

                )

                success += 1

            except Exception as retry_error:

                failed += 1

                print(

                    f"Повторная ошибка "
                    f"{user_id}: {retry_error}"

                )

        except Exception as error:

            failed += 1

            print(

                f"Ошибка отправки "
                f"{user_id}: {error}"

            )

    # --------------------------------------
    # РЕЗУЛЬТАТ
    # --------------------------------------

    await message.answer(

        "✅ Рассылка завершена!\n\n"

        f"📨 Успешно: {success}\n"

        f"❌ Ошибок: {failed}"

    )


# ==========================================
# HTTP SERVER ДЛЯ RENDER
# ==========================================

async def health_check(request):

    return web.Response(
        text="Bot is running!"
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health_check
    )

    app.router.add_get(
        "/health",
        health_check
    )

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(

        runner,

        host="0.0.0.0",

        port=PORT

    )

    await site.start()

    print(

        f"HTTP server started "
        f"on port {PORT}"

    )


# ==========================================
# MAIN
# ==========================================

async def main():

    print(
        "================================="
    )

    print(
        "Telegram Bot is starting..."
    )

    print(
        f"Price: {PRICE} Stars"
    )

    print(
        f"Access: @socially_exhausted"
    )

    print(
        f"HTTP port: {PORT}"
    )

    print(
        f"Admin ID: {ADMIN_ID}"
    )

    print(
        "================================="
    )

    # Запускаем HTTP-сервер

    await start_web_server()

    # Запускаем Telegram-бота

    await dp.start_polling(
        bot
    )


# ==========================================
# START
# ==========================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "Bot stopped."
)
