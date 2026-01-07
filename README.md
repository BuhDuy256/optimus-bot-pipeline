# Optimus Bot

## How to Run Locally

**1. Create Vector Store & Assistant on [OpenAI Platform](https://platform.openai.com/)**

- Create a Vector Store → Save `VECTOR_STORE_ID`
- Create an Assistant → Enable **File Search** → Link to your Vector Store

**2. Config:** Update `VECTOR_STORE_ID` in [src/config.py](src/config.py)

**3. Env:** Create `.env` with:

```
OPENAI_API_KEY=your_api_key_here
```

**4. Run:**

```bash
docker build -t main.py .
docker run --env-file .env main.py
# Or: docker run -e OPENAI_API_KEY=... main.py
```

## Chunking Strategy

Instead of letting OpenAI split files automatically (which loses context and makes costs unpredictable), we manually chunk each article with controlled overlap (`OVERLAP_PERCENTAGE = 0.15`). Each chunk includes the article title and URL at the top and bottom, helping the AI recognize the source. By setting `CHUNK_BODY_TOKENS = 800`, we can predict costs: with max 5 search results × 1,000 tokens = 5,000 tokens/query (~$0.05 at $0.01/1k tokens). See [CHUNKING_STRATEGY.md](CHUNKING_STRATEGY.md) for details.

## Daily Job & Deployment

**Platform:** GitHub Actions (Digital Ocean requires credit card verification and $24 minimum deposit, which I don't have access to)

**Results:** See [docs/images/daily-job-logs.png](docs/images/daily-job-logs.png) for execution logs showing articles processed, chunked, and uploaded to vector store.

**Setup:** See [DEPLOY.md](DEPLOY.md) for GitHub Actions configuration.

## Validation

**Test:** "How do I add a YouTube video?" - See [docs/images/assistant-result.png](docs/images/assistant-result.png)
