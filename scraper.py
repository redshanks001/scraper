
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
RATE_LIMIT_DELAY = 2  # Add delay between requests to prevent bans
BATCH_SIZE = 50  # Process manga in batches to avoid hitting GitHub Actions limits

def fetch_existing_manga_ids():
    """Fetch existing manga IDs from Supabase to avoid duplicates."""
    response = supabase.table("manga").select("id").execute()
    if response and response.data:
        return {entry["id"] for entry in response.data}
    return set()

def fetch_all_manga():
    url = f"{BASE_URL}/manga?limit=100"
    manga_list = []
    while url:
        response = requests.get(url)
        if response.status_code != 200:
            print("Failed to fetch manga list")
            break
        data = response.json()
        manga_list.extend([manga["id"] for manga in data.get("data", [])])
        url = data.get("links", {}).get("next")
        time.sleep(RATE_LIMIT_DELAY)  # Prevent rate limiting
    return manga_list

def fetch_manga_details(manga_id):
    url = f"{BASE_URL}/manga/{manga_id}?includes[]=cover_art&includes[]=author&includes[]=artist&includes[]=publisher"
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
    tags = [tag["attributes"]["name"]["en"] for tag in attributes.get("tags", [])]
    
    # Extract relationships
    authors = [rel["attributes"]["name"] for rel in data.get("relationships", []) if rel["type"] == "author"]
    artists = [rel["attributes"]["name"] for rel in data.get("relationships", []) if rel["type"] == "artist"]
    publishers = [rel["attributes"]["name"] for rel in data.get("relationships", []) if rel["type"] == "publisher"]
    
    # Extract cover image
    cover = next((rel for rel in data.get("relationships", []) if rel["type"] == "cover_art"), {})
    cover_url = f"https://uploads.mangadex.org/covers/{manga_id}/{cover.get('attributes', {}).get('fileName', '')}"

    # Fetch stats (rating, follows, views)
    stats_url = f"{BASE_URL}/statistics/manga/{manga_id}"
    stats_response = requests.get(stats_url)
    stats_data = stats_response.json().get("statistics", {}).get(manga_id, {})
    
    # Ensure average_rating is a valid decimal
    average_rating = stats_data.get("rating", {}).get("average", None)
    if isinstance(average_rating, (int, float)):
        average_rating = round(min(max(average_rating, 0), 9.99), 2)  # Ensure within valid range (0-9.99)
    else:
        average_rating = None
    
    follows = stats_data.get("follows", 0)
    views = stats_data.get("views", 0)

    # Fetch chapters
    chapters = []
    chapter_url = f"{BASE_URL}/manga/{manga_id}/feed?order[chapter]=asc"
    chapter_response = requests.get(chapter_url)
    if chapter_response.status_code == 200:
        chapter_data = chapter_response.json().get("data", [])
        for chap in chapter_data:
            chap_attr = chap.get("attributes", {})
            chapters.append({
                "chapter_number": chap_attr.get("chapter", "Unknown"),
                "title": chap_attr.get("title", "No title"),
                "release_date": chap_attr.get("createdAt", "Unknown")
            })
    
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
        "publishers": publishers,
        "cover_url": cover_url,
        "average_rating": average_rating,
        "follows": follows,
        "views": views,
        "chapters": chapters,
        "created_at": datetime.utcnow().isoformat()
    }
    
    time.sleep(RATE_LIMIT_DELAY)  # Prevent rate limiting
    return manga_data

def insert_into_supabase(manga_data):
    response = supabase.table("manga").upsert(manga_data).execute()
    print(f"Inserted into Supabase: {response}")
    time.sleep(RATE_LIMIT_DELAY)  # Prevent rate limiting

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
        time.sleep(60)  # Prevent hitting GitHub Actions time limit

if __name__ == "__main__":
    main()
