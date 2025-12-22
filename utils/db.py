import os
import logging
from supabase import create_client

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Подключение к Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def safe_execute(func, default=None):
    try:
        return func()
    except Exception as e:
        logging.error(f"Supabase error: {e}")
        return default

# ========================
# ПОЛЬЗОВАТЕЛИ (только для рассылки админом — НЕ для хранения ПДн)
# ВНИМАНИЕ: если не используешь рассылку — можешь удалить эти функции
# ========================

def add_user_for_broadcast(tg_id: int, username: str = None):
    """
    Добавляет пользователя ТОЛЬКО для ручной рассылки админом.
    НЕ используется для идентификации, подписок или заказов.
    """
    safe_execute(lambda: supabase.table("broadcast_users").upsert({
        "tg_id": tg_id,
        "username": username
    }).execute())

def get_all_broadcast_users():
    """Получает список для рассылки (только если админ использует команду /send)"""
    return safe_execute(
        lambda: supabase.table("broadcast_users")
        .select("tg_id, username")
        .execute()
        .data,
        []
    )

# ========================
# ТОВАРЫ — ОСНОВНАЯ ЧАСТЬ
# ========================

def get_categories():
    """Получить уникальные категории товаров"""
    data = safe_execute(
        lambda: supabase.table("products")
        .select("category")
        .execute()
        .data,
        []
    )
    return sorted(set(item["category"] for item in data)) if data else []

def get_products_by_category(category: str):
    """Получить все товары в категории"""
    return safe_execute(
        lambda: supabase.table("products")
        .select("*")
        .eq("category", category)
        .execute()
        .data,
        []
    )

def get_product_by_id(product_id: int):
    """Получить товар по ID"""
    data = safe_execute(
        lambda: supabase.table("products")
        .select("*")
        .eq("id", product_id)
        .execute()
        .data,
        []
    )
    return data[0] if data else None

def save_product(name: str, category: str, price: int, photo_file_id: str, sizes: str = ""):
    """
    Сохраняет товар.
    Фото хранится как file_id из Telegram → безопасно, без внешних сервисов.
    """
    safe_execute(
        lambda: supabase.table("products")
        .insert({
            "name": name,
            "category": category,
            "price": price,
            "photo_file_id": photo_file_id,  # ← именно file_id, не URL
            "sizes": sizes
        })
        .execute()
    )

def update_product(product_id: int, name: str, category: str, price: int, photo_file_id: str, sizes: str = ""):
    """Обновить товар"""
    safe_execute(
        lambda: supabase.table("products")
        .update({
            "name": name,
            "category": category,
            "price": price,
            "photo_file_id": photo_file_id,
            "sizes": sizes
        })
        .eq("id", product_id)
        .execute()
    )

def delete_product(product_id: int):
    """Удалить товар по ID"""
    safe_execute(
        lambda: supabase.table("products")
        .delete()
        .eq("id", product_id)
        .execute()
    )

# ========================
# ЗАКАЗЫ — НЕ ХРАНЯТСЯ!
# ========================
# В этой версии заказы НЕ сохраняются в базу.
# Все сообщения пересылаются владельцу напрямую.
# Поэтому функции ниже ЗАКОММЕНЧЕНЫ.
# Раскомментируй ТОЛЬКО если позже захочешь добавить заказы БЕЗ ПДн (например, только product_id + размер)

"""
def save_order(product_id: int, size: str, raw_message: str):
    '''
    Пример безопасного хранения заказа БЕЗ ПДн:
    - Нет tg_id, нет username
    - Только анонимный заказ
    '''
    safe_execute(
        lambda: supabase.table("orders")
        .insert({
            "product_id": product_id,
            "size": size,
            "raw_message": raw_message  # например: "5 L"
        })
        .execute()
    )

def get_all_orders():
    return safe_execute(
        lambda: supabase.table("orders")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data,
        []
    )

def delete_order(order_id: int):
    safe_execute(
        lambda: supabase.table("orders")
        .delete()
        .eq("id", order_id)
        .execute()
    )
"""
