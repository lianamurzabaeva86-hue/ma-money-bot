import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from handlers import start, catalog, admin
import logging

logging.basicConfig(level=logging.INFO)

# === Проверка токена ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не установлен!")

# === Webhook настройки ===
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_SECRET = "my-secret"
# Убираем лишние пробелы в URL (частая ошибка!)
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "https://ma-money-bot.onrender.com").rstrip("/")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Поддержка webhook (переподключение при сбое) ===
async def ensure_webhook():
    while True:
        try:
            await bot.set_webhook(
                url=f"{BASE_URL}{WEBHOOK_PATH}",
                secret_token=WEBHOOK_SECRET,
                allowed_updates=dp.resolve_used_update_types()
            )
            logging.info(f"✅ Webhook активен: {BASE_URL}{WEBHOOK_PATH}")
        except Exception as e:
            logging.error(f"🔁 Ошибка установки webhook: {e}")
        await asyncio.sleep(60)

# === События при запуске/остановке ===
async def on_startup(app):
    app["webhook_task"] = asyncio.create_task(ensure_webhook())

async def on_shutdown(app):
    task = app.get("webhook_task")
    if task:
        task.cancel()
    await bot.delete_webhook(drop_pending_updates=True)

# === Главная функция ===
def main():
    # Подключаем роутеры
    dp.include_routers(start.router, catalog.router, admin.router)

    # Создаём приложение
    app = web.Application()

    # 🔑 Health-check для Render (обязательно!)
    async def healthcheck(request):
        return web.Response(text="OK", content_type="text/plain")

    app.router.add_get("/healthz", healthcheck)

    # Регистрируем webhook
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Запуск
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"🚀 Запуск на порту {port}")
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
