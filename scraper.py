import requests
import json
import time
from datetime import datetime
from supabase import create_client

# Supabase credentials
SUPABASE_URL = "https://cbdkiyruretigoldouhf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNiZGtpeXJ1cmV0aWdvbGRvdWhmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczODU2NDc5OSwiZXhwIjoyMDU0MTQwNzk5fQ.NqeVS9WSjeGYjAM52XRXOS_FTjgE8uyTM4yDmkqSy5I"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://api.mangadex.org"
RATE_LIMIT_DELAY = 5  # To prevent getting banned
BATCH_SIZE = 25  # To reduce load
MAX_MANGA_PER_RUN = 250  # Limits total manga fetched per run

def fetch_existing_manga_ids():
    """Fetch existing manga IDs from Supabase to avoid duplicates."""
    response = supabase.table("new_manga").select("id").execute()
    if response.data:
        return {entry["id"] for entry in response.data}
    return set()

def fetch_all_manga():
    """Fetch all manga IDs with pagination."""
    url = f"{BASE_URL}/manga?limit=100"
    manga_list = []
    while url and len(manga_list) < MAX_MANGA_PER_RUN:
        response = requests.get(url)
        if response.status_code != 200:
            print("Failed to fetch manga list")
            break
        data = response.json()
        manga_list.extend([manga["id"] for manga in data.get("data", [])])
        url = data.get("links", {}).get("next")
        time.sleep(RATE_LIMIT_DELAY)
    return manga_list[:MAX_MANGA_PER_RUN]

def fetch_manga_details(manga_id):
    """Fetch manga details including title, author, cover, and chapters."""
    url = f"{BASE_URL}/manga/{manga_id}?includes[]=cover_art&includes[]=author&includes[]=artist"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch manga data for {manga_id}")
        return None
    
    data = response.json().get("data", {})
    attributes = data.get("attributes", {})
    title = attributes.get("title", {}).get("en", "Unknown")
    description = attributes.get("description", {}).get("en", "No description available")
    
    manga_data = {
        "id": manga_id,
        "title": title,
        "description": description,
        "created_at": datetime.utcnow().isoformat()
    }
    
    time.sleep(RATE_LIMIT_DELAY)
    return manga_data

def insert_into_supabase(manga_data):
    """Insert manga details into Supabase only if not exists."""
    existing_ids = fetch_existing_manga_ids()
    if manga_data["id"] in existing_ids:
        print(f"Skipping existing manga ID: {manga_data['id']}")
        return
    
    response = supabase.table("new_manga").insert(manga_data).execute()
    print(f"Inserted into Supabase: {response}")
    time.sleep(RATE_LIMIT_DELAY)

def main():
    existing_manga_ids = fetch_existing_manga_ids()
    manga_ids = fetch_all_manga()
    new_manga_ids = [m_id for m_id in manga_ids if m_id not in existing_manga_ids]
    
    for i in range(0, len(new_manga_ids), BATCH_SIZE):
        batch = new_manga_ids[i:i + BATCH_SIZE]
        for manga_id in batch:
            manga_data = fetch_manga_details(manga_id)
            if manga_data:
                insert_into_supabase(manga_data)
        time.sleep(120)  # Longer pause after processing a batch

if __name__ == "__main__":
    main()
