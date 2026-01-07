# Chunking Strategy

## The Problem

If we upload full files and let OpenAI split them automatically, two issues occur:

1. **Lost Context**: The AI may struggle to understand the context when reading small pieces
2. **Unknown Costs**: We can't control how many tokens the AI reads per response, making costs hard to predict

## The Solution

We take control of the chunking process:

### Step 1: Manual Chunking

- Split each `.md` file into smaller chunks ourselves
- Add overlap between chunks (controlled by `OVERLAP_PERCENTAGE` in config)
- This keeps context flowing between related pieces

### Step 2: Add Article Info to Each Chunk

Each chunk uses this format:

```text
# [Article Title]

Article URL: [Article URL]


[Main chunk content with overlap]


---

Article URL: [Article URL]
```

This helps the Assistant recognize the original article and mention it in responses.

### Step 3: Control Token Usage

By setting `CHUNK_BODY_TOKENS` (e.g., 800), we can predict costs:

- Each chunk = ~900 tokens (`CHUNK_BODY_TOKENS` + 100 for title/URL)
- File search returns max 5 results
- Max tokens per response = 5 × 1,000 = 5,000 tokens
- At $0.01 per 1,000 tokens → Max cost = **$0.05 per response**

**Result**: Predictable costs and better context understanding.

## Implementation

The chunking logic in [src/scraper.py](src/scraper.py) uses smart splitting that respects:

- Paragraph boundaries (double newlines)
- List items (avoid breaking mid-list)
- Code blocks (never split inside backticks)
- Headings (prefer splitting before headers)
- Sentences (split at sentence endings when possible)

This ensures chunks remain readable and contextually meaningful, not just arbitrary character cuts.
