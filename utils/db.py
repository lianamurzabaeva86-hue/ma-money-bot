import os
import io
import base64
import logging
from supabase import create_client
import httpx

# Инициализация Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def safe_execute(func, default=None):
    try:
        return func()
    except Exception as e:
        logging.error(f"Supabase error: {e}")
        return default

async def upload_to_imgbb(bot, file_id: str) -> str:
    """
    Загружает фото из Telegram в ImgBB и возвращает публичную ссылку.
    Если IMGBB_KEY не задан — возвращает Telegram file_id как fallback.
    """
    try:
        # Получаем информацию о файле
        file = await bot.get_file(file_id)
        # Скачиваем как BytesIO
        photo_io = await bot.download_file(file.file_path)
        # Преобразуем в bytes (обязательно!)
        photo_bytes = photo_io.read()
        
        # Кодируем в base64
        encoded = base64.b64encode(photo_bytes).decode('utf-8')
        
        # Проверяем ключ
        imgbb_key = os.getenv("IMGBB_KEY")
        if not imgbb_key:
            logging.warning("IMGBB_KEY не установлен. Используется Telegram file_id.")
            return f"tg://{file_id}"
        
        # Отправляем в ImgBB
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.imgbb.com/1/upload",
                data={
                    "key": imgbb_key,
                    "image": encoded,
                    "name": f"product_{file_id}"
                }
            )
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data["data"]["url"]
            else:
                error_msg = data.get("error", {}).get("message", "Неизвестная ошибка ImgBB")
                raise Exception(f"ImgBB API error: {error_msg}")
                
    except Exception as e:
        logging.error(f"Ошибка загрузки в ImgBB: {e}")
        # Всегда возвращаем fallback
        return f"tg://{file_id}"

# === Пользователи ===
def add_user(tg_id, username):
    safe_execute(lambda: supabase.table("users").upsert({
        "tg_id": tg_id,
        "username": username
    }).execute())

def get_all_users():
    return safe_execute(lambda: supabase.table("users").select("tg_id,username").execute().data, [])

# === Товары ===
def get_categories():
    data = safe_execute(lambda: supabase.table("products").select("category").execute().data, [])
    return sorted(set(item["category"] for item in data)) if data else []

def get_products_by_category(cat):
    return safe_execute(lambda: supabase.table("products").select("*").eq("category", cat).execute().data, [])

def get_product_by_id(pid):
    data = safe_execute(lambda: supabase.table("products").select("*").eq("id", pid).execute().data, [])
    return data[0] if data else None

def save_product(data):
    """
    Сохраняет товар в базу.
    Ожидает словарь с ключами: name, category, price, photo_url, sizes
    """
    safe_execute(lambda: supabase.table("products").insert({
        "name": data["name"],
        "category": data["category"],
        "price": data["price"],
        "photo_url": data["photo_url"],
        "sizes": data["sizes"]
    }).execute())

def delete_product(pid):
    safe_execute(lambda: supabase.table("products").delete().eq("id", pid).execute())

# === Заказы ===
def save_order(uid, uname, pid, size):
    safe_execute(lambda: supabase.table("orders").insert({
        "user_id": uid,
        "username": uname,
        "product_id": pid,
        "size": size
    }).execute())

def get_all_orders():
    return safe_execute(lambda: supabase.table("orders").select("*").order("created_at", desc=True).execute().data, [])
