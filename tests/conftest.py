import pytest
from pathlib import Path
from unittest.mock import Mock
import json

@pytest.fixture
def sample_html():
    return """
    <html>
        <head>
            <script>var x = 1;</script>
            <style>.test { color: red; }</style>
        </head>
        <body>
            <nav>Navigation</nav>
            <header>Header</header>
            <div class="content">
                <h1>Main Content</h1>
                <p>This is the actual content we want.</p>
            </div>
            <div class="sidebar">Sidebar content</div>
            <div class="ad-banner">Advertisement</div>
            <footer>Footer content</footer>
            <iframe src="ads.html"></iframe>
        </body>
    </html>
    """

@pytest.fixture
def sample_article():
    return {
        "id": 123456,
        "title": "How to Add YouTube Videos",
        "body": "<h1>Guide</h1><p>Step 1: Click upload</p><p>Step 2: Paste URL</p>",
        "html_url": "https://support.optisigns.com/articles/123456",
        "updated_at": "2024-01-15T10:30:00Z"
    }

@pytest.fixture
def sample_article_updated():
    return {
        "id": 123456,
        "title": "How to Add YouTube Videos",
        "body": "<h1>Updated Guide</h1><p>Step 1: Click new upload button</p><p>Step 2: Paste URL</p>",
        "html_url": "https://support.optisigns.com/articles/123456",
        "updated_at": "2024-01-20T14:45:00Z"
    }

@pytest.fixture
def empty_hash_store():
    return {
        "articles": {},
        "last_fetching_time": None
    }

@pytest.fixture
def populated_hash_store():
    return {
        "articles": {
            "123456": {
                "hash": "abc123def456",
                "openai_file_ids": ["file-xyz"],
                "updated_at": "2024-01-15T10:30:00Z",
                "num_chunks": 1
            }
        },
        "last_fetching_time": 1705315800
    }

@pytest.fixture
def mock_zendesk_response():
    return {
        "articles": [
            {
                "id": 123456,
                "title": "Test Article",
                "body": "<p>Test content</p>",
                "html_url": "https://support.optisigns.com/articles/123456",
                "updated_at": "2024-01-15T10:30:00Z"
            },
            {
                "id": 789012,
                "title": "Another Article",
                "body": "<p>Another content</p>",
                "html_url": "https://support.optisigns.com/articles/789012",
                "updated_at": "2024-01-16T11:00:00Z"
            }
        ],
        "next_page": None
    }

@pytest.fixture
def temp_directories(tmp_path):
    data_dir = tmp_path / "data"
    raw_data_dir = data_dir / "raw"
    markdown_dir = data_dir / "markdown"
    
    data_dir.mkdir(parents=True, exist_ok=True)
    raw_data_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        "base_dir": tmp_path,
        "data_dir": data_dir,
        "raw_data_dir": raw_data_dir,
        "markdown_dir": markdown_dir
    }

@pytest.fixture
def long_text_with_headings():
    return """# Main Title

## Section 1

This is the first section with some content. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

### Subsection 1.1

More detailed content here. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

## Section 2

Another section with different content. Ut enim ad minim veniam, quis nostrud exercitation ullamco.

### Subsection 2.1

- Item 1
- Item 2
- Item 3

## Section 3

Final section with a code block:

```python
def example():
    return "code"
```

End of document."""

@pytest.fixture
def text_with_lists():
    return """# Shopping List

Here are the items:

1. First item with a long description that goes on and on
2. Second item also with details
3. Third item with more information

And some bullets:

* Alpha point
* Beta point
* Gamma point

That's all."""

@pytest.fixture
def mock_openai_client():
    from unittest.mock import MagicMock
    client = MagicMock()
    
    file_obj = MagicMock()
    file_obj.id = "file-test123"
    client.files.create.return_value = file_obj
    
    batch_result = MagicMock()
    batch_result.file_counts.completed = 1
    client.vector_stores.file_batches.create_and_poll.return_value = batch_result
    
    client.vector_stores.files.delete.return_value = None
    client.files.delete.return_value = None
    
    return client

@pytest.fixture
def sample_chunk_files(temp_directories):
    markdown_dir = temp_directories["markdown_dir"]
    
    chunk1 = markdown_dir / "123-test-article-part1.md"
    chunk2 = markdown_dir / "123-test-article-part2.md"
    chunk3 = markdown_dir / "456-another-article-part1.md"
    
    chunk1.write_text("# Test Article\n\nChunk 1 content")
    chunk2.write_text("# Test Article\n\nChunk 2 content")
    chunk3.write_text("# Another Article\n\nChunk 1 content")
    
    return {
        "123": [chunk1, chunk2],
        "456": [chunk3]
    }

@pytest.fixture
def hash_store_with_files():
    return {
        "articles": {
            "123": {
                "hash": "oldhash123",
                "openai_file_ids": ["file-old1", "file-old2"],
                "updated_at": "2024-01-15T10:30:00Z",
                "num_chunks": 2
            }
        },
        "last_fetching_time": 1705315800
    }
