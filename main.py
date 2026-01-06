from src.scraper import *
from src.uploader import *

if __name__ == "__main__":
    changed_articles = scraper()
    uploader(changed_articles=changed_articles)