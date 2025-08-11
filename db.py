import os
from supabase import create_client, Client

# Initialize Supabase client
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

def get_user_by_telegram_id(telegram_id):
    """Fetch a user from the database by their Telegram ID."""
    try:
        response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        data = response.data
        if data:
            return data[0]
        return None
    except Exception as e:
        print(f"DB Error (get_user_by_telegram_id): {e}")
        return None

def add_user(telegram_id, phone_number, social_card):
    """Insert a new user into the database and return the new user ID."""
    try:
        res = supabase.table("users").insert({
            "telegram_id": telegram_id,
            "phone_number": phone_number,
            "social_card": social_card
        }).execute()
        data = res.data
        if data:
            user_id = data[0].get("id")
            return user_id
    except Exception as e:
        print(f"DB Error (add_user): {e}")
    return None

def add_search(user_id, exam_type, branch, filter_type, filter_value):
    """Insert a new search record into the database."""
    try:
        supabase.table("searches").insert({
            "user_id": user_id,
            "exam_type": exam_type,
            "branch": branch,
            "filter_type": filter_type,
            "filter_value": filter_value,
            # "timestamp": ... # If needed, can be set by DB default
        }).execute()
    except Exception as e:
        print(f"DB Error (add_search): {e}")
