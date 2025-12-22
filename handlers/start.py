from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import logging

router = Router()

@router.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    try:
        # ❌ УДАЛЕНО: add_user(...) — не сохраняем пользователей
        from keyboards.kb import main_menu
        await message.answer(
            "👗 Добро пожаловать в магазин одежды!\nВыберите действие:",
            reply_markup=main_menu()
        )
    except Exception as e:
        logging.error(f"Ошибка в /start: {e}")
        await message.answer("Добро пожаловать! Меню временно недоступно.")

@router.message(F.text.in_(["⬅️ Назад", "⬅️ В меню"]))
async def back_to_menu(message: Message, state: FSMContext):
    await state.clear()
    try:
        from keyboards.kb import main_menu
        await message.answer("Главное меню:", reply_markup=main_menu())
    except Exception as e:
        logging.error(f"Ошибка меню: {e}")
        await message.answer("Главное меню временно недоступно.")
