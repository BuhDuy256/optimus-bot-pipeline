# Optimus Bot

## Set up & Local execution

### 1. Create Vector Store and Assistant on OpenAI

Go to [OpenAI Platform](https://platform.openai.com/):

#### Step 1: Create Vector Store

- Log in to your OpenAI account
- Go to **Vector Stores**
- Create a new Vector Store and save the `VECTOR_STORE_ID`

#### Step 2: Create Assistant

- Go to **Assistants**
- Create a new Assistant
- In the **Tools** section, enable **File Search**
- Select the Vector Store created in step 1 to load into the Assistant

### 2. Configure in `src/config.py`

Update the following parameters in [src/config.py](src/config.py):

```python
VECTOR_STORE_ID = "vs_xxxxx"  # Vector Store ID from OpenAI
ENV = "development"  # or "production"
MAX_ARTICLES_IN_DEVELOPMENT = 50  # Max number of articles in dev environment
BATCH_SIZE = 500  # Batch size for processing
CHUNK_BODY_TOKENS = 800  # Number of tokens per chunk
MAX_CHUNK_TOKENS = 900  # Max tokens (CHUNK_BODY_TOKENS + 100)
OVERLAP_PERCENTAGE = 0.15  # Overlap percentage between chunks
RAW_DATA_BASE_URL = "support.optisigns.com"  # Data source URL
```

### 3. Create .env file

Create a `.env` file with:

```
OPENAI_API_KEY=your_api_key_here
```

### 4. Run with Docker

```bash
docker build -t main.py .
docker run -e OPENAI_API_KEY=... main.py
```

## Chunking Strategy

### The Problem

If we upload full files and let OpenAI split them automatically, two issues occur:

1. **Lost Context**: The AI may struggle to understand the context when reading small pieces
2. **Unknown Costs**: We can't control how many tokens the AI reads per response, making costs hard to predict

### The Solution

We take control of the chunking process:

**Step 1: Manual Chunking**

- Split each `.md` file into smaller chunks ourselves
- Add overlap between chunks (controlled by `OVERLAP_PERCENTAGE` in config)
- This keeps context flowing between related pieces

**Step 2: Add Article Info to Each Chunk**

Each chunk uses this format:

```text
# [Article Title]

Article URL: [Article URL]


[Main chunk content with overlap]


---

Article URL: [Article URL]
```

This helps the Assistant recognize the original article and mention it in responses.

**Step 3: Control Token Usage**

By setting `CHUNK_BODY_TOKENS` (e.g., 800), we can predict costs:

- Each chunk = ~900 tokens (`CHUNK_BODY_TOKENS` + 100 for title/URL)
- File search returns max 5 results
- Max tokens per response = 5 × 1,000 = 5,000 tokens
- At \$0.01 per 1,000 tokens → Max cost = **\$0.05 per response**

**Result**: Predictable costs and better context understanding.

## Delta Detection Strategy

The system uses a two-layer delta detection mechanism to efficiently identify and update only articles with actual content changes. See [DELTA_DETECTION.md](DELTA_DETECTION.md) for details.

## Daily Job & Sync Logic

## Sanity Check & Validation

**Configuration Used:**

```python
CHUNK_BODY_TOKENS = 800
MAX_CHUNK_TOKENS = 900  # CHUNK_BODY_TOKENS + 100
OVERLAP_PERCENTAGE = 0.15
BATCH_SIZE = 500
MAX_ARTICLES_IN_DEVELOPMENT = 50
```

**Test Question:** "How do I add a YouTube video?"

**Response:**

![Validation Result](docs/images/image.png)

**Note:** There is no `.md` file about YouTube in the training data. The system prompt instructs: "Only answer using the uploaded docs." However, the Assistant still generated a response with an Article URL, showing it learned the pattern from training data but also hallucinated content.

**Why This Happens:**

- The system prompt may not be strong enough to fully constraint the AI
- Vector search uses semantic matching between the prompt and document chunks
- If no closely related documents exist, the AI may still respond based on its base knowledge

**Potential Solutions:**

- Strengthen the system prompt to enforce stricter boundaries
- Use another AI model to summarize each uploaded file's content, improving semantic matching and helping the vector store rank truly relevant documents higher
