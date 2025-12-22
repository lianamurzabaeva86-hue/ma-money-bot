from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

OWNER_ID = 6782041245

def main_menu():
    """
    Главное меню — кнопка 'Админка' видна всем, 
    но доступ к ней ограничен на уровне handlers (is_owner).
    Это безопасно и не требует передачи user_id.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Каталог")],
            [KeyboardButton(text="👑 Админка")]  # Доступ проверяется в admin.py
        ],
        resize_keyboard=True
    )

def categories_kb(categories):
    """Клавиатура с категориями (до 2 в строке)"""
    if not categories:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⬅️ Назад")]],
            resize_keyboard=True
        )
    kb = []
    for i in range(0, len(categories), 2):
        row = [KeyboardButton(text=f"👗 {categories[i]}")]
        if i + 1 < len(categories):
            row.append(KeyboardButton(text=f"👗 {categories[i+1]}"))
        kb.append(row)
    kb.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def product_kb():
    """Кнопка назад после показа товаров"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад к категориям")]],
        resize_keyboard=True
    )

def admin_menu():
    """
    Админ-меню.
    Опционально: если не используешь заказы/пользователей/рассылку — 
    можно убрать соответствующие кнопки.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить товар")],
            [KeyboardButton(text="🗑 Удалить товар")],
            # === Опциональные пункты (раскомментируй при необходимости) ===
            # [KeyboardButton(text="📋 Заказы")],
            # [KeyboardButton(text="🗑 Удалить заказ")],
            # [KeyboardButton(text="👥 Пользователи")],
            # [KeyboardButton(text="📢 Рассылка")],
            [KeyboardButton(text="⬅️ В меню")]
        ],
        resize_keyboard=True
    )
