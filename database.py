# database.py
from config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client, Client

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user(user_id: int):
    """Retrieve user record by Telegram user ID."""
    res = supabase.table("users").select("*").eq("id", user_id).execute()
    data = res.data
    if data:
        return data[0]
    return None

def create_user(user_id: int, phone: str, social: str, email: str = None, cookies: dict = None):
    """Insert a new user record."""
    user_data = {
        "id": user_id,
        "phone": phone,
        "social": social,
        "email": email if email else None,
        "cookies": cookies if cookies else None
    }
    supabase.table("users").insert(user_data).execute()
    return user_data

def update_user(user_id: int, update_fields: dict):
    """Update existing user record with given fields."""
    supabase.table("users").update(update_fields).eq("id", user_id).execute()
