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

def fetch_manga_from_supabase():
    """Fetch all manga from Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()  # List of manga
    else:
        print("❌ Failed to fetch manga from Supabase!")
        return []

def update_manga_cache():
    cache_file = "manga_cache.json"

    # Load existing cache
    try:
        with open(cache_file, "r") as f:
            cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}  # Initialize empty dictionary if the file is missing

    # Fetch manga from Supabase
    manga_list = fetch_manga_from_supabase()

    # Check for new manga
    new_manga_added = False
    for manga in manga_list:
        manga_id = str(manga["id"])  # Ensure ID is stored as a string
        title = manga["title"]
        last_chapter = manga.get("last_chapter", "Unknown")

        if manga_id not in cache:  # New manga found!
            print(f"🆕 New manga detected: {title} (ID: {manga_id})")
            cache[manga_id] = {
                "title": title,
                "last_chapter": last_chapter
            }
            new_manga_added = True

    # Save updated cache if new manga were added
    if new_manga_added:
        with open(cache_file, "w") as f:
            json.dump(cache, f, indent=4)
        print("✅ manga_cache.json updated!")

# Run the function to check for new manga and update the cache
update_manga_cache()
