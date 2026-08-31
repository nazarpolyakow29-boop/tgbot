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


# ============================================================
# НАСТРОЙКИ
# ============================================================

# НЕ ВСТАВЛИВАЙ ТОКЕН ПРЯМО СЮДА.
# На Render создай переменную окружения BOT_TOKEN.
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 5800940022

PORT = int(os.getenv("PORT", 10000))

USERS_FILE = "users.json"

# Курс выкупа
STAR_RATE = 1.4

# Лимиты
MIN_STARS = 50
MAX_STARS = 100_000


# ============================================================
# ПРОВЕРКА ТОКЕНА
# ============================================================

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден. "
        "Добавь BOT_TOKEN в Environment Variables."
    )


# ============================================================
# БОТ
# ============================================================

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()


# ============================================================
# JSON
# ============================================================

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


def load_users():

    return load_json(
        USERS_FILE
    )


def save_users(users):

    save_json(
        USERS_FILE,
        users
    )


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

def main_keyboard():

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="⭐️ Купить звёзды",
                    callback_data="buy_stars"
                )
            ],

            [
                InlineKeyboardButton(
                    text="💰 Продажа звёзд",
                    callback_data="sell_stars"
                )
            ]

        ]

    )


# ============================================================
# /START
# ============================================================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id

    # --------------------------------------------------------
    # Сохраняем пользователя
    # --------------------------------------------------------

    users = load_users()

    if user_id not in users:

        users.append(user_id)

        save_users(users)

        print(
            f"Новый пользователь: {user_id}"
        )

    # --------------------------------------------------------
    # Приветствие
    # --------------------------------------------------------

    await message.answer(

        "☺️ Привет, бурмалдун!\n\n"

        "Здесь вы можете быстро приобрести "
        "Telegram Stars и Premium подписку "
        "на свой аккаунт за рубли\n\n"

        "⭐️ При помощи нашего сервиса купили "
        "34 469 799 звёзд "
        "(40 329 665 ₽)⭐️",

        reply_markup=main_keyboard()

    )


# ============================================================
# КНОПКА "КУПИТЬ ЗВЁЗДЫ"
# ============================================================

@dp.callback_query(F.data == "buy_stars")
async def buy_stars(
    callback: CallbackQuery
):

    # Пока ничего не делаем

    await callback.answer()


# ============================================================
# КНОПКА "ПРОДАЖА ЗВЁЗД"
# ============================================================

@dp.callback_query(F.data == "sell_stars")
async def sell_stars(
    callback: CallbackQuery
):

    await callback.message.answer(

        "💰 Курс выкупа: 1,4₽ за 1 ⭐️\n\n"

        "— Минимум: 50 звёзд\n"
        "— Максимум (за один заказ): 100,000 звёзд\n\n"

        "🔎 Введите количество звёзд для продажи:"

    )

    await callback.answer()


# ============================================================
# ОБРАБОТКА ВВОДА КОЛИЧЕСТВА
# ============================================================

@dp.message(F.text)
async def process_amount(
    message: Message
):

    text = message.text.strip()

    # Команды не обрабатываем здесь
    if text.startswith("/"):
        return

    # --------------------------------------------------------
    # Проверяем число
    # --------------------------------------------------------

    if not text.isdigit():

        await message.answer(

            "❌ Введите количество звёзд "
            "целым числом.\n\n"

            "Например:\n"
            "500"

        )

        return

    stars = int(text)

    # --------------------------------------------------------
    # Минимум
    # --------------------------------------------------------

    if stars < MIN_STARS:

        await message.answer(

            f"❌ Минимальное количество — "
            f"{MIN_STARS} ⭐️"

        )

        return

    # --------------------------------------------------------
    # Максимум
    # --------------------------------------------------------

    if stars > MAX_STARS:

        await message.answer(

            f"❌ Максимальное количество — "
            f"{MAX_STARS:,} ⭐️".replace(",", " ")

        )

        return

    # --------------------------------------------------------
    # Расчёт
    # --------------------------------------------------------

    rub_amount = stars * STAR_RATE

    # --------------------------------------------------------
    # ВАЖНО:
    #
    # Telegram invoice с XTR принимает количество Stars,
    # а не рубли.
    #
    # Поэтому реальный invoice будет на stars.
    # --------------------------------------------------------

    payload = (
        f"stars_order:"
        f"{message.from_user.id}:"
        f"{stars}"
    )

    try:

        await message.answer(

            f"⭐️ Количество: {stars:,}\n"
            f"💰 Расчёт по курсу: {rub_amount:,.2f} ₽\n\n"
            f"⚠️ Telegram-платёж будет выставлен "
            f"в Stars, а не в рублях.".replace(",", " ")

        )

        await message.answer_invoice(

            title="⭐️ Telegram Stars",

            description=(
                f"Оплата за {stars:,} Telegram Stars"
            ).replace(",", " "),

            payload=payload,

            # Для XTR provider_token не нужен
            provider_token="",

            currency="XTR",

            prices=[

                LabeledPrice(

                    label=f"{stars:,} Stars".replace(",", " "),

                    amount=stars

                )

            ]

        )

    except Exception as error:

        print(
            f"Ошибка создания invoice: {error}"
        )

        await message.answer(

            "❌ Не удалось создать счёт.\n\n"
            "Попробуйте ещё раз."

        )


# ============================================================
# PRE-CHECKOUT
# ============================================================

