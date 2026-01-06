import requests
import json
import re
import os
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from .config import *
from .helper import *
from markdownify import markdownify
import tiktoken

load_dotenv()

tokenizer = tiktoken.encoding_for_model("gpt-4o")

RAW_DATA_BASE_URL = os.getenv("RAW_DATA_BASE_URL")

def count_tokens(text):
    return len(tokenizer.encode(text))

def create_slug(article_id, title):
    title_slug = re.sub(r'[^\w\s-]', '', title.lower())
    title_slug = re.sub(r'[-\s]+', '-', title_slug).strip('-')
    return f"{article_id}-{title_slug}"

def get_overlap_text(text, overlap):
    return text[-overlap:] if text and overlap > 0 else ""

def character_split_with_overlap(text, max_size, overlap):
    chunks = []
    for i in range(0, len(text), max_size - overlap):
        chunks.append(text[i:i + max_size])
        if i + max_size >= len(text): break
    return chunks

def chunk_text(text, max_tokens=1000, overlap_pct=0.15):
    tokens = tokenizer.encode(text)
    total_tokens = len(tokens)
    overlap_size = int(max_tokens * overlap_pct)
    chunks = []
    
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, total_tokens)
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens)
        
        is_last_chunk = (end == total_tokens)
        
        if end < len(tokens):
            last_break = chunk_text.rfind('\n\n')
            if last_break == -1:
                last_break = chunk_text.rfind('. ')
            
            if last_break != -1:
                potential_text = chunk_text[:last_break + 2]
                potential_tokens_count = len(tokenizer.encode(potential_text))
                
                if potential_tokens_count > (max_tokens * 0.7):
                    chunk_text = potential_text
        
        chunks.append(chunk_text.strip())
        
        if is_last_chunk:
            break
        
        actual_chunk_tokens = len(tokenizer.encode(chunk_text))
        effective_overlap = min(overlap_size, int(actual_chunk_tokens * 0.3))
        start += max(1, actual_chunk_tokens - effective_overlap)
        
    return chunks

def fetch_articles(max_articles=None):
    env = os.getenv("ENV")
    
    url = f"https://{RAW_DATA_BASE_URL}/api/v2/help_center/en-us/articles"
    
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate"
    }
    
    if env == "development":
        if max_articles:
            url += f"?per_page={max_articles}"
            
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        
        print(f"Total fetched articles: {len(articles)}")
        
        return articles

    url += "?per_page=100"
    
    all_articles = []
    page_cnt = 0
    
    while url:
        page_cnt += 1
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        all_articles.extend(data.get("articles", []))
        url = data.get("next_page")

    print(f"Total fetched articles: {len(all_articles)}")
    return all_articles

def fetch_updated_articles(start_time, max_articles=None):
    start_time = start_time or 0
    
    def filter_updated_articles(articles):
        updated_articles = []
        for article in articles:
            updated_at_str = article.get("updated_at")
            
            if updated_at_str:
                updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                updated_at_timestamp = int(updated_at.timestamp())

                if updated_at_timestamp > start_time:
                    updated_articles.append(article)
                
        return updated_articles
    
    env = os.getenv("ENV")
    
    # API is authorized
    # url = f"https://{RAW_DATA_BASE_URL}/api/v2/help_center/incremental/articles?start_time={start_time}"
    
    url = f"https://{RAW_DATA_BASE_URL}/api/v2/help_center/en-us/articles"
    
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate"
    }
    
    end_time = int(time.time())
    
    if env == "development":
        if max_articles:
            url += f"?per_page={max_articles}"
            
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        
        updated_articles = filter_updated_articles(articles)
        print(f"Total fetched updated articles: {len(updated_articles)}")
        return updated_articles, end_time

    url += "?per_page=100"
    
    all_articles = []
    page_cnt = 0
    
    while url:
        page_cnt += 1
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        all_articles.extend(data.get("articles", []))
        url = data.get("next_page")

    all_updated_articles = filter_updated_articles(all_articles)
    print(f"Total fetched updated articles: {len(all_updated_articles)}")
    return all_updated_articles, end_time

def delete_old_chunks(article_id, slug, markdown_dir):
    # Pattern: {article_id}-{slug}-part*.md
    pattern = f"{article_id}-{slug}-part*.md"
    old_files = list(markdown_dir.glob(pattern))
    
    for old_file in old_files:
        old_file.unlink() 

