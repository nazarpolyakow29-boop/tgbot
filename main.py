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

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 5800940022

PORT = int(os.getenv("PORT", 10000))

USERS_FILE = "users.json"
CONFIG_FILE = "config.json"

# Цена доступа
PRICE = 10

# Начальная ссылка на видео
DEFAULT_VIDEO_LINK = "https://t.me/+uMzPPsbNqVYyZTlk"

# Payload платежа
PAYMENT_PAYLOAD = "video_access_10_stars"


# ============================================================
# ПРОВЕРКА BOT TOKEN
# ============================================================

if not BOT_TOKEN:
    raise ValueError(
        "Ошибка: переменная окружения BOT_TOKEN не найдена!"
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

            return json.load(file)

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


# ============================================================
# USERS
# ============================================================

def load_users():

    data = load_json(USERS_FILE)

    if isinstance(data, list):
        return data

    return []


def save_users(users):

    save_json(
        USERS_FILE,
        users
    )


# ============================================================
# CONFIG
# ============================================================

def load_config():

    if not os.path.exists(CONFIG_FILE):

        config = {
            "video_link": DEFAULT_VIDEO_LINK
        }

        save_json(
            CONFIG_FILE,
            config
        )

        return config

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            config = json.load(file)

            if not isinstance(config, dict):
                raise ValueError

            if "video_link" not in config:
                config["video_link"] = DEFAULT_VIDEO_LINK

            return config

    except Exception:

        return {
            "video_link": DEFAULT_VIDEO_LINK
        }


def get_video_link():

    config = load_config()

    return config.get(
        "video_link",
        DEFAULT_VIDEO_LINK
    )


def set_video_link(new_link):

    config = load_config()

    config["video_link"] = new_link

    save_json(
        CONFIG_FILE,
        config
    )


# ============================================================
# КНОПКА ОПЛАТЫ
# ============================================================

def get_payment_keyboard():

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="⭐️ Оплатить 10 Stars",
                    callback_data="pay_10_stars"
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
    # Сообщение
    # --------------------------------------------------------

    await message.answer(

        "👋 Привет!\n\n"

        "🎬 Чтобы получить видео, "
        "оплатите счёт на 10 ⭐️\n\n"

        "Если у вас нет 10 ⭐️, "
        "можете написать 30 комментариев "
        "под разными видео в TikTok.\n\n"

        "Подробнее: @yuzaye",

        reply_markup=get_payment_keyboard()

    )


# ============================================================
# КНОПКА ОПЛАТЫ
# ============================================================

@dp.callback_query(F.data == "pay_10_stars")
async def pay_10_stars(
    callback: CallbackQuery
):

    try:

        await callback.message.answer_invoice(

            title="🎬 Получение видео",

            description=(
                "Оплата доступа к видео"
            ),

            payload=PAYMENT_PAYLOAD,

            # Для Telegram Stars provider token пустой
            provider_token="",

            currency="XTR",

            prices=[

                LabeledPrice(

                    label="🎬 Доступ к видео",

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

            "❌ Не удалось создать счёт.",

            show_alert=True

        )


# ============================================================
# PRE-CHECKOUT
# ============================================================

@dp.pre_checkout_query()
async def process_pre_checkout(
    query: PreCheckoutQuery
):

    # --------------------------------------------------------
    # Проверяем payload
    # --------------------------------------------------------

    if query.invoice_payload != PAYMENT_PAYLOAD:

        await query.answer(

            ok=False,

            error_message="Неверный платёж."

        )

        return

    # --------------------------------------------------------
    # Проверяем сумму
    # --------------------------------------------------------

    if query.total_amount != PRICE:

        await query.answer(

            ok=False,

            error_message="Неверная сумма."

        )

        return

    # --------------------------------------------------------
    # Подтверждаем платёж
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

    # --------------------------------------------------------
    # Проверяем payload
    # --------------------------------------------------------

    if payment.invoice_payload != PAYMENT_PAYLOAD:

        await message.answer(
            "❌ Ошибка платежа."
        )

        return

    user_id = message.from_user.id

    # --------------------------------------------------------
    # Получаем актуальную ссылку
    # --------------------------------------------------------

    video_link = get_video_link()

    # --------------------------------------------------------
    # Лог
    # --------------------------------------------------------

    print(
        "========================================"
    )

    print(
        "НОВАЯ ОПЛАТА"
    )

    print(
        f"User ID: {user_id}"
    )

    print(
        f"Stars: {payment.total_amount}"
    )

    print(
        f"Video: {video_link}"
    )

    print(
        "Charge ID:",
        payment.telegram_payment_charge_id
    )

    print(
        "========================================"
    )

    # --------------------------------------------------------
    # Отправляем видео
    # --------------------------------------------------------

    await message.answer(

        "✅ Оплата успешно завершена!\n\n"

        "🎬 Ваше видео здесь:\n\n"

        f"{video_link}"

    )

    # --------------------------------------------------------
    # Уведомляем администратора
    # --------------------------------------------------------

    try:

        username = message.from_user.username

        if username:

            username_text = f"@{username}"

        else:

            username_text = "без username"

        await bot.send_message(

            ADMIN_ID,

            "💰 НОВАЯ ОПЛАТА\n\n"

            f"👤 Пользователь: "
            f"{message.from_user.full_name}\n"

            f"🔗 Username: "
            f"{username_text}\n"

            f"🆔 ID: "
            f"{user_id}\n\n"

            f"⭐️ Оплачено: "
            f"{payment.total_amount} Stars"

        )

    except Exception as error:

        print(
            f"Ошибка уведомления админа: {error}"
        )


# ============================================================
# /SUPPORT
# ============================================================

@dp.message(Command("support"))
async def support(
    message: Message
):

    await message.answer(

        "🆘 Если вам нужна помощь, "
        "пишите сюда:\n\n"
        "@yuzaye"

    )


# ============================================================
# /CHANGE
# ============================================================

@dp.message(Command("change"))
async def change_video(
    message: Message
):

    # --------------------------------------------------------
    # Только администратор
    # --------------------------------------------------------

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ У вас нет доступа к этой команде."
        )

        return

    # --------------------------------------------------------
    # Получаем ссылку
    # --------------------------------------------------------

    text = message.text or ""

    new_link = text[
        len("/change"):
    ].strip()

    # --------------------------------------------------------
    # Если ссылка не указана
    # --------------------------------------------------------

    if not new_link:

        await message.answer(

            "❌ Вы не указали ссылку.\n\n"

            "Использование:\n"

            "/change https://t.me/your_video"

        )

        return

    # --------------------------------------------------------
    # Проверяем ссылку
    # --------------------------------------------------------

    if not (
        new_link.startswith("https://t.me/")
        or new_link.startswith("http://t.me/")
        or new_link.startswith("t.me/")
    ):

        await message.answer(

            "❌ Неверная ссылка.\n\n"

            "Нужна ссылка вида:\n"

            "https://t.me/..."

        )

        return

    # --------------------------------------------------------
    # Сохраняем новую ссылку
    # --------------------------------------------------------

    set_video_link(new_link)

    await message.answer(

        "✅ Ссылка успешно изменена!\n\n"

        "🎬 Новая ссылка:\n"

        f"{new_link}"

    )

    print(
        f"Администратор изменил ссылку: {new_link}"
    )


# ============================================================
# /USERS
# ============================================================

@dp.message(Command("users"))
async def users_count(
    message: Message
):

    # Только администратор

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ У вас нет доступа к этой команде."
        )

        return

    users = load_users()

    await message.answer(

        "📊 Статистика бота\n\n"

        f"👥 Всего пользователей: "
        f"{len(users)}"

    )


# ============================================================
# /BROADCAST
# ============================================================

@dp.message(Command("broadcast"))
async def broadcast(
    message: Message
):

    # Только администратор

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ У вас нет доступа к этой команде."
        )

        return

    text = message.text or ""

    broadcast_text = text[
        len("/broadcast"):
    ].strip()

    # --------------------------------------------------------
    # Если текст не указан
    # --------------------------------------------------------

    if not broadcast_text:

        users = load_users()

        await message.answer(

            "📢 Рассылка\n\n"

            f"👥 Получателей: {len(users)}\n\n"

            "Использование:\n\n"

            "/broadcast Ваш текст"

        )

        return

    # --------------------------------------------------------
    # Получаем пользователей
    # --------------------------------------------------------

    users = load_users()

    await message.answer(

        "📢 Начинаю рассылку.\n\n"

        f"👥 Получателей: {len(users)}"

    )

    success = 0

    failed = 0

    # --------------------------------------------------------
    # Рассылка
    # --------------------------------------------------------

    for user_id in users:

        try:

            await bot.send_message(

                chat_id=user_id,

                text=broadcast_text

            )

            success += 1

            await asyncio.sleep(0.1)

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

    # --------------------------------------------------------
    # Результат
    # --------------------------------------------------------

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
        f"HTTP server started "
        f"on port {PORT}"
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    print(
        "========================================"
    )

    print(
        "Telegram Bot is starting..."
    )

    print(
        f"Цена: {PRICE} Stars"
    )

    print(
        f"Видео: {get_video_link()}"
    )

    print(
        f"Admin ID: {ADMIN_ID}"
    )

    print(
        f"HTTP port: {PORT}"
    )

    print(
        "========================================"
    )

    await start_web_server()

    await dp.start_polling(
        bot
    )


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
