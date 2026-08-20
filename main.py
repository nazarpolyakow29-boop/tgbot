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
    FSInputFile,
)
from aiogram.exceptions import TelegramRetryAfter


# ==========================================
# НАСТРОЙКИ
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

PRICE = 6

VIDEO_FILE = "video.mp4"

USERS_FILE = "users.json"
BUYERS_FILE = "buyers.json"

ADMIN_ID = 5800940022

PORT = int(os.getenv("PORT", 10000))

PAYMENT_PAYLOAD = "video_purchase"


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
# JSON
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
    return load_json(USERS_FILE)


def save_users(users):
    save_json(USERS_FILE, users)


# ==========================================
# BUYERS
# ==========================================

def load_buyers():
    return load_json(BUYERS_FILE)


def save_buyers(buyers):
    save_json(BUYERS_FILE, buyers)


# ==========================================
# КЛАВИАТУРА ПОКУПКИ
# ==========================================

def get_buy_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⭐ Купить видео — {PRICE} Stars",
                    callback_data="buy_video"
                )
            ]
        ]
    )


# ==========================================
# КЛАВИАТУРА ПОЛУЧЕНИЯ ВИДЕО
# ==========================================

def get_video_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎥 Получить видео",
                    callback_data="get_video"
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
    # Сохраняем пользователя
    # --------------------------------------

    users = load_users()

    if user_id not in users:

        users.append(user_id)

        save_users(users)

        print(
            f"Новый пользователь: {user_id}"
        )

    # --------------------------------------
    # Проверяем покупку
    # --------------------------------------

    buyers = load_buyers()

    if user_id in buyers:

        await message.answer(
            "✅ Вы уже приобрели это видео.\n\n"
            "Нажмите кнопку ниже, чтобы "
            "получить его снова.",
            reply_markup=get_video_keyboard()
        )

        return

    # --------------------------------------
    # Новый пользователь
    # --------------------------------------

    await message.answer(
        "🎥 Добро пожаловать!\n\n"
        f"Стоимость видео: ⭐ {PRICE} Stars\n\n"
        "После оплаты видео будет "
        "отправлено автоматически.\n\n"
        "Нажмите кнопку ниже, чтобы купить видео.",
        reply_markup=get_buy_keyboard()
    )


# ==========================================
# /USERS
# ==========================================

@dp.message(Command("users"))
async def users_count(message: Message):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ У вас нет доступа к этой команде."
        )

        return

    users = load_users()
    buyers = load_buyers()

    await message.answer(
        "📊 Статистика бота\n\n"
        f"👥 Пользователей: {len(users)}\n"
        f"💰 Покупателей: {len(buyers)}"
    )


# ==========================================
# ПОКУПКА
# ==========================================

