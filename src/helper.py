import hashlib
import json

def calculate_content_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def load_hash_store(data_dir):
    hash_store_path = data_dir / "hash_store.json"
    
    if hash_store_path.exists():
        with open(hash_store_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {
        "last_fetching_time": None,
        "articles": {}
    }
    
def save_hash_store(hash_store, data_dir):
    hash_store_path = data_dir / "hash_store.json"
    with open(hash_store_path, 'w', encoding='utf-8') as f:
        json.dump(hash_store, f, ensure_ascii=False, indent=2)