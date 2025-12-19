from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

router = Router()
OWNER_ID = 6782041245  # Убедись, что это твой ID!

def is_owner(msg: Message): 
    return msg.from_user.id == OWNER_ID

class AddProduct(StatesGroup):
    name = State()
    price = State()
    category = State()
    photo = State()
    sizes = State()

@router.message(F.text == "👑 Админка")
async def admin_panel(message: Message):
    if not is_owner(message): 
        await message.answer("❌ Доступ запрещён")
        return
    from keyboards.kb import admin_menu
    await message.answer("👑 Админ-панель", reply_markup=admin_menu())

@router.message(F.text == "➕ Добавить товар")
async def add_product_start(message: Message, state: FSMContext):
    if not is_owner(message): 
        await message.answer("❌ Доступ запрещён")
        return
    await state.set_state(AddProduct.name)
    await message.answer("Введите название товара:")

@router.message(AddProduct.name)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProduct.price)
    await message.answer("Введите цену (только число, например: 2990):")

@router.message(AddProduct.price)
async def add_product_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError
        await state.update_data(price=price)
        await state.set_state(AddProduct.category)
        await message.answer("Введите категорию (например: Платья, Джинсы):")
    except ValueError:
        await message.answer("❌ Неверная цена. Введите число > 0:")

@router.message(AddProduct.category)
async def add_product_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await state.set_state(AddProduct.photo)
    await message.answer("Отправьте фото товара:")

@router.message(AddProduct.photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext):
    photo_url = message.photo[-1].file_id
    await state.update_data(photo_url=photo_url)
    await state.set_state(AddProduct.sizes)
    await message.answer("Введите размеры через запятую (например: 36, 38, 40) или '-' если нет:")

@router.message(AddProduct.photo)
async def photo_invalid(message: Message):
    await message.answer("❌ Отправьте фото!")

@router.message(AddProduct.sizes)
async def add_product_sizes(message: Message, state: FSMContext):
    sizes = message.text.strip()
    if sizes == "-":
        sizes = []
    else:
        sizes = [s.strip() for s in sizes.split(",")]
    
    data = await state.get_data()
    data["sizes"] = sizes

    try:
        from utils.db import save_product
        save_product(data)
        await message.answer("✅ Товар добавлен!")
    except Exception as e:
        logging.error(f"Ошибка добавления: {e}")
        await message.answer("❌ Не удалось сохранить товар.")
    
    await state.clear()
