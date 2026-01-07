# Test Suite Documentation

## Running Tests

### Run all tests

```bash
pytest
```

### Run specific test categories

```bash
pytest -m unit
pytest -m integration
```

### Run specific test file

```bash
pytest tests/test_scraper.py
```

### Run specific test class or function

```bash
pytest tests/test_scraper.py::TestChunkText
pytest tests/test_scraper.py::TestChunkText::test_chunks_respect_max_tokens
```

### Run with coverage

```bash
pytest --cov=src --cov-report=html
```

## Test Structure

### Unit Tests

- `TestCleanHTML`: Validates HTML cleaning logic
- `TestCreateSlug`: Tests slug generation from titles
- `TestCountTokens`: Verifies token counting accuracy
- `TestChunkText`: Tests chunking strategy (safe split, overlap, token limits)
- `TestFindBackwardSafeSplit`: Tests safe split point detection
- `TestIsHeading`: Validates heading detection
- `TestIsInCodeBlock`: Tests code block detection

### Integration Tests

- `TestProcessArticle`: Tests article processing workflow
- `TestFetchArticles`: Tests API fetching logic
- `TestFetchUpdatedArticles`: Tests delta sync filtering
- `TestScraperIntegration`: End-to-end scraper workflow tests

## Key Test Cases

### Chunking Quality Tests

1. **Safe Split**: Ensures chunks don't break mid-sentence or mid-heading
2. **Overlap Validation**: Verifies overlap between consecutive chunks
3. **Token Limits**: Confirms no chunk exceeds max_tokens threshold
4. **Heading Preservation**: Validates headings stay intact
5. **Code Block Integrity**: Ensures code blocks aren't split

### Delta Sync Tests

1. **First Run (ADDED)**: All articles marked as new
2. **Unchanged (HASH_SKIPPED)**: Articles with same hash are skipped
3. **Updated (UPDATED)**: Changed articles trigger re-processing and old chunk deletion

## Fixtures (conftest.py)

- `sample_html`: HTML with navigation, ads, scripts to test cleaning
- `sample_article`: Basic article structure
- `sample_article_updated`: Modified version for update testing
- `empty_hash_store`: Clean state for first-run tests
- `populated_hash_store`: Pre-existing data for delta sync tests
- `temp_directories`: Temporary file system for integration tests
- `long_text_with_headings`: Multi-section text for chunking tests
- `text_with_lists`: Text with numbered and bulleted lists

## Coverage Goals

- Unit test coverage: >90%
- Integration test coverage: >80%
- Critical paths (chunking, delta sync): 100%
