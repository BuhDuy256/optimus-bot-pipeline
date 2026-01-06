import os
from pathlib import Path
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from .helper import *
from .config import *
import time

load_dotenv()

def extract_article_id(filename: str) -> Optional[int]:
    match = CHUNK_NAME_FORMAT.match(filename)
    if match:
        return int(match.group(1))
    return None


def group_files_by_article(markdown_files):
    article_files = {}
    for file_path in markdown_files:
        article_id = extract_article_id(file_path.name)
        if article_id:
            article_files.setdefault(article_id, []).append(file_path)
    return article_files


def upload_files_batch(client, vector_store_id, markdown_files):
    file_ids = []
    article_file_mapping = {}
    
    for path in markdown_files:
        try:
            with open(path, "rb") as f:
                file_obj = client.files.create(file=f, purpose="assistants")
                file_ids.append(file_obj.id)
                
                article_id = extract_article_id(path.name)
                if article_id:
                    article_file_mapping.setdefault(article_id, []).append(file_obj.id)
        except Exception as e:
            print(f"Failed to upload {path.name}: {e}")

    if file_ids:
        client.vector_stores.file_batches.create_and_poll(
            vector_store_id=vector_store_id,
            file_ids=file_ids
        )

    return article_file_mapping
        
def delete_old_files(client, vector_store_id, file_ids):
    for file_id in file_ids:
        try:
            client.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
        except Exception as e:
            print(f"Failed to delete {file_id} from vector store: {e}")
        
        try:
            client.files.delete(file_id=file_id)
        except Exception as e:
            print(f"Failed to delete {file_id} from storage: {e}")
    
def upload_article_chunks(client, vector_store_id, article_id, chunk_files, old_file_ids):
    try:
        if old_file_ids:
            delete_old_files(client, vector_store_id, old_file_ids)
        
        new_file_ids = []
        for chunk_file in chunk_files:
            with open(chunk_file, "rb") as f:
                uploaded_file = client.files.create(
                    file=f,
                    purpose="assistants"
                )
            new_file_ids.append(uploaded_file.id)
        
        for file_id in new_file_ids:
            client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file_id,
                chunking_strategy={
                    "type": "static",
                    "static": {
                        "max_chunk_size_tokens": 1100,
                        "chunk_overlap_tokens": 0
                    }
                }
            )
        
        return new_file_ids, True
    except Exception as e:
        print(f"Error uploading article {article_id}: {e}")
        return [], False
            
def upload_incremental(client, vector_store_id, article_files, hash_store):
    article_file_mapping = {}
    failed_articles = []
    stats = {"added": 0, "updated": 0, "failed": 0}
    
    for article_id, chunk_files in article_files.items():
        article_id_str = str(article_id)
        
        old_file_ids = hash_store.get("articles", {}).get(article_id_str, {}).get("openai_file_ids", [])
        
        new_file_ids, success = upload_article_chunks(
            client,
            vector_store_id,
            article_id,
            chunk_files,
            old_file_ids
        )
        
        if success:
            article_file_mapping[article_id] = new_file_ids
            if old_file_ids:
                stats["updated"] += 1
            else:
                stats["added"] += 1
        else:
            failed_articles.append(article_id)
            stats["failed"] += 1
    
    return article_file_mapping, failed_articles

def uploader():
    api_key = os.getenv("OPENAI_API_KEY")
    vector_store_id = os.getenv("VECTOR_STORE_ID")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    if not vector_store_id:
        raise ValueError("VECTOR_STORE_ID not found in environment variables")
    
    client = OpenAI(api_key=api_key)
     
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    raw_data_dir = data_dir / "raw"
    markdown_dir = data_dir / "markdown"
    
    if not markdown_dir.exists():
        raise FileNotFoundError(f"Markdown directory not found: {markdown_dir}")
    
    hash_store = load_hash_store(data_dir)
    
    md_files = list(markdown_dir.glob("*.md"))
    
    if not md_files:
        print("No markdown files found to upload")
        return

    article_files = group_files_by_article(md_files)
    
    last_fetching_time = hash_store.get("last_fetching_time")
    article_file_mapping = {}
    failed_articles = []
    
    print("Uploading...")
    
    if last_fetching_time is None:
        article_file_mapping = upload_files_batch(
            client,
            vector_store_id,
            md_files
        )
    else:
        article_file_mapping, failed_articles = upload_incremental(
            client,
            vector_store_id,
            article_files,
            hash_store
        )
    
    for article_id, file_ids in article_file_mapping.items():
        article_id_str = str(article_id)
        
        if article_id_str not in hash_store["articles"]:
            hash_store["articles"][article_id_str] = {
                "hash": "init_sync",
                "openai_file_ids": []
            }
        
        hash_store["articles"][article_id_str]["openai_file_ids"] = file_ids
    
    hash_store["last_fetching_time"] = int(time.time())
    save_hash_store(hash_store, data_dir)
    
    print(f"Upload complete: {len(article_file_mapping)} articles uploaded")
