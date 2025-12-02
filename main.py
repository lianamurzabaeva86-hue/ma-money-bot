import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from handlers import user_handlers
from settings import BOT_TOKEN
from database import Database

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверка токена
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в Render Environment Variables!")

# Настройки Render
RENDER_SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME")
if not RENDER_SERVICE_NAME:
    raise RuntimeError("❌ RENDER_SERVICE_NAME не задан. Убедитесь, что сервис запущен на Render.")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{RENDER_SERVICE_NAME}.onrender.com{WEBHOOK_PATH}"
PORT = int(os.getenv("PORT", 10000))

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(user_handlers.router)

# Webhook lifecycle
async def on_startup(bot: Bot):
    logger.info(f"🚀 Бот запускается на Render")
    logger.info(f"🔧 Webhook URL: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)

async def on_shutdown(bot: Bot):
    await bot.session.close()

# Точка входа
def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot, on_startup=on_startup, on_shutdown=on_shutdown)
    
    logger.info("✅ Сервер запущен")
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()