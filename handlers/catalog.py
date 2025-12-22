from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
import logging
import re

router = Router()
OWNER_ID = 6782041245

# Паттерн: "цифра(ы) + пробел + что угодно" → например: "5 L", "123 XL", "7 40"
ORDER_PATTERN = re.compile(r'^\d+\s+.+$')

# --- Остальные хендлеры (категории, товары) остаются без изменений ---

@router.message(F.text == "📦 Каталог")
async def show_categories(message: Message, state: FSMContext):
    await state.clear()
    try:
        from utils.db import get_categories
        categories = get_categories()
        if not categories:
            await message.answer("Каталог пока пуст.")
            return
        from keyboards.kb import categories_kb
        await message.answer("Выберите категорию:", reply_markup=categories_kb(categories))
    except Exception as e:
        logging.error(f"Ошибка загрузки категорий: {e}")
        await message.answer("❌ Не удалось загрузить категории.")

@router.message(F.text.startswith("👗 "))
async def show_products_by_category(message: Message, state: FSMContext):
    await state.clear()
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
                caption += f"\n📏 Размеры: {p['sizes']}"
            photo_id = p.get("photo_file_id")
            if photo_id:
                try:
                    await message.answer_photo(photo=photo_id, caption=caption)
                except TelegramAPIError:
                    await message.answer(f"{caption}\n📷 [Фото недоступно]")
            else:
                await message.answer(caption)
        await message.answer(
            "👉 Напишите **ID товара и размер** (например: `5 L`)",
            reply_markup=product_kb()
        )
    except Exception as e:
        logging.error(f"Ошибка загрузки товаров: {e}")
        await message.answer("❌ Ошибка при показе товаров.")

@router.message(F.text == "🛒 Заказать")
async def order_help(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Напишите **ID товара и размер** (например: `5 L`).")

# 🔑 НОВЫЙ ХЕНДЛЕР: пересылка ТОЛЬКО похожих на заказ
@router.message(F.text, ORDER_PATTERN.match)
async def forward_order_message(message: Message, state: FSMContext):
    await state.clear()
    try:
        await message.bot.forward_message(
            chat_id=OWNER_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        await message.answer(
            "✅ Отправлено! Владелец свяжется с вами в Telegram."
        )
    except Exception as e:
        logging.error(f"Ошибка пересылки: {e}")
        await message.answer("❌ Не удалось отправить.")

# 🔑 Кнопки НАЗАД — обрабатываются ОТДЕЛЬНО, и НЕ попадают в заказ
@router.message(F.text.in_(["⬅️ Назад", "⬅️ Назад к категориям"]))
async def back_to_categories(message: Message, state: FSMContext):
    await state.clear()
    await show_categories(message, state)
