import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# ТОКЕН И ССЫЛКА (Меняй ?v= каждый раз при обновлении сайта)
API_TOKEN = '8719240397:AAFgT2cH5QfJy-d1PM4_5dYGMH5RqoCoAO8'
WEBAPP_URL = 'https://kiberkiller2000.github.io/my-use/'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Открыть софт", web_app=WebAppInfo(url=WEBAPP_URL))]])
    await message.answer("👋 Нажми на кнопку ниже для авторизации:", reply_markup=kb)

@dp.message(F.web_app_data)
async def handle_data(message: types.Message):
    data = message.web_app_data.data
    d = dict(item.split(":") for item in data.split("|"))
    m, k = d.get("mode"), d.get("key")
    h, p = ("92.118.206.166", "30025") if m == "Antena" else ("194.62.248.55", "30011")

    text = f"✅ **Ключ `{k}` отправлен!**\n\n📍 **Host:** `{h}`\n🔢 **Port:** `{p}`\n\n⚠️ Отключайте VPN в лобби!"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Копировать Host", switch_inline_query_current_chat=h)],
        [InlineKeyboardButton(text="📋 Копировать Port", switch_inline_query_current_chat=p)]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

async def main(): await dp.start_polling(bot)
if __name__ == '__main__': asyncio.run(main())
