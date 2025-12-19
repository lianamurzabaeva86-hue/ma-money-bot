import os
from supabase import create_client
import logging

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def safe_execute(func, default=None):
    try:
        return func()
    except Exception as e:
        logging.error(f"Supabase error: {e}")
        return default

# Пользователи
def add_user(tg_id, username):
    safe_execute(lambda: supabase.table("users").upsert({"tg_id": tg_id, "username": username}).execute())

def get_all_users():
    return safe_execute(lambda: supabase.table("users").select("tg_id,username").execute().data, [])

# Товары
def get_categories():
    data = safe_execute(lambda: supabase.table("products").select("category").execute().data, [])
    return sorted(set(item["category"] for item in data)) if data else []

def get_products_by_category(cat):
    return safe_execute(lambda: supabase.table("products").select("*").eq("category", cat).execute().data, [])

def get_product_by_id(pid):
    data = safe_execute(lambda: supabase.table("products").select("*").eq("id", pid).execute().data, [])
    return data[0] if data else None

def add_product(name, cat, price, photo, sizes):
    safe_execute(lambda: supabase.table("products").insert({
        "name": name, "category": cat, "price": price, "photo_url": photo, "sizes": sizes
    }).execute())

def delete_product(pid):
    safe_execute(lambda: supabase.table("products").delete().eq("id", pid).execute())

# Заказы
def save_order(uid, uname, pid, size):
    safe_execute(lambda: supabase.table("orders").insert({
        "user_id": uid, "username": uname, "product_id": pid, "size": size
    }).execute())

def get_all_orders():
    return safe_execute(lambda: supabase.table("orders").select("*").order("created_at", desc=True).execute().data, [])