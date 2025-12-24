from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

OWNER_ID = 6782041245

def main_menu(user_id: int):
    """Показывает админку только владельцу"""
    keyboard = [[KeyboardButton(text="📦 Каталог")]]
    if user_id == OWNER_ID:
        keyboard.append([KeyboardButton(text="👑 Админка")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def categories_kb(categories):
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
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад к категориям")]],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить товар")],
            [KeyboardButton(text="🗑 Удалить товар")],
            [KeyboardButton(text="⬅️ В меню")]
        ],
        resize_keyboard=True
    )
