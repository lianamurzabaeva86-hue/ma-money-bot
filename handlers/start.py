from aiogram import Router, F
from aiogram.types import Message
import logging

router = Router()

@router.message(F.text == "/start")
async def start(message: Message):
    try:
        from utils.db import add_user
        add_user(message.from_user.id, message.from_user.username)
        from keyboards.kb import main_menu
        await message.answer(
            "👗 Добро пожаловать в магазин одежды!\nВыберите действие:",
            reply_markup=main_menu(message.from_user.id)
        )
    except Exception as e:
        logging.error(f"Ошибка в /start: {e}")
        await message.answer("Добро пожаловать! Меню временно недоступно.")

@router.message(F.text.in_(["⬅️ Назад", "⬅️ В меню"]))
async def back_to_menu(message: Message):
    try:
        from keyboards.kb import main_menu
        await message.answer("Главное меню:", reply_markup=main_menu(message.from_user.id))
    except Exception as e:
        logging.error(f"Ошибка меню: {e}")
        await message.answer("Главное меню временно недоступно.")