def process_article(article, hash_store, raw_data_dir, markdown_dir):
    article_id = article["id"]
    article_title = article["title"]
    article_body = article.get("body", "")
    article_url = article.get("html_url", "")
    updated_at = article.get("updated_at", "")
    
    slug = create_slug(article_id, article_title)
    markdown_content = markdownify(article_body, heading_style="ATX")
    content_hash = calculate_content_hash(markdown_content)
    
    article_id_str = str(article_id)
    action = "ADDED"
    
    if article_id_str in hash_store["articles"]:
        stored_hash = hash_store["articles"][article_id_str].get("hash", "")
        if stored_hash == content_hash:
            return "HASH_SKIPPED", []
        else:
            action = "UPDATED"
            delete_old_chunks(article_id, slug, markdown_dir)
    
    raw_filename = f"{slug}.json"
    raw_filepath = raw_data_dir / raw_filename
    with open(raw_filepath, 'w', encoding='utf-8') as f:
        json.dump(article, f, ensure_ascii=False, indent=2)

    chunks = chunk_text(markdown_content, max_tokens=CHUNK_BODY_TOKENS, overlap_pct=OVERLAP_PERCENTAGE)
    chunk_paths = []
    
    for idx, chunk_content in enumerate(chunks, start=1):
        chunk_with_metadata = f"# {article_title}\n\n"
        
        chunk_with_metadata += f"Article URL: {article_url}\n\n\n"
        
        chunk_with_metadata += chunk_content
        chunk_with_metadata += f"\n\n---\n\nArticle URL: {article_url}"
        
        chunk_token_count = count_tokens(chunk_with_metadata)
        # print(f"  Chunk {idx}: {chunk_token_count} tokens")
        
        chunk_filename = f"{slug}-part{idx}.md"
        chunk_filepath = markdown_dir / chunk_filename
        with open(chunk_filepath, 'w', encoding='utf-8') as f:
            f.write(chunk_with_metadata)
        chunk_paths.append(chunk_filepath)
    
    hash_store["articles"][article_id_str] = {
        "hash": content_hash,
        "openai_file_ids": hash_store["articles"].get(article_id_str, {}).get("openai_file_ids", []),
        "updated_at": updated_at,
        "num_chunks": len(chunks)
    }
    
    return action, chunk_paths

def scraper(max_articles=None):
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    raw_data_dir = data_dir / "raw"
    markdown_dir = data_dir / "markdown"
    
    data_dir.mkdir(parents=True, exist_ok=True)
    raw_data_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir.mkdir(parents=True, exist_ok=True)
    
    hash_store = load_hash_store(data_dir)
    last_fetching_time = hash_store.get("last_fetching_time")
    
    stats = {"ADDED": 0, "UPDATED": 0, "API_SKIPPED": 0, "HASH_SKIPPED": 0}

    if last_fetching_time is None:
        all_articles = fetch_articles(MAX_ARTICLES_IN_DEVELOPMENT)
        end_time = int(time.time())
        stats["API_SKIPPED"] = 0
    else:
        existing_article_ids = set(hash_store["articles"].keys())
        total_in_store = len(existing_article_ids)
        all_articles, end_time = fetch_updated_articles(last_fetching_time, MAX_ARTICLES_IN_DEVELOPMENT)
        stats["API_SKIPPED"] = total_in_store - len(all_articles)
   
    changed_articles = {"added": {}, "updated": {}}
    
    for article in all_articles:
        try:
            action, chunk_paths = process_article(article, hash_store, raw_data_dir, markdown_dir)
            if action == "HASH_SKIPPED":
                stats["HASH_SKIPPED"] += 1
            else:
                stats[action] += 1
                article_id = article["id"]
                if action == "ADDED":
                    changed_articles["added"][article_id] = chunk_paths
                elif action == "UPDATED":
                    changed_articles["updated"][article_id] = chunk_paths
        except Exception as e:
            print(f"Error processing article {article.get('id', 'unknown')}: {e}")
            
    hash_store["last_fetching_time"] = end_time
    save_hash_store(hash_store, data_dir)
    
    total_skipped = stats["API_SKIPPED"] + stats["HASH_SKIPPED"]
    
    print(f"[ADDED]:   {stats['ADDED']} article(s)")
    print(f"[UPDATED]: {stats['UPDATED']} article(s)")
    print(f"[SKIPPED]: {total_skipped} (Total unchanged)")
    print(f"   |-- From API filter: {stats["API_SKIPPED"]}")
    print(f"   |-- From Hash match: {stats['HASH_SKIPPED']}")
    print(f"Next start_time: {end_time}")
    
    return changed_articles # Returns {"added": {article_id: [chunk_paths]}, "updated": {article_id: [chunk_paths]}}
