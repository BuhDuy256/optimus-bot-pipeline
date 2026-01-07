# Delta Detection Mechanism

## The Problem

To keep the vector store up-to-date efficiently, we need to detect which articles have actually changed. Simply re-uploading all articles every time is wasteful and expensive.

Two common approaches exist, but both have issues:

### Method 1: Using `updated_at` Field

**How it works:**

- Fetch all articles from the API
- Check the `updated_at` timestamp on each article
- Compare it with the last sync time
- Process only articles modified after the last sync

**The Problem:**

- The `updated_at` field tracks **metadata changes** (title, tags, category, etc.)
- Metadata updates don't always mean the **body content** changed
- This can trigger unnecessary re-uploads when only minor metadata changed

### Method 2: Content Hashing

**How it works:**

- Calculate a hash (like MD5 or SHA256) of each article's content
- Compare the new hash with the stored hash
- If different, the content changed

**The Problem:**

- Must hash **every single article** in the database
- Very slow for large datasets (thousands of articles)
- Computationally expensive

## The Solution: Two-Layer Detection

We combine both methods to get the best of both worlds:

### Layer 1: Quick Filter with Timestamp

Fetch all articles and filter them by `updated_at` timestamp:

**Result:** Quickly narrow down from thousands of articles to maybe 10-50 candidates that were modified since the last sync

### Layer 2: Hash Verification

Only hash the **body content** of articles from Layer 1 to confirm actual content changes:

**Result:** Only re-upload articles with actual content changes

## Benefits

1. **Fast**: Layer 1 filters out 99% of articles instantly
2. **Accurate**: Layer 2 confirms real content changes
3. **Efficient**: Only hash a small subset of articles
4. **Cost-Effective**: Avoid unnecessary vector store upload