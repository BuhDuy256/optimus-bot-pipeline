import os
from pathlib import Path
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from .helper import *
from .config import *
import time

load_dotenv()

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

def upload_added_articles(client, vector_store_id, added_articles):
    if not added_articles:
        return {}
    
    print(f"Uploading {len(added_articles)} added articles...")
    
    article_file_mapping = {}
    file_ids = []
    chunk_to_file_id = {}
    
    # Step 1: Upload all files to OpenAI storage
    for article_id, chunk_paths in added_articles.items():
        for chunk_path in chunk_paths:
            try:
                with open(chunk_path, "rb") as f:
                    file_obj = client.files.create(file=f, purpose="assistants")
                    file_ids.append(file_obj.id)
                    chunk_to_file_id[str(chunk_path)] = file_obj.id
            except Exception as e:
                print(f"Failed to upload {chunk_path.name}: {e}")
    
    # Step 2: Add files to vector store in batches (max 500 per batch)
    if file_ids:
        total_files = len(file_ids)
        
        for i in range(0, total_files, BATCH_SIZE):
            batch = file_ids[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (total_files + BATCH_SIZE - 1) // BATCH_SIZE
            
            try:
                print(f"Adding batch {batch_num}/{total_batches} ({len(batch)} files) to vector store...")
                client.vector_stores.file_batches.create_and_poll(
                    vector_store_id=vector_store_id,
                    file_ids=batch,
                    chunking_strategy={
                        "type": "static",
                        "static": {
                            "max_chunk_size_tokens": MAX_CHUNK_TOKENS + 200,
                            "chunk_overlap_tokens": 0
                        }
                    }
                )
            except Exception as e:
                print(f"Failed to add batch {batch_num} to vector store: {e}")
    
    # Step 3: Map file IDs back to articles
    for article_id, chunk_paths in added_articles.items():
        article_file_ids = []
        for chunk_path in chunk_paths:
            file_id = chunk_to_file_id.get(str(chunk_path))
            if file_id:
                article_file_ids.append(file_id)
        
        if article_file_ids:
            article_file_mapping[article_id] = article_file_ids
    
    print(f"Added {len(article_file_mapping)} articles successfully")
    return article_file_mapping

def upload_updated_articles(client, vector_store_id, updated_articles, hash_store):
    if not updated_articles:
        return {}
    
    print(f"Uploading {len(updated_articles)} updated articles...")
    
    for article_id, chunk_files in updated_articles.items():
        article_id_str = str(article_id)
        old_file_ids = hash_store.get("articles", {}).get(article_id_str, {}).get("openai_file_ids", [])
        
        if old_file_ids:
            print(f"Deleting {len(old_file_ids)} old files for article {article_id}...")
            delete_old_files(client, vector_store_id, old_file_ids)
    
    return upload_added_articles(client, vector_store_id, updated_articles)
    
def uploader(changed_articles):
    if changed_articles is None:
        print("No changed articles to upload")
        return
    
    api_key = os.getenv("OPENAI_API_KEY")
    vector_store_id = os.getenv("VECTOR_STORE_ID")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    if not vector_store_id:
        raise ValueError("VECTOR_STORE_ID not found in environment variables")
     
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    raw_data_dir = data_dir / "raw"
    markdown_dir = data_dir / "markdown"
    
    if not markdown_dir.exists():
        raise FileNotFoundError(f"Markdown directory not found: {markdown_dir}")
    
    client = OpenAI(api_key=api_key)
    hash_store = load_hash_store(data_dir)
    
    # Extract added and updated articles
    added_articles = changed_articles.get("added", {})
    updated_articles = changed_articles.get("updated", {})
    
    if not added_articles and not updated_articles:
        print("No changed articles to upload")
        return
    
    print("Uploading...")
    
    added_mapping = upload_added_articles(
        client,
        vector_store_id,
        added_articles
    )
    
    updated_mapping = upload_updated_articles(
        client,
        vector_store_id,
        updated_articles,
        hash_store
    )
    
    article_file_mapping = {**added_mapping, **updated_mapping}
    
    for article_id, file_ids in article_file_mapping.items():
        article_id_str = str(article_id)  
        hash_store["articles"][article_id_str]["openai_file_ids"] = file_ids
    
    hash_store["last_fetching_time"] = int(time.time())
    save_hash_store(hash_store, data_dir)
    
    print(f"Upload complete: {len(added_mapping)} added, {len(updated_mapping)} updated")