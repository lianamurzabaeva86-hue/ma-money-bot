from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import logging

router = Router()

@router.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    from keyboards.kb import main_menu
    await message.answer(
        "👗 Добро пожаловать в магазин одежды!\nВыберите действие:",
        reply_markup=main_menu(message.from_user.id)  # ← передаём ID
    )

@router.message(F.text.in_(["⬅️ Назад", "⬅️ В меню"]))
async def back_to_menu(message: Message, state: FSMContext):
    await state.clear()
    from keyboards.kb import main_menu
    await message.answer("Главное меню:", reply_markup=main_menu(message.from_user.id))
