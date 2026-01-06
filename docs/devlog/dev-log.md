##### 1. Scarper: Pull ≥ 30 articles from support.optisigns.com.

![alt text](image.png)

##### 2. Scarper: Convert each article to clean Markdown.

![alt text](image-1.png)

##### 3. Uploader: Upload Markdown files to OpenAI Vector Store via OpenAI API.

###### Result 1:

![alt text](image-2.png)

=> The result is incorrect; the AI responded based on its default knowledge.
=> Error detected:

- The vector store does not contain data related to YouTube.
  => The error originates from "scraper.py" because, by default, it only crawls 30 articles.

![alt text](image-3.png)

##### 4. New solution for Scraper and uploader

###### => Problem 1: Context Retention and Cost Management

- **Context Preservation**: Splitting articles into multiple chunks can cause the AI to lose global context. To mitigate this, each chunk must include the article title, category, and overlapping content from adjacent segments.
- **Token Optimization**: To manage OpenAI Assistant API costs, we must strictly control the number of tokens per chunk.

**Solution**: Split each original `.md` file into smaller fragments using this structure:

```text
# [Title]
## Category: [Breadcrumb]
Source: [Article URL]
***
[Main Content of Chunk]
***
[Overlap from previous/next chunk]
***
Article URL: [Article URL]
```

**Cost Estimation and Configuration**:

- **Overlap**: Set to 0 in the Vector Store configuration, as overlap is now handled manually within the content structure.
- **Predictable Costs**: By fixing the chunk size (e.g., 1,000 tokens) and limiting the number of retrieved files (e.g., 5), we can cap the cost per query.
- _Example_: 5 files × 1,000 tokens = 5,000 tokens. At $0.01/1k tokens, the cost is approximately $0.05 per prompt.

###### => Problem 2: Precise Change Detection

- To efficiently update files, we need to accurately detect content changes. Two primary methods exist: monitoring the `updated_at` field or using content hashing. Both have limitations:
  - **`updated_at` field**: The Zendesk API (`GET /api/v2/help_center/incremental/articles?start_time={start_time}`) tracks metadata changes. However, as noted in the documentation, metadata updates do not always reflect changes in the actual body content.
  - **Hashing**: Hashing every file to detect changes is computationally expensive and time-consuming, especially for large datasets.
- **Solution**: A two-layered approach.
  1. **Layer 1**: Use the Zendesk API to identify articles with any changes (metadata or content) since the last sync.
  2. **Layer 2**: Perform a hash comparison on the body content of those specific articles to confirm if a re-upload to the vector store is actually required.
```
