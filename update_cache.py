import json
import requests

# 🔹 Replace with your actual Supabase credentials
SUPABASE_URL = "https://cbdkiyruretigoldouhf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNiZGtpeXJ1cmV0aWdvbGRvdWhmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczODU2NDc5OSwiZXhwIjoyMDU0MTQwNzk5fQ.NqeVS9WSjeGYjAM52XRXOS_FTjgE8uyTM4yDmkqSy5I"
SUPABASE_TABLE = "manga"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def fetch_manga_ids_from_supabase():
    """Fetch only manga IDs from Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?select=id"  # Fetch only 'id'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return [manga["id"] for manga in response.json()]  # Extract only IDs
    else:
        print("❌ Failed to fetch manga IDs from Supabase!")
        return []

def update_manga_cache():
    cache_file = "manga_cache.json"

    # Load existing cache (as a list)
    try:
        with open(cache_file, "r") as f:
            cache = json.load(f)
        
        # Ensure cache is a list, not a dictionary
        if not isinstance(cache, list):
            cache = []
    except (FileNotFoundError, json.JSONDecodeError):
        cache = []  # Initialize empty list if the file is missing

    # Fetch manga IDs from Supabase
    manga_ids = fetch_manga_ids_from_supabase()

    # Check for new IDs
    new_ids = [manga_id for manga_id in manga_ids if manga_id not in cache]

    if new_ids:
        print(f"🆕 New manga IDs detected: {new_ids}")
        cache.extend(new_ids)  # Append new IDs

        # Save updated cache
        with open(cache_file, "w") as f:
            json.dump(cache, f, indent=4)
        print("✅ manga_cache.json updated!")

# Run the function to check for new manga IDs and update the cache
update_manga_cache()
