from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

router = Router()
OWNER_ID = 6782041245

def is_owner(msg: Message):
    return msg.from_user.id == OWNER_ID

class AddProduct(StatesGroup):
    name = State()
    price = State()
    category = State()
    photo = State()
    sizes = State()

class DeleteProduct(StatesGroup):
    id = State()

@router.message(F.text == "👑 Админка")
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
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
async def add_product_photo(message: Message, state: FSMContext, bot: Bot):
    try:
        from utils.db import upload_to_imgbb
        photo_url = await upload_to_imgbb(bot, message.photo[-1].file_id)
        await state.update_data(photo_url=photo_url)
        await state.set_state(AddProduct.sizes)
        await message.answer("Введите размеры через запятую (например: 36, 38, 40) или '-' если нет:")
    except Exception as e:
        logging.error(f"Ошибка загрузки фото: {e}")
        await message.answer("❌ Не удалось загрузить фото. Повторите попытку.")

@router.message(AddProduct.photo)
async def photo_invalid(message: Message):
    await message.answer("❌ Отправьте именно фото!")

@router.message(AddProduct.sizes)
async def add_product_sizes(message: Message, state: FSMContext):
    sizes = message.text.strip()
    data = await state.get_data()

    # Проверка обязательных полей
    required = ["name", "price", "category", "photo_url"]
    for key in required:
        if key not in 
            await message.answer("❌ Ошибка: не все данные собраны. Начните заново.")
            logging.error(f"Недостающее поле при сохранении: {key}")
            return

    try:
        from utils.db import save_product
        save_product(
            name=data["name"],
            category=data["category"],
            price=data["price"],
            photo_url=data["photo_url"],
            sizes=sizes
        )
        await message.answer("✅ Товар успешно добавлен!")
    except Exception as e:
        logging.error(f"Ошибка сохранения товара: {e}")
        await message.answer("❌ Не удалось сохранить товар в базу.")
    
    await state.clear()

@router.message(F.text == "🗑 Удалить товар")
async def delete_product_start(message: Message, state: FSMContext):
    if not is_owner(message):
        return
    await state.set_state(DeleteProduct.id)
    await message.answer("Введите ID товара для удаления:")

@router.message(DeleteProduct.id)
async def delete_product_confirm(message: Message, state: FSMContext):
    try:
        pid = int(message.text)
        from utils.db import delete_product, get_product_by_id
        if not get_product_by_id(pid):
            await message.answer("❌ Товар не найден.")
            return
        delete_product(pid)
        await message.answer("✅ Товар удалён!")
    except ValueError:
        await message.answer("❌ Неверный ID. Введите число.")
    await state.clear()

@router.message(F.text == "⬅️ В меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    from keyboards.kb import main_menu
    await message.answer("Главное меню:", reply_markup=main_menu(message.from_user.id))
