import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def uploader():
    api_key = os.getenv("OPENAI_API_KEY")
    vector_store_id = os.getenv("VECTOR_STORE_ID")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    if not vector_store_id:
        raise ValueError("VECTOR_STORE_ID not found in environment variables")
    
    client = OpenAI(api_key=api_key)
    
    markdown_dir = Path(__file__).parent.parent / "data" / "markdown"
    
    if not markdown_dir.exists():
        raise FileNotFoundError(f"Markdown directory not found: {markdown_dir}")
    
    md_files = list(markdown_dir.glob("*.md"))
    
    if not md_files:
        print("No markdown files found to upload")
        return
    
    print(f"Found {len(md_files)} markdown files to upload")
    print("-" * 50)
    
    file_ids = []
    
    for md_file in md_files:
        print(f"Uploading: {md_file.name}")
        
        with open(md_file, 'rb') as f:
            uploaded_file = client.files.create(
                file=f,
                purpose='assistants'
            )
        
        file_ids.append(uploaded_file.id)
        print(f"File ID: {uploaded_file.id}")
    
    print("-" * 50)
    print(f"Complete: Uploaded {len(file_ids)} files to OpenAI")
    print("-" * 50)
    
    print(f"Attaching files to Vector Store: {vector_store_id}")
    
    for file_id in file_ids:
        client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id
        )
    
    print("-" * 50)
    print(f"Complete: Successfully attached {len(file_ids)} files to Vector Store")
    print(f"Vector Store ID: {vector_store_id}")
    print("-" * 50)
