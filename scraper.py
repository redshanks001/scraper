import requests
import json
import time
from datetime import datetime
from supabase import create_client

# 🔹 Supabase credentials
SUPABASE_URL = "https://cbdkiyruretigoldouhf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNiZGtpeXJ1cmV0aWdvbGRvdWhmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczODU2NDc5OSwiZXhwIjoyMDU0MTQwNzk5fQ.NqeVS9WSjeGYjAM52XRXOS_FTjgE8uyTM4yDmkqSy5I"  # Replace with your secret key

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔹 MangaDex API
BASE_URL = "https://api.mangadex.org"
RATE_LIMIT_DELAY = 5  # Prevent rate limits
BATCH_SIZE = 25  # Process in chunks
MAX_MANGA_PER_RUN = 1000  # Limit the number of manga per run
CACHE_FILE = "manga_cache.json"

# ✅ Load Cache
def load_cache():
    """Load manga cache from a JSON file."""
    try:
        with open(CACHE_FILE, "r") as f:
            cache_data = json.load(f)
            if isinstance(cache_data, list):  # Handle empty list case
                return {"last_fetched_manga": []}
            return cache_data
    except FileNotFoundError:
        return {"last_fetched_manga": []}

# ✅ Save Cache
def save_cache(manga_ids):
    """Save fetched manga IDs to cache."""
    cache_data = {"last_fetched_manga": manga_ids}
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f)

# ✅ Fetch Existing Manga IDs from Supabase
def fetch_existing_manga_ids():
    """Fetch existing manga IDs from Supabase to avoid duplicates."""
    response = supabase.table("manga_columns_only").select("id").execute()
    if response and response.data:
        return {entry["id"] for entry in response.data}
    return set()

# ✅ Fetch Manga List from MangaDex
def fetch_all_manga():
    """Fetch all manga IDs and exclude cached & existing Supabase IDs."""
    url = f"{BASE_URL}/manga?limit=100&order[updatedAt]=desc"
    manga_list = []

    cache_data = load_cache()
    cached_manga_ids = set(cache_data.get("last_fetched_manga", []))
    existing_manga_ids = fetch_existing_manga_ids()

    while url and len(manga_list) < MAX_MANGA_PER_RUN:
        response = requests.get(url)
        if response.status_code != 200:
            print("❌ Failed to fetch manga list")
            break

        data = response.json()
        new_ids = {manga["id"] for manga in data.get("data", [])}

        # Exclude manga already in Supabase and cache
        fresh_ids = new_ids - cached_manga_ids - existing_manga_ids
        manga_list.extend(fresh_ids)

        url = data.get("links", {}).get("next")
        time.sleep(RATE_LIMIT_DELAY)

    return manga_list[:MAX_MANGA_PER_RUN]

# ✅ Fetch Manga Details
def fetch_manga_details(manga_id):
    """Fetch manga details including title, author, cover, and chapters."""
    url = f"{BASE_URL}/manga/{manga_id}?includes[]=cover_art&includes[]=author&includes[]=artist"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ Failed to fetch manga data for {manga_id}")
        return None

    data = response.json().get("data", {})
    attributes = data.get("attributes", {})

    title = attributes.get("title", {}).get("en", "Unknown")
    alternative_titles = attributes.get("altTitles", [])
    description = attributes.get("description", {}).get("en", "No description available")
    year = attributes.get("year")
    status = attributes.get("status", "Unknown").capitalize()
    tags = [tag["attributes"]["name"].get("en", "Unknown") for tag in attributes.get("tags", [])]

    authors = [rel["attributes"]["name"] for rel in data.get("relationships", []) if rel["type"] == "author"]
    artists = [rel["attributes"]["name"] for rel in data.get("relationships", []) if rel["type"] == "artist"]

    cover = next((rel for rel in data.get("relationships", []) if rel["type"] == "cover_art"), {})
    cover_url = f"https://uploads.mangadex.org/covers/{manga_id}/{cover.get('attributes', {}).get('fileName', '')}"

    read_link = f"https://mangadex.org/title/{manga_id}"
    buy_link = f"https://www.amazon.com/s?k={title.replace(' ', '+')}+manga"

    manga_data = {
        "id": manga_id,
        "title": title,
        "alternative_titles": alternative_titles,
        "description": description,
        "year": year,
        "status": status,
        "tags": tags,
        "authors": authors,
        "artists": artists,
        "cover_url": cover_url,
        "read_link": read_link,
        "buy_link": buy_link,
        "created_at": datetime.utcnow().isoformat()
    }

    time.sleep(RATE_LIMIT_DELAY)
    return manga_data

# ✅ Insert Data into Supabase
def insert_into_supabase(manga_data, existing_manga_ids):
    """Insert manga details into Supabase, skipping existing ones."""
    if manga_data["id"] in existing_manga_ids:
        print(f"⏭️ Skipping existing manga: {manga_data['title']}")
        return

    response = supabase.table("manga_columns_only").upsert(manga_data).execute()
    print(f"✅ Inserted/Updated in Supabase: {manga_data['title']}")

    existing_manga_ids.add(manga_data["id"])
    time.sleep(5)

# ✅ Main Function
def main():
    existing_manga_ids = fetch_existing_manga_ids()
    manga_ids = fetch_all_manga()

    for i in range(0, len(manga_ids), BATCH_SIZE):
        batch = manga_ids[i:i + BATCH_SIZE]
        for manga_id in batch:
            if manga_id in existing_manga_ids:
                print(f"⏭️ Skipping existing manga: {manga_id}")
                continue

            manga_data = fetch_manga_details(manga_id)
            if manga_data:
                insert_into_supabase(manga_data, existing_manga_ids)

        save_cache(manga_ids)
        time.sleep(120)

if __name__ == "__main__":
    main()
