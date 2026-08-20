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


# ==========================================
# НАСТРОЙКИ
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

PRICE = 6

VIDEO_FILE = "video.mp4"

# Все пользователи, которые нажали /start
USERS_FILE = "users.json"

# Пользователи, которые купили видео
BUYERS_FILE = "buyers.json"

# ТВОЙ TELEGRAM ID
ADMIN_ID = 5800940022

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
        FileNotFoundError
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
# ПОЛЬЗОВАТЕЛИ
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
# ПОКУПАТЕЛИ
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

    # ======================================
    # СОХРАНЯЕМ ПОЛЬЗОВАТЕЛЯ
    # ======================================

    users = load_users()

    if user_id not in users:

        users.append(user_id)

        save_users(users)

        print(
            f"Новый пользователь добавлен: {user_id}"
        )


    # ======================================
    # ПРОВЕРЯЕМ ПОКУПКУ
    # ======================================

    buyers = load_buyers()

    if user_id in buyers:

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


    # ======================================
    # НОВЫЙ ПОЛЬЗОВАТЕЛЬ
    # ======================================

    await message.answer(

        "🎥 Добро пожаловать!\n\n"

        f"Стоимость видео: ⭐ {PRICE} Stars\n\n"

        "Нажмите кнопку ниже, "
        "чтобы купить видео.",

        reply_markup=buy_keyboard

    )


# ==========================================
# КОМАНДА /USERS
# ==========================================

@dp.message(Command("users"))
async def users_count(message: Message):

    # Только для администратора

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ У вас нет доступа к этой команде."
        )

        return


    # Загружаем пользователей

    users = load_users()

    users_count_number = len(users)


    # Показываем количество

    await message.answer(

        "📊 Статистика бота\n\n"

        f"👥 Всего пользователей: "
        f"{users_count_number}\n\n"

        "📢 Именно столько пользователей "
        "получит сообщение при рассылке."

    )


# ==========================================
# ПОКУПКА ВИДЕО
# ==========================================

@dp.callback_query(
    F.data == "buy_video"
)
async def buy_video(
    callback: CallbackQuery
):

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

@dp.message(
    F.successful_payment
)
async def successful_payment(
    message: Message
):

    user_id = message.from_user.id


    # ======================================
    # ДОБАВЛЯЕМ ПОКУПАТЕЛЯ
    # ======================================

    buyers = load_buyers()

    if user_id not in buyers:

        buyers.append(user_id)

        save_buyers(
            buyers
        )


    # ======================================
    # ПРОВЕРЯЕМ ВИДЕО
    # ======================================

    if not os.path.exists(
        VIDEO_FILE
    ):

        await message.answer(

            "❌ Оплата прошла успешно, "
            "но файл видео сейчас недоступен.\n\n"

            "Пожалуйста, обратитесь "
            "к администратору @yuzaye."

        )

        return


    # ======================================
    # СООБЩЕНИЕ ОБ УСПЕШНОЙ ОПЛАТЕ
    # ======================================

    await message.answer(

        "✅ Оплата успешно завершена!\n\n"
        "🎥 Отправляю ваше видео..."

    )


    # ======================================
    # ОТПРАВЛЯЕМ ВИДЕО
    # ======================================

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


# ==========================================
# ПОВТОРНО ПОЛУЧИТЬ ВИДЕО
# ==========================================

@dp.callback_query(
    F.data == "get_video"
)
async def get_video(
    callback: CallbackQuery
):

    user_id = callback.from_user.id


    # ======================================
    # ПРОВЕРЯЕМ ПОКУПАТЕЛЯ
    # ======================================

    buyers = load_buyers()

    if user_id not in buyers:

        await callback.answer(

            "Сначала необходимо купить видео.",

            show_alert=True

        )

        return


    # ======================================
    # ПРОВЕРЯЕМ ФАЙЛ
    # ======================================

    if not os.path.exists(
        VIDEO_FILE
    ):

        await callback.answer(

            "Видео временно недоступно.",

            show_alert=True

        )

        return


    # ======================================
    # ОТПРАВЛЯЕМ ВИДЕО
    # ======================================

    video = FSInputFile(
        VIDEO_FILE
    )

    await callback.message.answer_video(

        video=video,

        caption="🎥 Ваше видео."

    )

    await callback.answer()


# ==========================================
# РАССЫЛКА
# ==========================================

@dp.message(
    Command("broadcast")
)
async def broadcast(
    message: Message
):

    # ======================================
    # ПРОВЕРЯЕМ АДМИНИСТРАТОРА
    # ======================================

    if message.from_user.id != ADMIN_ID:

        await message.answer(

            "❌ У вас нет доступа "
            "к этой команде."

        )

        return


    # ======================================
    # ПОЛУЧАЕМ ТЕКСТ
    # ======================================

    text = message.text or ""

    broadcast_text = text[
        len("/broadcast"):
    ].strip()


    # ======================================
    # ЕСЛИ ТЕКСТ НЕ УКАЗАН
    # ======================================

    if not broadcast_text:

        users = load_users()

        await message.answer(

            "📢 Рассылка\n\n"

            f"👥 Получателей: {len(users)}\n\n"

            "Чтобы сделать рассылку, "
            "напишите:\n\n"

            "/broadcast Ваш текст"

        )

        return


    # ======================================
    # ЗАГРУЖАЕМ ПОЛЬЗОВАТЕЛЕЙ
    # ======================================

    users = load_users()


    await message.answer(

        "📢 Начинаю рассылку.\n\n"

        f"👥 Получателей: {len(users)}"

    )


    success = 0

    failed = 0


    # ======================================
    # ОТПРАВЛЯЕМ СООБЩЕНИЕ
    # ======================================

    for user_id in users:

        try:

            await bot.send_message(

                chat_id=user_id,

                text=broadcast_text

            )

            success += 1


            # Небольшая пауза

            await asyncio.sleep(
                0.05
            )


        except Exception as error:

            failed += 1

            print(

                f"Ошибка отправки "
                f"{user_id}: {error}"

            )


    # ======================================
    # РЕЗУЛЬТАТ
    # ======================================

    await message.answer(

        "✅ Рассылка завершена!\n\n"

        f"📨 Успешно отправлено: {success}\n"

        f"❌ Ошибок: {failed}"

    )


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

        f"HTTP server started "
        f"on port {PORT}"

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
# ЗАПУСК
# ==========================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
