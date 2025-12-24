import os
import base64
import logging
from supabase import create_client
import httpx

logging.basicConfig(level=logging.INFO)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def safe_execute(func, default=None):
    try:
        return func()
    except Exception as e:
        logging.error(f"Supabase error: {e}")
        return default

# === ЗАГРУЗКА ФОТО НА IMGBB ===
async def upload_to_imgbb(bot, file_id: str) -> str:
    try:
        file = await bot.get_file(file_id)
        photo_io = await bot.download_file(file.file_path)
        photo_bytes = photo_io.read()
        encoded = base64.b64encode(photo_bytes).decode('utf-8')
        
        imgbb_key = os.getenv("IMGBB_KEY")
        if not imgbb_key:
            logging.warning("IMGBB_KEY не установлен. Используется Telegram file_id.")
            return f"tg://{file_id}"
        
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
        return f"tg://{file_id}"

# === ТОВАРЫ ===
def get_categories():
    data = safe_execute(
        lambda: supabase.table("products").select("category").execute().data,
        []
    )
    return sorted(set(item["category"] for item in data)) if data else []

def get_products_by_category(category: str):
    return safe_execute(
        lambda: supabase.table("products").select("*").eq("category", category).execute().data,
        []
    )

def get_product_by_id(product_id: int):
    data = safe_execute(
        lambda: supabase.table("products").select("*").eq("id", product_id).execute().data,
        []
    )
    return data[0] if data else None

def save_product(name: str, category: str, price: int, photo_url: str, sizes: str = ""):
    logging.info(f"Сохраняю товар: {name} | Категория: {category} | Фото: {photo_url}")
    safe_execute(
        lambda: supabase.table("products").insert({
            "name": name,
            "category": category,
            "price": price,
            "photo_url": photo_url,
            "sizes": sizes
        }).execute()
    )

def delete_product(product_id: int):
    safe_execute(
        lambda: supabase.table("products").delete().eq("id", product_id).execute()
    )
