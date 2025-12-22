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

# === ЗАКАЗЫ и ПОЛЬЗОВАТЕЛИ — ОПЦИОНАЛЬНО (закомментировано по умолчанию) ===
# Раскомментируй ТОЛЬКО если используешь анонимные заказы или рассылку

# class DeleteOrder(StatesGroup):
#     id = State()

# class Broadcast(StatesGroup):
#     text = State()

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
async def add_product_photo(message: Message, state: FSMContext):
    # Сохраняем ТОЛЬКО file_id из Telegram — безопасно!
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_file_id)
    await state.set_state(AddProduct.sizes)
    await message.answer("Введите размеры через запятую (например: 36, 38, 40) или '-' если нет:")

@router.message(AddProduct.photo)
async def photo_invalid(message: Message):
    await message.answer("❌ Отправьте именно фото!")

@router.message(AddProduct.sizes)
async def add_product_sizes(message: Message, state: FSMContext):
    sizes = message.text.strip()
    if sizes == "-":
        sizes = ""
    else:
        sizes = message.text  # Сохраняем как строку

    data = await state.get_data()
    data["sizes"] = sizes

    try:
        from utils.db import save_product
        # Передаём photo_file_id вместо photo_url
        save_product(
            name=data["name"],
            category=data["category"],
            price=data["price"],
            photo_file_id=data["photo_file_id"],
            sizes=data["sizes"]
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

# === ОПЦИОНАЛЬНЫЕ ФУНКЦИИ (закомментированы для безопасности) ===

# @router.message(F.text == "📋 Заказы")
# async def show_orders(message: Message, state: FSMContext):
#     await state.clear()
#     if not is_owner(message):
#         return
#     try:
#         from utils.db import get_all_orders
#         orders = get_all_orders()
#         if not orders:
#             await message.answer("Нет заказов.")
#             return
#         text = "📋 Последние заказы:\n\n"
#         for o in orders[:20]:
#             order_id = o.get('id', '—')
#             size = o.get('size', '—')
#             # НЕТ username, НЕТ tg_id — только анонимные данные
#             text += f"📦 ID: {order_id} | Размер: {size}\n"
#         text += "\nЧтобы удалить, нажмите «🗑 Удалить заказ» и введите ID."
#         await message.answer(text)
#     except Exception as e:
#         logging.error(f"Ошибка загрузки заказов: {e}")
#         await message.answer("❌ Ошибка при получении заказов.")

# @router.message(F.text == "🗑 Удалить заказ")
# async def delete_order_start(message: Message, state: FSMContext):
#     if not is_owner(message):
#         return
#     await state.set_state(DeleteOrder.id)
#     await message.answer("Введите ID заказа для удаления:")

# @router.message(DeleteOrder.id)
# async def delete_order_confirm(message: Message, state: FSMContext):
#     try:
#         order_id = int(message.text)
#         from utils.db import delete_order, get_order_by_id
#         if not get_order_by_id(order_id):
#             await message.answer("❌ Заказ не найден.")
#             return
#         delete_order(order_id)
#         await message.answer("✅ Заказ удалён!")
#     except ValueError:
#         await message.answer("❌ Неверный ID. Введите число.")
#     await state.clear()

# @router.message(F.text == "👥 Пользователи")
# async def show_users(message: Message, state: FSMContext):
#     await state.clear()
#     if not is_owner(message):
#         return
#     try:
#         from utils.db import get_all_broadcast_users
#         users = get_all_broadcast_users()
#         if not users:
#             await message.answer("Нет пользователей для рассылки.")
#             return
#         text = "👥 Пользователи (только для ручной рассылки):\n\n"
#         for u in users[:20]:
#             text += f"ID: {u['tg_id']} | @{u['username'] or '—'}\n"
#         await message.answer(text)
#     except Exception as e:
#         logging.error(f"Пользователи: {e}")
#         await message.answer("❌ Ошибка загрузки пользователей.")

# @router.message(F.text == "📢 Рассылка")
# async def broadcast_start(message: Message, state: FSMContext):
#     if not is_owner(message):
#         return
#     await state.set_state(Broadcast.text)
#     await message.answer("Введите текст рассылки:")

# @router.message(Broadcast.text)
# async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
#     text = message.text
#     try:
#         from utils.db import get_all_broadcast_users
#         users = get_all_broadcast_users()
#         success = 0
#         for u in users:
#             try:
#                 await bot.send_message(u["tg_id"], text)
#                 success += 1
#             except:
#                 pass
#         await message.answer(f"✅ Рассылка отправлена {success} пользователям.")
#     except Exception as e:
#         logging.error(f"Рассылка: {e}")
#         await message.answer("❌ Ошибка рассылки.")
#     await state.clear()
