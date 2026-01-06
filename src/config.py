import re

RAW_DATA_BASE_URL="support.optisigns.com"
CHUNK_NAME_FORMAT = re.compile(r'^(\d+)-.*-part\d+\.md$')
MAX_ARTICLES_IN_DEVELOPMENT=50