@dp.pre_checkout_query()
async def pre_checkout(
    query: PreCheckoutQuery
):

    payload = query.invoice_payload

    # --------------------------------------------------------
    # Проверяем формат payload
    # --------------------------------------------------------

    if not payload.startswith("stars_order:"):

        await query.answer(

            ok=False,

            error_message="Неверный заказ."

        )

        return

    try:

        parts = payload.split(":")

        user_id = int(parts[1])

        stars = int(parts[2])

    except Exception:

        await query.answer(

            ok=False,

            error_message="Ошибка заказа."

        )

        return

    # --------------------------------------------------------
    # Проверяем пользователя
    # --------------------------------------------------------

    if user_id != query.from_user.id:

        await query.answer(

            ok=False,

            error_message="Этот счёт предназначен другому пользователю."

        )

        return

    # --------------------------------------------------------
    # Проверяем сумму
    # --------------------------------------------------------

    if query.total_amount != stars:

        await query.answer(

            ok=False,

            error_message="Неверная сумма."

        )

        return

    # --------------------------------------------------------
    # Всё нормально
    # --------------------------------------------------------

    await query.answer(
        ok=True
    )


# ============================================================
# УСПЕШНАЯ ОПЛАТА
# ============================================================

@dp.message(F.successful_payment)
async def successful_payment(
    message: Message
):

    payment = message.successful_payment

    payload = payment.invoice_payload

    if not payload.startswith("stars_order:"):

        await message.answer(
            "❌ Неизвестный платёж."
        )

        return

    try:

        parts = payload.split(":")

        user_id = int(parts[1])

        stars = int(parts[2])

    except Exception:

        await message.answer(
            "❌ Ошибка обработки платежа."
        )

        return

    rub_amount = stars * STAR_RATE

    # --------------------------------------------------------
    # ЛОГ
    # --------------------------------------------------------

    print(
        "========================================"
    )

    print("НОВЫЙ ПЛАТЁЖ")

    print(
        f"Пользователь: {user_id}"
    )

    print(
        f"Stars: {stars}"
    )

    print(
        f"Расчёт: {rub_amount:.2f} RUB"
    )

    print(
        "Charge ID:",
        payment.telegram_payment_charge_id
    )

    print(
        "========================================"
    )

    # --------------------------------------------------------
    # Уведомление администратору
    # --------------------------------------------------------

    try:

        username = message.from_user.username

        if username:

            username_text = f"@{username}"

        else:

            username_text = "без username"

        await bot.send_message(

            ADMIN_ID,

            "💰 НОВЫЙ ПЛАТЁЖ\n\n"

            f"👤 Пользователь: "
            f"{message.from_user.full_name}\n"

            f"🔗 Username: {username_text}\n"

            f"🆔 ID: {user_id}\n\n"

            f"⭐️ Количество: "
            f"{stars:,}\n"

            f"💵 Расчёт по курсу: "
            f"{rub_amount:,.2f} ₽\n\n"

            "⚠️ Проверьте заказ.".replace(",", " ")

        )

    except Exception as error:

        print(
            f"Ошибка уведомления админа: {error}"
        )

    # --------------------------------------------------------
    # Пользователю
    # --------------------------------------------------------

    await message.answer(

        "✅ Оплата успешно завершена!\n\n"

        f"⭐️ Количество: {stars:,}\n"

        f"💰 Расчёт: {rub_amount:,.2f} ₽\n\n"

        "Спасибо!"

    )


# ============================================================
# /USERS
# ============================================================

@dp.message(Command("users"))
async def users_count(
    message: Message
):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ У вас нет доступа."
        )

        return

    users = load_users()

    await message.answer(

        "📊 Статистика\n\n"

        f"👥 Пользователей: {len(users)}"

    )


# ============================================================
# /BROADCAST
# ============================================================

@dp.message(Command("broadcast"))
async def broadcast(
    message: Message
):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ У вас нет доступа."
        )

        return

    text = message.text or ""

    broadcast_text = text[
        len("/broadcast"):
    ].strip()

    if not broadcast_text:

        users = load_users()

        await message.answer(

            "📢 Рассылка\n\n"

            f"👥 Получателей: {len(users)}\n\n"

            "Использование:\n\n"

            "/broadcast Ваш текст"

        )

        return

    users = load_users()

    await message.answer(

        "📢 Начинаю рассылку.\n\n"

        f"👥 Получателей: {len(users)}"

    )

    success = 0

    failed = 0

    for user_id in users:

        try:

            await bot.send_message(

                chat_id=user_id,

                text=broadcast_text

            )

            success += 1

            await asyncio.sleep(0.1)

        except TelegramRetryAfter as error:

            await asyncio.sleep(
                error.retry_after
            )

            try:

                await bot.send_message(

                    chat_id=user_id,

                    text=broadcast_text

                )

                success += 1

            except Exception:

                failed += 1

        except Exception as error:

            failed += 1

            print(
                f"Ошибка {user_id}: {error}"
            )

    await message.answer(

        "✅ Рассылка завершена!\n\n"

        f"📨 Успешно: {success}\n"

        f"❌ Ошибок: {failed}"

    )


# ============================================================
# HTTP SERVER ДЛЯ RENDER
# ============================================================

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

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(

        runner,

        host="0.0.0.0",

        port=PORT

    )

    await site.start()

    print(
        f"HTTP server started on port {PORT}"
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    print(
        "========================================"
    )

    print(
        "Telegram Bot starting..."
    )

    print(
        f"Курс: {STAR_RATE} RUB / ⭐️"
    )

    print(
        f"Минимум: {MIN_STARS}"
    )

    print(
        f"Максимум: {MAX_STARS}"
    )

    print(
        f"Admin ID: {ADMIN_ID}"
    )

    print(
        f"Port: {PORT}"
    )

    print(
        "========================================"
    )

    await start_web_server()

    await dp.start_polling(bot)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "Bot stopped."
        )
