import asyncio
import json
import os

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


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

PRICE = 100
VIDEO_FILE = "video.mp4"
USERS_FILE = "users.json"


# =========================
# ПРОВЕРКА ТОКЕНА
# =========================

if not BOT_TOKEN:
    raise ValueError("Ошибка: переменная BOT_TOKEN не найдена!")


# =========================
# СОЗДАНИЕ БОТА
# =========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# РАБОТА С ПОЛЬЗОВАТЕЛЯМИ
# =========================

def load_users():
    if not os.path.exists(USERS_FILE):
        return []

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file)


# =========================
# КНОПКА ПОКУПКИ
# =========================

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


# =========================
# КОМАНДА /START
# =========================

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
            "Нажмите кнопку ниже, чтобы получить его снова.",
            reply_markup=keyboard
        )
        return

    # Новый пользователь
    await message.answer(
        "🎥 Добро пожаловать!\n\n"
        f"Стоимость видео: ⭐ {PRICE} Stars\n\n"
        "Нажмите кнопку ниже, чтобы купить видео.",
        reply_markup=buy_keyboard
    )


# =========================
# ПОКУПКА ВИДЕО
# =========================

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


# =========================
# ПОДТВЕРЖДЕНИЕ ПЛАТЕЖА
# =========================

@dp.pre_checkout_query()
async def process_pre_checkout(
    pre_checkout_query: PreCheckoutQuery
):
    await pre_checkout_query.answer(
        ok=True
    )


# =========================
# УСПЕШНАЯ ОПЛАТА
# =========================

@dp.message(F.successful_payment)
async def successful_payment(message: Message):

    user_id = message.from_user.id

    users = load_users()

    # Добавляем пользователя в список купивших
    if user_id not in users:
        users.append(user_id)
        save_users(users)

    # Проверяем наличие видео
    if not os.path.exists(VIDEO_FILE):
        await message.answer(
            "❌ Оплата прошла успешно, "
            "но видео временно недоступно. "
            "Пожалуйста, свяжитесь с администратором."
        )
        return

    await message.answer(
        "✅ Оплата успешно завершена!\n\n"
        "🎥 Сейчас отправлю ваше видео..."
    )

    # Отправляем видео
    video = FSInputFile(VIDEO_FILE)

    await message.answer_video(
        video=video,
        caption="🎉 Спасибо за покупку! Приятного просмотра!"
    )


# =========================
# ПОВТОРНАЯ ОТПРАВКА ВИДЕО
# =========================

@dp.callback_query(F.data == "get_video")
async def get_video(callback: CallbackQuery):

    user_id = callback.from_user.id

    users = load_users()

    # Проверяем, покупал ли пользователь видео
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

    video = FSInputFile(VIDEO_FILE)

    await callback.message.answer_video(
        video=video,
        caption="🎥 Ваше видео."
    )

    await callback.answer()


# =========================
# ЗАПУСК БОТА
# =========================

async def main():

    print("=================================")
    print("Бот запускается...")
    print("=================================")

    await dp.start_polling(bot)


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    asyncio.run(main())
