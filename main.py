import asyncio
import json
import os

from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
    FSInputFile,
)


# ==========================================
# НАСТРОЙКИ
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

PRICE = 8

VIDEO_FILE = "video.mp4"
USERS_FILE = "users.json"

PORT = int(os.getenv("PORT", 10000))


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
# РАБОТА С ПОЛЬЗОВАТЕЛЯМИ
# ==========================================

def load_users():
    if not os.path.exists(USERS_FILE):
        return []

    try:
        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_users(users):
    with open(
        USERS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            users,
            file,
            ensure_ascii=False,
            indent=2
        )


# ==========================================
# КЛАВИАТУРА ПОКУПКИ
# ==========================================

buy_keyboard = InlineKeyboardMarkup(
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
# КОМАНДА /START
# ==========================================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id

    users = load_users()

    # Если пользователь уже покупал видео
    if user_id in users:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎥 Получить видео",
                        callback_data="get_video"
                    )
                ]
            ]
        )

        await message.answer(
            "✅ Вы уже приобрели это видео.\n\n"
            "Нажмите кнопку ниже, "
            "чтобы получить его снова.",
            reply_markup=keyboard
        )

        return

    # Новый пользователь

    await message.answer(
        "🎥 Добро пожаловать!\n\n"
        f"Стоимость видео: ⭐ {PRICE} Stars\n\n"
        "Нажмите кнопку ниже, "
        "чтобы купить видео.",
        reply_markup=buy_keyboard
    )


# ==========================================
# СОЗДАНИЕ ПЛАТЕЖА
# ==========================================

@dp.callback_query(F.data == "buy_video")
async def buy_video(callback: CallbackQuery):

    await callback.message.answer_invoice(

        title="🎥 Видео",

        description="Покупка доступа к видео",

        payload="video_purchase",

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


# ==========================================
# ПОДТВЕРЖДЕНИЕ ПЛАТЕЖА
# ==========================================

@dp.pre_checkout_query()
async def process_pre_checkout(
    pre_checkout_query: PreCheckoutQuery
):

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

    user_id = message.from_user.id

    users = load_users()

    # Добавляем покупателя
    if user_id not in users:

        users.append(user_id)

        save_users(users)


    # Проверяем наличие видео

    if not os.path.exists(VIDEO_FILE):

        await message.answer(
            "❌ Оплата прошла успешно, "
            "но файл видео сейчас недоступен.\n\n"
            "Пожалуйста, обратитесь к администратору @yuzaye , 🛑 Оплатили 1 раз- одноразовое видео, оплатили 2 раза- видео с возможностью сохранения, оплатили +1 раз- фотки генит🅰️лии"
        )

        return


    # Сообщение об успешной оплате

    await message.answer(
        "✅ Оплата успешно завершена!\n\n"
        "🎥 Отправляю ваше видео..."
    )


    # Загружаем видео

    video = FSInputFile(
        VIDEO_FILE
    )


    # Отправляем видео

    await message.answer_video(

        video=video,

        caption=(
            "🎉 Спасибо за покупку!\n\n"
            "Приятного просмотра!"
        )
    )


# ==========================================
# ПОВТОРНО ПОЛУЧИТЬ ВИДЕО
# ==========================================

@dp.callback_query(F.data == "get_video")
async def get_video(
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    users = load_users()


    # Проверяем покупку

    if user_id not in users:

        await callback.answer(

            "Сначала необходимо купить видео.",

            show_alert=True
        )

        return


    # Проверяем наличие файла

    if not os.path.exists(VIDEO_FILE):

        await callback.answer(

            "Видео временно недоступно.",

            show_alert=True
        )

        return


    # Отправляем видео

    video = FSInputFile(
        VIDEO_FILE
    )

    await callback.message.answer_video(

        video=video,

        caption="🎥 Ваше видео."
    )

    await callback.answer()


# ==========================================
# HTTP СЕРВЕР ДЛЯ RENDER
# ==========================================

async def health_check(
    request
):

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
        f"HTTP server started on port {PORT}"
    )


# ==========================================
# ЗАПУСК БОТА
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
        "================================="
    )


    # Запускаем HTTP сервер для Render

    await start_web_server()


    # Запускаем Telegram бота

    await dp.start_polling(
        bot
    )


# ==========================================
# ЗАПУСК
# ==========================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
