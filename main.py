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
    FSInputFile
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

PRICE = 100
VIDEO_FILE = "video.mp4"
USERS_FILE = "users.json"


def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f)


menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"⭐ Купить видео ({PRICE} Stars)",
                callback_data="buy"
            )
        ]
    ]
)
@dp.message(CommandStart())
async def start(message: Message):
    users = load_users()

    if message.from_user.id in users:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎥 Получить видео",
                        callback_data="video"
                    )
                ]
            ]
        )

        await message.answer(
            "✅ Вы уже купили это видео.",
            reply_markup=keyboard
        )
        return

    await message.answer(
        "🎥 Привет!\n\n"
        "Нажми кнопку ниже, чтобы купить видео.",
        reply_markup=menu
    )


@dp.callback_query(F.data == "buy")
async def buy(callback: CallbackQuery):
    await callback.message.answer_invoice(
        title="Видео",
        description="Покупка видео",
        payload="video_buy",
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
  @dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    users = load_users()

    if message.from_user.id not in users:
        users.append(message.from_user.id)
        save_users(users)

    video = FSInputFile(VIDEO_FILE)

    await message.answer("✅ Оплата прошла успешно!")

    await message.answer_video(
        video=video,
        caption="🎉 Спасибо за покупку!"
    )


@dp.callback_query(F.data == "video")
async def send_video(callback: CallbackQuery):
    video = FSInputFile(VIDEO_FILE)

    await callback.message.answer_video(
        video=video,
        caption="🎥 Ваше видео."
    )

    await callback.answer()
  async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
