import logging
import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F

# Загружаем переменные окружения
load_dotenv()

# --- НАСТРОЙКИ ---
# Вместо os.getenv пишем просто строку в кавычках
API_TOKEN = '8281850605:AAH4P2nxaHykcAgh2TvIwKoWu-oo61Na0jo'
SOURCE_GROUP_ID = int(os.getenv('SOURCE_GROUP_ID', -1002153720177))
TARGET_GROUP_ID = int(os.getenv('TARGET_GROUP_ID', -1002187172073))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(F.chat.id == SOURCE_GROUP_ID)
async def forward_new_messages(message: types.Message):
    """
    Функция ловит все сообщения из группы-источника 
    и копирует их в группу-цель.
    """
    try:
        # Используем copy_message, чтобы сообщение выглядело как родное, 
        # а не как "пересланное от кого-то"
        await message.copy_to(chat_id=TARGET_GROUP_ID)
        logging.info(f"Сообщение {message.message_id} успешно скопировано.")
    except Exception as e:
        logging.error(f"Ошибка при копировании: {e}")

async def main():
    print("🚀 Бот-пересыльщик запущен и следит за новыми объявлениями...")
    await bot.delete_webhook(drop_pending_updates=True) # Чтобы не пересылать старое при включении
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
