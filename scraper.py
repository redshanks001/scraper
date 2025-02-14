import requests
import json
from supabase import create_client

# Supabase credentials
SUPABASE_URL = "https://cbdkiyruretigoldouhf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNiZGtpeXJ1cmV0aWdvbGRvdWhmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczODU2NDc5OSwiZXhwIjoyMDU0MTQwNzk5fQ.NqeVS9WSjeGYjAM52XRXOS_FTjgE8uyTM4yDmkqSy5I"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# MangaDex API (UUID for Bungou Stray Dogs)
MANGA_UUID = "3fba42cf-2ad6-4c30-a7ab-46cb8149208a"  
MANGADEX_API_URL = f"https://api.mangadex.org/manga/{MANGA_UUID}?includes[]=cover_art&includes[]=author&includes[]=artist"

def scrape_manga():
    response = requests.get(MANGADEX_API_URL)
    if response.status_code == 200:
        data = response.json()
        manga = data.get("data", {})
        attributes = manga.get("attributes", {})

        # Extract data
        title = attributes.get("title", {}).get("en", "Unknown")
        description = attributes.get("description", {}).get("en", "No description available")
        status = attributes.get("status", "Unknown").capitalize()
        year = attributes.get("year", None)
        tags = [tag["attributes"]["name"]["en"] for tag in attributes.get("tags", [])]

        # Extract cover image
        cover = next((rel for rel in manga.get("relationships", []) if rel["type"] == "cover_art"), {})
        cover_url = f"https://uploads.mangadex.org/covers/{MANGA_UUID}/{cover.get('attributes', {}).get('fileName', '')}"

        # Insert into Supabase
        manga_data = {
            "title": title,
            "description": description,
            "year": year,
            "status": status,
            "tags": tags,
            "cover_url": cover_url
        }
        
        response = supabase.table("manga").upsert(manga_data).execute()
        print("Inserted into Supabase:", response)

    else:
        print("Failed to fetch data from MangaDex")

if __name__ == "__main__":
    scrape_manga()
