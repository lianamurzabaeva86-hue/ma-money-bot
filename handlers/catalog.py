from aiogram import Router, F
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError
import logging

router = Router()
OWNER_ID = 6782041245

@router.message(F.text == "📦 Каталог")
async def show_categories(message: Message):
    try:
        from utils.db import get_categories
        categories = get_categories()
        if not categories:
            await message.answer("Каталог пока пуст.")
            return
        from keyboards.kb import categories_kb
        await message.answer("Выберите категорию:", reply_markup=categories_kb(categories))
    except Exception as e:
        logging.error(f"Каталог: {e}")
        await message.answer("❌ Не удалось загрузить категории.")

@router.message(F.text.startswith("👗 "))
async def show_products_by_category(message: Message):
    try:
        category = message.text[2:]
        from utils.db import get_products_by_category
        products = get_products_by_category(category)
        if not products:
            await message.answer("В этой категории нет товаров.")
            return
        from keyboards.kb import product_kb
        for p in products:
            caption = f"ID: {p['id']}\n{p['name']}\n💰 {p['price']} ₽"
            if p.get("sizes"):
                caption += f"\n📏 Размеры: {', '.join(p['sizes'])}"
            try:
                await message.answer_photo(photo=p["photo_url"], caption=caption)
            except TelegramAPIError:
                await message.answer(f"{caption}\n📷 [Фото недоступно]")
        await message.answer(
            "Чтобы заказать, напишите: **ID и размер** (например: `5 36`).",
            reply_markup=product_kb()
        )
    except Exception as e:
        logging.error(f"Товары: {e}")
        await message.answer("❌ Ошибка загрузки товаров.")

@router.message(F.text == "🛒 Заказать")
async def order_help(message: Message):
    await message.answer("Напишите ID товара и размер (например: `5 36`).")

@router.message(F.text.regexp(r'^\d+\s+.+$'))
async def handle_order_text(message: Message):
    try:
        if not message.from_user.username:
            await message.answer("❌ У вас нет @username. Задайте его в настройках Telegram.")
            return
        parts = message.text.split(maxsplit=1)
        product_id = int(parts[0])
        size = parts[1].strip()
        from utils.db import get_product_by_id, save_order
        product = get_product_by_id(product_id)
        if not product:
            await message.answer("❌ Товар не найден.")
            return
        sizes = product.get("sizes", [])
        if sizes and size not in sizes:
            await message.answer(f"❌ Нет размера {size}. Доступно: {', '.join(sizes)}")
            return
        save_order(message.from_user.id, message.from_user.username, product_id, size)
        await message.bot.send_message(
            OWNER_ID,
            f"🆕 ЗАКАЗ!\nТовар: {product['name']}\nID: {product_id}\nРазмер: {size}\n@{message.from_user.username}"
        )
        await message.answer("✅ Заказ отправлен! Владелец свяжется с вами.")
    except Exception as e:
        logging.error(f"Заказ: {e}")
        await message.answer("❌ Ошибка оформления заказа.")

@router.message(F.text.in_(["⬅️ Назад", "⬅️ Назад к категориям"]))
async def back_to_categories(message: Message):
    await show_categories(message)