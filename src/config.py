import re

CHUNK_NAME_FORMAT = re.compile(r'^(\d+)-.*-part\d+\.md$')
MAX_ARTICLES_IN_DEVELOPMENT=50
BATCH_SIZE = 500
CHUNK_BODY_TOKENS = 800
MAX_CHUNK_TOKENS = CHUNK_BODY_TOKENS + 100
OVERLAP_PERCENTAGE = 0.15
VECTOR_STORE_ID="vs_695d0cc82a1481919b47306479820757"
RAW_DATA_BASE_URL="support.optisigns.com"

# Environment Modes:
# - Production (ENV = "production"): Scrapes all articles from the API for full data sync
# - Development (ENV = "development"): Scrapes only MAX_ARTICLES_IN_DEVELOPMENT articles for testing purposes
ENV="development"