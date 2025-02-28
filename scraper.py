import requests
import json
import time
from datetime import datetime
from supabase import create_client

# 🔹 Supabase credentials
SUPABASE_URL = "https://cbdkiyruretigoldouhf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNiZGtpeXJ1cmV0aWdvbGRvdWhmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczODU2NDc5OSwiZXhwIjoyMDU0MTQwNzk5fQ.NqeVS9WSjeGYjAM52XRXOS_FTjgE8uyTM4yDmkqSy5I"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔹 MangaDex API
BASE_URL = "https://api.mangadex.org"
RATE_LIMIT_DELAY = 5  # Prevent rate limits
BATCH_SIZE = 25  # Reduce load
MAX_MANGA_PER_RUN = 1000  # Fetch more manga per run

def fetch_existing_manga_ids():
    """Fetch existing manga IDs from Supabase to avoid duplicates."""
    response = supabase.table("manga").select("id").execute()
    if response and response.data:
        return {entry["id"] for entry in response.data}
    return set()

def fetch_all_manga():
    """Fetch all manga IDs with pagination."""
    url = f"{BASE_URL}/manga?limit=100&order[updatedAt]=desc"  # Fetch updated manga
    manga_list = []
    
    while url and len(manga_list) < MAX_MANGA_PER_RUN:
        response = requests.get(url)
        if response.status_code != 200:
            print("❌ Failed to fetch manga list")
            break
        
        data = response.json()
        manga_list.extend([manga["id"] for manga in data.get("data", [])])
        
        # Get next page link
        url = data.get("links", {}).get("next")
        if url:
            print(f"🔄 Fetching next page: {url}")  # Debugging
            time.sleep(RATE_LIMIT_DELAY)  # Prevent rate limiting
        else:
            print("✅ No more pages left to fetch.")
    
    return manga_list[:MAX_MANGA_PER_RUN]  # Limit total fetched manga

def fetch_all_chapters(manga_id):
    """Fetch all available chapters with pagination."""
    chapters = []
    url = f"{BASE_URL}/manga/{manga_id}/feed?order[chapter]=asc&limit=100"
    
    while url:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"❌ Failed to fetch chapters for {manga_id}")
            break
        
        data = response.json()
        for chap in data.get("data", []):
            chap_attr = chap.get("attributes", {})
            chapter_title = chap_attr.get("title", "Untitled")  # Default title
            translated_lang = chap_attr.get("translatedLanguage", "")

            if translated_lang == "en":  # Fetch only English chapters
                chapters.append({
                    "chapter_number": chap_attr.get("chapter", "Unknown"),
                    "title": chapter_title,
                    "release_date": chap_attr.get("createdAt", "Unknown")
                })

        url = data.get("links", {}).get("next")  # Get next page link
        time.sleep(RATE_LIMIT_DELAY)  # Prevent rate limit bans
    
    return chapters

def fetch_manga_details(manga_id):
    """Fetch manga details including title, author, cover, and chapters."""
    url = f"{BASE_URL}/manga/{manga_id}?includes[]=cover_art&includes[]=author&includes[]=artist"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ Failed to fetch manga data for {manga_id}")
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
    
    # Fetch all chapters
    chapters = fetch_all_chapters(manga_id)
    
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
        "chapters": chapters,
        "read_link": read_link,
        "buy_link": buy_link,
        "created_at": datetime.utcnow().isoformat()
    }
    
    time.sleep(RATE_LIMIT_DELAY)  # Prevent rate limiting
    return manga_data

def insert_into_supabase(manga_data, existing_manga_ids):
    """Insert manga details into Supabase, skipping existing ones."""
    if manga_data["id"] in existing_manga_ids:
        print(f"⏭️ Skipping existing manga: {manga_data['title']}")
        return
    
    response = supabase.table("manga").insert(manga_data).execute()
    print(f"✅ Inserted into Supabase: {manga_data['title']}")
    time.sleep(RATE_LIMIT_DELAY)  # Prevent rate limiting

def main():
    existing_manga_ids = fetch_existing_manga_ids()
    manga_ids = fetch_all_manga()
    new_manga_ids = [m_id for m_id in manga_ids if m_id not in existing_manga_ids]  # Skip existing manga
    
    for i in range(0, len(new_manga_ids), BATCH_SIZE):
        batch = new_manga_ids[i:i + BATCH_SIZE]
        for manga_id in batch:
            manga_data = fetch_manga_details(manga_id)
            if manga_data:
                insert_into_supabase(manga_data, existing_manga_ids)
        time.sleep(120)  # Longer pause after processing a batch

if __name__ == "__main__":
    main()
