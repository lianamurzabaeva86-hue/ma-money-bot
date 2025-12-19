import os
import asyncio
import threading
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from handlers import start, catalog, admin

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Фон: запуск бота ---
async def run_bot():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_routers(start.router, catalog.router, admin.router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def start_bot_in_thread():
    asyncio.run(run_bot())

# --- Веб-сервер для Render ---
async def health(request):
    return web.json_response({"status": "ok", "message": "Bot is alive"})

def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    print("🚀 Запуск бота в фоне...")
    threading.Thread(target=start_bot_in_thread, daemon=True).start()
    print("🌐 Запуск веб-сервера для Render...")
    start_web_server()