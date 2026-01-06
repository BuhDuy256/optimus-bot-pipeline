import re

CHUNK_NAME_FORMAT = re.compile(r'^(\d+)-.*-part\d+\.md$')
MAX_ARTICLES_IN_DEVELOPMENT=100
CHUNK_BODY_TOKENS = 800
OVERLAP_PERCENTAGE = 0.1
BATCH_SIZE = 500
# Max tokens for OpenAI chunking (body + metadata overhead)
MAX_CHUNK_TOKENS = CHUNK_BODY_TOKENS + 200
# Max tokens for OpenAI chunking (body + metadata overhead)
MAX_CHUNK_TOKENS = CHUNK_BODY_TOKENS + 200