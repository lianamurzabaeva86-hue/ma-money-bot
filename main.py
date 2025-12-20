import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from handlers import start, catalog, admin

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не установлен!")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_SECRET = "my-secret"
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "https://clothing-bot.onrender.com").rstrip("/")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def ensure_webhook():
    while True:
        try:
            info = await bot.get_webhook_info()
            expected_url = f"{BASE_URL}{WEBHOOK_PATH}"
            if info.url != expected_url:
                await bot.set_webhook(expected_url, secret_token=WEBHOOK_SECRET)
                print(f"🔁 Webhook восстановлен: {expected_url}")
        except Exception as e:
            print(f"⚠️ Ошибка проверки webhook: {e}")
        await asyncio.sleep(300)

async def on_startup(app):
    app["webhook_task"] = asyncio.create_task(ensure_webhook())
    try:
        await bot.set_webhook(f"{BASE_URL}{WEBHOOK_PATH}", secret_token=WEBHOOK_SECRET)
        print("✅ Webhook установлен")
    except Exception as e:
        print(f"❌ Ошибка при старте: {e}")

async def on_shutdown(app):
    task = app.get("webhook_task")
    if task:
        task.cancel()
    await bot.delete_webhook(drop_pending_updates=True)

def main():
    dp.include_routers(start.router, catalog.router, admin.router)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=WEBHOOK_SECRET).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    main()
