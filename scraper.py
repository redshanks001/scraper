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
    response = supabase.table("manga").select("id").execute()
    
    if response.data and isinstance(response.data, list):  # Ensure response is valid
        return {entry["id"] for entry in response.data}  # Convert to a set for quick lookup
    else:
        print("⚠️ Warning: Failed to fetch existing manga IDs from Supabase!")
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
    
    # Extract main details
    title = attributes.get("title", {}).get("en", "Unknown")
    alternative_titles = attributes.get("altTitles", [])
    description = attributes.get("description", {}).get("en", "No description available")
    year = attributes.get("year")
    status = attributes.get("status", "Unknown").capitalize()
    tags = [tag["attributes"]["name"].get("en", "Unknown") for tag in attributes.get("tags", [])]
    
    # Extract relationships
    authors = [rel["attributes"]["name"] for rel in data.get("relationships", []) if rel["type"] == "author"]
    artists = [rel["attributes"]["name"] for rel in data.get("relationships", []) if rel["type"] == "artist"]
    
    # Extract cover image
    cover = next((rel for rel in data.get("relationships", []) if rel["type"] == "cover_art"), {})
    cover_url = f"https://uploads.mangadex.org/covers/{manga_id}/{cover.get('attributes', {}).get('fileName', '')}"
    
    # Add read and buy links
    read_link = f"https://mangadex.org/title/{manga_id}"
    buy_link = f"https://www.amazon.com/s?k={title.replace(' ', '+')}+manga"
    
    # Construct manga data
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
    
    time.sleep(RATE_LIMIT_DELAY)  # Prevent rate limiting
    return manga_data

def insert_into_supabase(manga_data, existing_manga_ids):
    """Insert manga details into Supabase, skipping existing ones."""
    manga_id = manga_data["id"]

    if manga_id in existing_manga_ids:
        print(f"✅ Skipping existing manga: {manga_data['title']} ({manga_id})")
        return  # Skip existing manga
    
    try:
        response = supabase.table("manga").insert(manga_data).execute()
        print(f"✅ Inserted into Supabase: {manga_data['title']} ({manga_id})")
        time.sleep(RATE_LIMIT_DELAY)
    except Exception as e:
        print(f"⚠️ Error inserting {manga_id}: {e}")


def main():
    existing_manga_ids = fetch_existing_manga_ids()
    manga_ids = fetch_all_manga()
    new_manga_ids = [m_id for m_id in manga_ids if m_id not in existing_manga_ids]

    for i in range(0, len(new_manga_ids), BATCH_SIZE):
        batch = new_manga_ids[i:i + BATCH_SIZE]
        for manga_id in batch:
            manga_data = fetch_manga_details(manga_id)
            if manga_data:
                insert_into_supabase(manga_data, existing_manga_ids)
        time.sleep(120)  # Longer pause after processing a batch

if __name__ == "__main__":
    main()
