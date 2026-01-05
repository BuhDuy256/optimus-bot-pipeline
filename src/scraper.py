import requests
import json
import re
import os
from pathlib import Path
from . import config

def create_slug(article_id, title):
    title_slug = re.sub(r'[^\w\s-]', '', title.lower())
    title_slug = re.sub(r'[-\s]+', '-', title_slug).strip('-')
    return f"{article_id}-{title_slug}"

def scraper():
    url = f"https://{config.RAW_DATA_BASE_URL}/api/v2/help_center/en-us/articles"
    headers = {
        "Content-Type": "application/json",
    }
    
    response = requests.request(
        "GET",
        url,
        headers=headers
    )
    data = response.json()
    
    raw_data_dir = Path(__file__).parent.parent / "data" / "raw"
    raw_data_dir.mkdir(parents=True, exist_ok=True)
    
    for article in data["articles"]:
        article_id = article["id"]
        article_title = article["title"]
        
        slug = create_slug(article_id, article_title)
        
        filename = f"{slug}.json"
        filepath = raw_data_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(article, f, ensure_ascii=False, indent=2)
        
        print(f"Saved article: {filename}")
