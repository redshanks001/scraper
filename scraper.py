import requests
import json
import time
from datetime import datetime
from supabase import create_client

# 🔹 Load config from JSON
with open("config.json", "r") as config_file:
    config = json.load(config_file)

SUPABASE_URL = config["SUPABASE_URL"]
SUPABASE_KEY = config["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔹 MangaDex API
BASE_URL = "https://api.mangadex.org"
RATE_LIMIT_DELAY = 5
BATCH_SIZE = 25
MAX_MANGA_PER_RUN = 1000

def fetch_existing_manga_ids():
    """Fetch existing manga IDs from Supabase."""
    response = supabase.table("manga").select("id").execute()
    return {entry["id"] for entry in response.data} if response and response.data else set()

def fetch_all_manga():
    """Fetch all manga IDs with pagination."""
    url = f"{BASE_URL}/manga?limit=100&order[updatedAt]=desc"
    manga_list = []
    
    while url and len(manga_list) < MAX_MANGA_PER_RUN:
        response = requests.get(url)
        if response.status_code != 200:
            print("❌ Failed to fetch manga list")
            break
        
        data = response.json()
        manga_list.extend([manga["id"] for manga in data.get("data", [])])
        url = data.get("links", {}).get("next")
        
        if url:
            time.sleep(RATE_LIMIT_DELAY)
    
    return manga_list[:MAX_MANGA_PER_RUN]

def fetch_all_chapters(manga_id):
    """Fetch all available chapters (English only)."""
    chapters = []
    url = f"{BASE_URL}/manga/{manga_id}/feed?order[chapter]=asc&limit=100"
    
    while url:
        response = requests.get(url)
        if response.status_code != 200:
            break
        
        data = response.json()
        for chap in data.get("data", []):
            chap_attr = chap.get("attributes", {})
            if chap_attr.get("translatedLanguage") == "en":
                chapters.append({
                    "chapter_number": chap_attr.get("chapter", "Unknown"),
                    "title": chap_attr.get("title", "Untitled"),
                    "release_date": chap_attr.get("createdAt", "Unknown")
                })

        url = data.get("links", {}).get("next")
        time.sleep(RATE_LIMIT_DELAY)
    
    return chapters

def fetch_manga_details(manga_id):
    """Fetch manga details including title, author, cover, and chapters."""
    url = f"{BASE_URL}/manga/{manga_id}?includes[]=cover_art&includes[]=author&includes[]=artist"
    response = requests.get(url)
    if response.status_code != 200:
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
    
    chapters = fetch_all_chapters(manga_id)
    
    read_link = f"https://mangadex.org/title/{manga_id}"
    buy_link = f"https://www.amazon.com/s?k={title.replace(' ', '+')}+manga"
    
    return {
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

def insert_into_supabase(manga_data, existing_manga_ids):
    """Insert manga details into Supabase."""
    if manga_data["id"] in existing_manga_ids:
        return
    
    response = supabase.table("manga").upsert(manga_data).execute()
    print(f"✅ Inserted/Updated: {manga_data['title']}")
    existing_manga_ids.add(manga_data["id"])
    time.sleep(5)

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
        time.sleep(120)

if __name__ == "__main__":
    main()