@dp.callback_query(F.data == "buy_video")
async def buy_video(callback: CallbackQuery):

    try:

        await callback.message.answer_invoice(

            title="🎥 Видео",

            description="Покупка доступа к видео",

            payload=PAYMENT_PAYLOAD,

            provider_token="",

            currency="XTR",

            prices=[
                LabeledPrice(
                    label="Видео",
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

    if pre_checkout_query.invoice_payload != PAYMENT_PAYLOAD:

        await pre_checkout_query.answer(
            ok=False,
            error_message="Неверный платёж."
        )

        return

    # Всё правильно

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
    # Проверяем payload
    # --------------------------------------

    if payment.invoice_payload != PAYMENT_PAYLOAD:

        print(
            f"Неизвестный payload от {user_id}: "
            f"{payment.invoice_payload}"
        )

        await message.answer(
            "❌ Ошибка платежа."
        )

        return

    # --------------------------------------
    # Добавляем покупателя
    # --------------------------------------

    buyers = load_buyers()

    if user_id not in buyers:

        buyers.append(user_id)

        save_buyers(buyers)

    # --------------------------------------
    # Проверяем видео
    # --------------------------------------

    if not os.path.exists(VIDEO_FILE):

        print(
            f"Файл {VIDEO_FILE} не найден!"
        )

        await message.answer(
            "✅ Оплата успешно завершена!\n\n"
            "Но видео временно недоступно.\n"
            "Пожалуйста, свяжитесь с администратором."
        )

        return

    # --------------------------------------
    # Сообщение
    # --------------------------------------

    await message.answer(
        "✅ Оплата успешно завершена!\n\n"
        "🎥 Отправляю ваше видео..."
    )

    # --------------------------------------
    # Отправляем видео
    # --------------------------------------

    try:

        video = FSInputFile(
            VIDEO_FILE
        )

        await message.answer_video(
            video=video,
            caption=(
                "🎉 Спасибо за покупку!\n\n"
                "Приятного просмотра!"
            )
        )

    except Exception as error:

        print(
            f"Ошибка отправки видео: {error}"
        )

        await message.answer(
            "⚠️ Оплата прошла успешно, "
            "но не удалось отправить видео.\n\n"
            "Пожалуйста, нажмите /start "
            "немного позже."
        )


# ==========================================
# ПОВТОРНО ПОЛУЧИТЬ ВИДЕО
# ==========================================

@dp.callback_query(F.data == "get_video")
async def get_video(
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    # --------------------------------------
    # Проверяем покупку
    # --------------------------------------

    buyers = load_buyers()

    if user_id not in buyers:

        await callback.answer(
            "Сначала необходимо купить видео.",
            show_alert=True
        )

        return

    # --------------------------------------
    # Проверяем файл
    # --------------------------------------

    if not os.path.exists(VIDEO_FILE):

        await callback.answer(
            "Видео временно недоступно.",
            show_alert=True
        )

        return

    # --------------------------------------
    # Отправляем видео
    # --------------------------------------

    try:

        video = FSInputFile(
            VIDEO_FILE
        )

        await callback.message.answer_video(
            video=video,
            caption="🎥 Ваше видео."
        )

        await callback.answer()

    except Exception as error:

        print(
            f"Ошибка повторной отправки видео: {error}"
        )

        await callback.answer(
            "Не удалось отправить видео.",
            show_alert=True
        )


# ==========================================
# /BROADCAST
# ==========================================

@dp.message(Command("broadcast"))
async def broadcast(
    message: Message
):

    # --------------------------------------
    # Проверяем администратора
    # --------------------------------------

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ У вас нет доступа к этой команде."
        )

        return

    # --------------------------------------
    # Получаем текст
    # --------------------------------------

    text = message.text or ""

    broadcast_text = text[
        len("/broadcast"):
    ].strip()

    # --------------------------------------
    # Если текст не указан
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
    # Загружаем пользователей
    # --------------------------------------

    users = load_users()

    await message.answer(
        "📢 Начинаю рассылку.\n\n"
        f"👥 Получателей: {len(users)}"
    )

    success = 0
    failed = 0

    # --------------------------------------
    # Рассылка
    # --------------------------------------

    for user_id in users:

        try:

            await bot.send_message(
                chat_id=user_id,
                text=broadcast_text
            )

            success += 1

            # Небольшая задержка

            await asyncio.sleep(0.1)

        except TelegramRetryAfter as error:

            print(
                f"Telegram попросил подождать "
                f"{error.retry_after} секунд."
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
    # Результат
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
        f"Video file: {VIDEO_FILE}"
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

    # --------------------------------------
    # Проверяем видео
    # --------------------------------------

    if os.path.exists(VIDEO_FILE):

        print(
            f"Video found: {VIDEO_FILE}"
        )

    else:

        print(
            f"WARNING: {VIDEO_FILE} NOT FOUND!"
        )

    # --------------------------------------
    # HTTP сервер
    # --------------------------------------

    await start_web_server()

    # --------------------------------------
    # Telegram
    # --------------------------------------

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
