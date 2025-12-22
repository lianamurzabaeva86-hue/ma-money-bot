from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
import logging

router = Router()
OWNER_ID = 6782041245  # Твой Telegram ID

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
        category = message.text[2:]  # Убираем "👗 "
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
            "👉 Напишите **ID товара и размер** (например: `5 L`), "
            "и владелец магазина свяжется с вами напрямую в Telegram.",
            reply_markup=product_kb()
        )
    except Exception as e:
        logging.error(f"Ошибка загрузки товаров: {e}")
        await message.answer("❌ Ошибка при показе товаров.")

@router.message(F.text == "🛒 Заказать")
async def order_help(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Напишите **ID товара и размер** (например: `5 L`). "
        "Владелец увидит ваше сообщение и напишет вам в личные сообщения Telegram."
    )

# 🔑 ОСНОВНАЯ ФУНКЦИЯ: любое сообщение → пересылка владельцу
@router.message(F.text)
async def forward_to_owner(message: Message, state: FSMContext):
    await state.clear()
    try:
        # Пересылаем полное сообщение — владелец видит профиль клиента
        await message.bot.forward_message(
            chat_id=OWNER_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        await message.answer(
            "✅ Отправлено! Владелец магазина получил ваше сообщение "
            "и свяжется с вами в личных сообщениях Telegram."
        )
    except Exception as e:
        logging.error(f"Ошибка пересылки: {e}")
        await message.answer("❌ Не удалось отправить. Попробуйте позже.")

@router.message(F.text.in_(["⬅️ Назад", "⬅️ Назад к категориям"]))
async def back_to_categories(message: Message, state: FSMContext):
    await show_categories(message, state)
