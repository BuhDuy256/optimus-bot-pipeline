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
from bs4 import BeautifulSoup

load_dotenv()

tokenizer = tiktoken.encoding_for_model("gpt-4o")

RAW_DATA_BASE_URL = os.getenv("RAW_DATA_BASE_URL")

def count_tokens(text):
    return len(tokenizer.encode(text))

def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    unwanted_selectors = [
        'nav', 'header', 'footer',
        '[class*="nav"]', '[class*="menu"]',
        '[class*="sidebar"]', '[class*="ad"]',
        '[id*="nav"]', '[id*="menu"]',
        '[id*="sidebar"]', '[id*="ad"]',
        'script', 'style', 'iframe'
    ]
    
    for selector in unwanted_selectors:
        for element in soup.select(selector):
            element.decompose()
    
    return str(soup)

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

def find_safe_split_point(text, max_pos):
    last_para = text.rfind('\n\n', 0, max_pos)
    if last_para > max_pos * 0.5:
        return last_para + 2
    
    lines = text[:max_pos].split('\n')
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if re.match(r'^[\*\-\+\d]+\.?\s', line):
            if i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if not next_line or not re.match(r'^[\*\-\+\d]+\.?\s|^\s+', next_line):
                    pos = sum(len(l) + 1 for l in lines[:i+1])
                    if pos > max_pos * 0.5:
                        return pos
    
    sentence_end = max(
        text.rfind('. ', 0, max_pos),
        text.rfind('.\n', 0, max_pos),
        text.rfind('!\n', 0, max_pos),
        text.rfind('?\n', 0, max_pos)
    )
    if sentence_end > max_pos * 0.5:
        return sentence_end + 2
    
    last_newline = text.rfind('\n', 0, max_pos)
    if last_newline > max_pos * 0.5:
        return last_newline + 1
    
    return max_pos

def is_heading(line):
    return bool(re.match(r'^#{1,6}\s', line.strip()))

def find_backward_safe_split(text, target_pos):
    if target_pos >= len(text):
        return len(text)
    
    search_start = max(0, int(target_pos * 0.5))
    substring = text[search_start:target_pos]
    
    if is_in_code_block(text, target_pos):
        code_start = text.rfind('```', 0, target_pos)
        if code_start > search_start:
            return code_start
    
    lines = text[:target_pos].split('\n')
    for i in range(len(lines) - 1, max(0, len(lines) - 20), -1):
        if i >= len(lines):
            continue
        line = lines[i].strip()
        
        if is_heading(line):
            return sum(len(l) + 1 for l in lines[:i])
    
    next_line_start = text.rfind('\n', search_start, target_pos)
    if next_line_start != -1 and next_line_start > search_start:
        potential_line = text[next_line_start:target_pos].strip()
        if '](' in potential_line or '![' in potential_line:
            link_start = text.rfind('[', search_start, next_line_start)
            if link_start > search_start:
                return link_start
    
    para_break = text.rfind('\n\n', search_start, target_pos)
    if para_break > search_start:
        return para_break + 2
    
    for i in range(len(lines) - 1, max(0, len(lines) - 10), -1):
        if i >= len(lines):
            continue
        line = lines[i].strip()
        if re.match(r'^[\*\-\+\d]+\.?\s', line):
            if i < len(lines) - 1:
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if not next_line or not re.match(r'^[\*\-\+\d]+\.?\s|^\s+', next_line):
                    pos = sum(len(l) + 1 for l in lines[:i+1])
                    if pos > search_start:
                        return pos
    
    sentence_end = max(
        text.rfind('. ', search_start, target_pos),
        text.rfind('.\n', search_start, target_pos),
        text.rfind('!\n', search_start, target_pos),
        text.rfind('?\n', search_start, target_pos)
    )
    if sentence_end > search_start:
        return sentence_end + 2
    
    last_newline = text.rfind('\n', search_start, target_pos)
    if last_newline > search_start:
        return last_newline + 1
    
    return target_pos

def is_in_code_block(text, position):
    before_text = text[:position]
    code_fence_count = before_text.count('```')
    return code_fence_count % 2 == 1

def chunk_text(text, max_tokens=1000, overlap_pct=0.15):
    if not text or not text.strip():
        return []
    
    total_tokens = count_tokens(text)
    if total_tokens <= max_tokens:
        return [text]
    
    chunks = []
    overlap_tokens = int(max_tokens * overlap_pct)
    chars_per_token = len(text) / total_tokens
    target_chars = int(max_tokens * chars_per_token * 0.9)
    
    pos = 0
    while pos < len(text):
        end_pos = min(pos + target_chars, len(text))
        
        if end_pos < len(text):
            end_pos = find_backward_safe_split(text, end_pos)
        
        chunk = text[pos:end_pos].strip()
        
        chunk_tokens = count_tokens(chunk)
        if chunk_tokens > max_tokens * 1.3:
            while count_tokens(chunk) > max_tokens and len(chunk) > 100:
                last_space = chunk.rfind(' ', 0, int(len(chunk) * 0.9))
                if last_space > len(chunk) * 0.5:
                    chunk = chunk[:last_space]
                else:
                    tokens = tokenizer.encode(chunk)
                    chunk = tokenizer.decode(tokens[:max_tokens])
                    break
        
        if chunk:
            chunks.append(chunk)
        
        if end_pos >= len(text):
            break
        
        overlap_chars = int(overlap_tokens * chars_per_token)
        pos = max(pos + 1, end_pos - overlap_chars)
    
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
    
    cleaned_html = clean_html(article_body)
    markdown_content = markdownify(cleaned_html, heading_style="ATX")
    
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
        print(f"  Chunk {idx}: {chunk_token_count} tokens")
        
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
