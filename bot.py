import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# ВАШ ТОКЕН (Обязательно смените его в @BotFather!)
API_TOKEN = '8719240397:AAFgT2cH5QfJy-d1PM4_5dYGMH5RqoCoAO8'
# ССЫЛКА НА ВАШ САЙТ (Где лежит index.html)
WEBAPP_URL = 'https://kiberkiller2000.github.io/my-use/' 

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    # Кнопка открытия Mini App
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    await message.answer(
        "👋 Привет! Нажми на кнопку ниже, чтобы активировать софт Free Fire.",
        reply_markup=markup
    )

# Обработка данных из Mini App
@dp.message(F.web_app_data)
async def web_app_receive(message: types.Message):
    data = message.web_app_data.data
    if data.startswith("activated:"):
        key = data.split(":")[1]
        
        text = (
            f"✅ **Ключ `{key}` успешно принят!**\n\n"
            "📥 **Инструкция по установке сертификата:**\n"
            "1. Перейдите по ссылке: [СКАЧАТЬ СЕРТИФИКАТ](https://example.com)\n"
            "2. Установите профиль в настройках iPhone.\n"
            "3. Настройки -> Основные -> VPN и управление устройством -> Доверять разработчику."
        )
        await message.answer(text, parse_mode="Markdown")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
