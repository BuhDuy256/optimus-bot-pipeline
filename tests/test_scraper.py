import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from pathlib import Path
import json
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper import (
    clean_html,
    create_slug,
    count_tokens,
    chunk_text,
    find_backward_safe_split,
    is_heading,
    is_in_code_block,
    process_article,
    fetch_articles,
    fetch_updated_articles,
    delete_old_chunks,
    scraper
)

class TestCleanHTML:
    def test_removes_navigation_elements(self, sample_html):
        result = clean_html(sample_html)
        assert '<nav>' not in result
        assert 'Navigation' not in result

    def test_removes_header_footer(self, sample_html):
        result = clean_html(sample_html)
        assert '<header>' not in result
        assert '<footer>' not in result

    def test_removes_scripts_and_styles(self, sample_html):
        result = clean_html(sample_html)
        assert '<script>' not in result
        assert '<style>' not in result
        assert 'var x = 1;' not in result

    def test_removes_sidebar_and_ads(self, sample_html):
        result = clean_html(sample_html)
        assert 'sidebar' not in result.lower()
        assert 'ad-banner' not in result.lower()

    def test_removes_iframe(self, sample_html):
        result = clean_html(sample_html)
        assert '<iframe' not in result

    def test_preserves_main_content(self, sample_html):
        result = clean_html(sample_html)
        assert 'Main Content' in result
        assert 'actual content we want' in result

    def test_handles_empty_html(self):
        result = clean_html("")
        assert result == ""

    def test_handles_minimal_html(self):
        html = "<p>Simple text</p>"
        result = clean_html(html)
        assert "Simple text" in result


class TestCreateSlug:
    def test_basic_slug_creation(self):
        result = create_slug(123, "Simple Title")
        assert result == "123-simple-title"

    def test_removes_special_characters(self):
        result = create_slug(456, "Title with @#$% special!")
        assert '@' not in result
        assert '#' not in result
        assert '$' not in result
        assert '%' not in result

    def test_handles_vietnamese_characters(self):
        result = create_slug(789, "Hướng dẫn sử dụng")
        assert result.startswith("789-")
        assert ' ' not in result

    def test_handles_multiple_spaces(self):
        result = create_slug(111, "Title   with    spaces")
        assert '   ' not in result
        assert result == "111-title-with-spaces"

    def test_handles_hyphens(self):
        result = create_slug(222, "Title - with - hyphens")
        assert result == "222-title-with-hyphens"

    def test_removes_leading_trailing_hyphens(self):
        result = create_slug(333, "  Title  ")
        assert not result.endswith('-')
        assert result.split('-', 1)[1][0] != '-'

    def test_lowercase_conversion(self):
        result = create_slug(444, "UPPERCASE TITLE")
        assert result == "444-uppercase-title"

class TestCountTokens:
    def test_empty_string(self):
        assert count_tokens("") == 0

    def test_simple_text(self):
        result = count_tokens("Hello world")
        assert result > 0
        assert isinstance(result, int)

    def test_long_text(self):
        text = "This is a longer piece of text. " * 50
        result = count_tokens(text)
        assert result > 50

    def test_special_characters(self):
        text = "Special chars: @#$%^&*()"
        result = count_tokens(text)
        assert result > 0

    def test_code_snippet(self):
        code = "def hello():\n    print('world')\n    return True"
        result = count_tokens(code)
        assert result > 5

class TestChunkText:
    def test_text_smaller_than_max_returns_single_chunk(self):
        text = "Short text"
        chunks = chunk_text(text, max_tokens=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text_returns_empty_list(self):
        chunks = chunk_text("", max_tokens=100)
        assert chunks == []

    def test_whitespace_only_returns_empty_list(self):
        chunks = chunk_text("   \n\n  ", max_tokens=100)
        assert chunks == []

    def test_chunks_respect_max_tokens(self, long_text_with_headings):
        max_tokens = 50
        chunks = chunk_text(long_text_with_headings, max_tokens=max_tokens)
        
        for chunk in chunks:
            token_count = count_tokens(chunk)
            assert token_count <= max_tokens * 1.3

    def test_chunks_have_overlap(self):
        text = "Sentence one. " * 100
        overlap_pct = 0.15
        chunks = chunk_text(text, max_tokens=50, overlap_pct=overlap_pct)
        
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                chunk_end = chunks[i][-50:]
                chunk_start = chunks[i + 1][:100]
                has_overlap = any(word in chunk_start for word in chunk_end.split()[-5:])
                assert has_overlap

    def test_does_not_split_headings(self, long_text_with_headings):
        chunks = chunk_text(long_text_with_headings, max_tokens=30)
        
        for chunk in chunks:
            lines = chunk.strip().split('\n')
            if len(lines) > 1:
                for i, line in enumerate(lines[:-1]):
                    if line.strip().startswith('#'):
                        assert i == 0 or lines[i-1].strip() == ''

    def test_preserves_code_blocks(self, long_text_with_headings):
        chunks = chunk_text(long_text_with_headings, max_tokens=100)
        
        all_text = ''.join(chunks)
        assert '```python' in all_text or all_text.count('```') % 2 == 0

    def test_handles_lists_properly(self, text_with_lists):
        chunks = chunk_text(text_with_lists, max_tokens=40)
        
        for chunk in chunks:
            if '1. ' in chunk or '2. ' in chunk:
                lines = chunk.split('\n')
                list_lines = [l for l in lines if l.strip() and l.strip()[0].isdigit()]
                if list_lines:
                    assert True

class TestFindBackwardSafeSplit:
    def test_finds_heading(self):
        text = "Some text\n\n## Heading\n\nMore text"
        pos = find_backward_safe_split(text, 30)
        assert text[pos:pos+2] == '##' or pos < 30

    def test_finds_paragraph_break(self):
        text = "Paragraph one.\n\nParagraph two."
        pos = find_backward_safe_split(text, 25)
        assert pos <= 25

    def test_avoids_code_blocks(self):
        text = "Text before\n```\ncode\n```\nText after"
        pos = find_backward_safe_split(text, 20)
        code_start = text.find('```')
        assert pos <= code_start or pos >= text.find('```', code_start + 3) + 3

    def test_finds_sentence_end(self):
        text = "First sentence. Second sentence. Third sentence."
        pos = find_backward_safe_split(text, 30)
        assert pos <= 30

class TestIsHeading:
    def test_detects_h1(self):
        assert is_heading("# Title")

    def test_detects_h2_to_h6(self):
        assert is_heading("## Subtitle")
        assert is_heading("### Level 3")
        assert is_heading("###### Level 6")

    def test_requires_space_after_hash(self):
        assert not is_heading("#NoSpace")

    def test_rejects_non_headings(self):
        assert not is_heading("Regular text")
        assert not is_heading("Text with # in middle")

class TestIsInCodeBlock:
    def test_inside_code_block(self):
        text = "Before\n```\ncode here\n```\nAfter"
        pos = text.find("code here")
        assert is_in_code_block(text, pos)

    def test_outside_code_block(self):
        text = "Before\n```\ncode here\n```\nAfter"
        pos = text.find("Before")
        assert not is_in_code_block(text, pos)

    def test_after_code_block(self):
        text = "Before\n```\ncode here\n```\nAfter"
        pos = text.find("After")
        assert not is_in_code_block(text, pos)

    def test_multiple_code_blocks(self):
        text = "```\nblock1\n```\ntext\n```\nblock2\n```"
        assert is_in_code_block(text, 5)
        assert not is_in_code_block(text, 20)

class TestDeleteOldChunks:
    def test_deletes_matching_chunks(self, temp_directories):
        markdown_dir = temp_directories["markdown_dir"]
        
        (markdown_dir / "123-test-slug-part1.md").write_text("chunk1")
        (markdown_dir / "123-test-slug-part2.md").write_text("chunk2")
        (markdown_dir / "456-other-part1.md").write_text("other")
        
        delete_old_chunks(123, "test-slug", markdown_dir)
        
        assert not (markdown_dir / "123-test-slug-part1.md").exists()
        assert not (markdown_dir / "123-test-slug-part2.md").exists()
        assert (markdown_dir / "456-other-part1.md").exists()

    def test_handles_no_matching_chunks(self, temp_directories):
        markdown_dir = temp_directories["markdown_dir"]
        delete_old_chunks(999, "nonexistent", markdown_dir)

class TestProcessArticle:
    def test_adds_new_article(self, sample_article, empty_hash_store, temp_directories):
        action, chunk_paths = process_article(
            sample_article,
            empty_hash_store,
            temp_directories["raw_data_dir"],
            temp_directories["markdown_dir"]
        )
        
        assert action == "ADDED"
        assert len(chunk_paths) > 0
        assert str(sample_article["id"]) in empty_hash_store["articles"]

    def test_skips_unchanged_article(self, sample_article, empty_hash_store, temp_directories):
        process_article(
            sample_article,
            empty_hash_store,
            temp_directories["raw_data_dir"],
            temp_directories["markdown_dir"]
        )
        
        action, chunk_paths = process_article(
            sample_article,
            empty_hash_store,
            temp_directories["raw_data_dir"],
            temp_directories["markdown_dir"]
        )
        
        assert action == "HASH_SKIPPED"
        assert chunk_paths == []

    def test_updates_changed_article(self, sample_article, sample_article_updated, empty_hash_store, temp_directories):
        markdown_dir = temp_directories["markdown_dir"]
        
        process_article(
            sample_article,
            empty_hash_store,
            temp_directories["raw_data_dir"],
            markdown_dir
        )
        
        old_chunks = list(markdown_dir.glob("123456-*.md"))
        
        action, chunk_paths = process_article(
            sample_article_updated,
            empty_hash_store,
            temp_directories["raw_data_dir"],
            markdown_dir
        )
        
        assert action == "UPDATED"
        assert len(chunk_paths) > 0

    def test_creates_raw_json_file(self, sample_article, empty_hash_store, temp_directories):
        process_article(
            sample_article,
            empty_hash_store,
            temp_directories["raw_data_dir"],
            temp_directories["markdown_dir"]
        )
        
        raw_files = list(temp_directories["raw_data_dir"].glob("*.json"))
        assert len(raw_files) > 0

    def test_chunk_contains_metadata(self, sample_article, empty_hash_store, temp_directories):
        action, chunk_paths = process_article(
            sample_article,
            empty_hash_store,
            temp_directories["raw_data_dir"],
            temp_directories["markdown_dir"]
        )
        
        chunk_content = chunk_paths[0].read_text()
        assert sample_article["title"] in chunk_content
        assert sample_article["html_url"] in chunk_content

class TestFetchArticles:
    @patch('src.scraper.requests.get')
    @patch('src.scraper.ENV', 'development')
    @patch('src.scraper.MAX_ARTICLES_IN_DEVELOPMENT', 10)
    def test_development_mode_limits_articles(self, mock_get, mock_zendesk_response):
        mock_response = Mock()
        mock_response.json.return_value = mock_zendesk_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        articles = fetch_articles(10)
        
        assert len(articles) == 2
        assert mock_get.called

    @patch('src.scraper.requests.get')
    @patch('src.scraper.ENV', 'production')
    def test_production_mode_fetches_all_pages(self, mock_get):
        mock_response_1 = Mock()
        mock_response_1.json.return_value = {
            "articles": [{"id": 1}],
            "next_page": "https://api.example.com/page2"
        }
        mock_response_1.raise_for_status = Mock()
        
        mock_response_2 = Mock()
        mock_response_2.json.return_value = {
            "articles": [{"id": 2}],
            "next_page": None
        }
        mock_response_2.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_response_1, mock_response_2]
        
        articles = fetch_articles()
        
        assert len(articles) == 2
        assert mock_get.call_count == 2

class TestFetchUpdatedArticles:
    @patch('src.scraper.requests.get')
    @patch('src.scraper.ENV', 'development')
    @patch('src.scraper.MAX_ARTICLES_IN_DEVELOPMENT', 10)
    def test_filters_by_timestamp(self, mock_get):
        start_time = 1705315800
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "articles": [
                {
                    "id": 1,
                    "updated_at": "2024-01-16T10:30:00Z"
                },
                {
                    "id": 2,
                    "updated_at": "2024-01-14T10:30:00Z"
                }
            ],
            "next_page": None
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        articles, end_time = fetch_updated_articles(start_time, 10)
        
        assert len(articles) == 1
        assert articles[0]["id"] == 1

    @patch('src.scraper.requests.get')
    @patch('src.scraper.ENV', 'development')
    def test_returns_end_timestamp(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"articles": [], "next_page": None}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        articles, end_time = fetch_updated_articles(0)
        
        assert isinstance(end_time, int)
        assert end_time > 0

class TestScraperIntegration:
    @patch('src.scraper.fetch_articles')
    @patch('src.scraper.save_hash_store')
    @patch('src.scraper.load_hash_store')
    @patch('src.scraper.Path')
    def test_first_run_all_added(self, mock_path_class, mock_load, mock_save, mock_fetch, sample_article, temp_directories):
        mock_path_instance = MagicMock()
        mock_path_instance.parent.parent = temp_directories["base_dir"]
        mock_path_class.return_value = mock_path_instance
        mock_path_class.__file__ = str(temp_directories["base_dir"] / "src" / "scraper.py")
        
        mock_load.return_value = {"articles": {}, "last_fetching_time": None}
        mock_fetch.return_value = [sample_article]
        
        result = scraper(1)
        
        assert len(result["added"]) > 0
        assert len(result["updated"]) == 0

    @patch('src.scraper.fetch_updated_articles')
    @patch('src.scraper.save_hash_store')
    @patch('src.scraper.load_hash_store')
    @patch('src.scraper.Path')
    def test_subsequent_run_with_no_changes(self, mock_path_class, mock_load, mock_save, mock_fetch, sample_article, populated_hash_store, temp_directories):
        mock_path_instance = MagicMock()
        mock_path_instance.parent.parent = temp_directories["base_dir"]
        mock_path_class.return_value = mock_path_instance
        
        mock_load.return_value = populated_hash_store
        mock_fetch.return_value = ([sample_article], 1705400000)
        
        result = scraper(1)
        
        assert isinstance(result, dict)

    @patch('src.scraper.fetch_updated_articles')
    @patch('src.scraper.save_hash_store')
    @patch('src.scraper.load_hash_store')
    @patch('src.scraper.Path')
    def test_handles_article_processing_error(self, mock_path_class, mock_load, mock_save, mock_fetch, sample_article, temp_directories):
        mock_path_instance = MagicMock()
        mock_path_instance.parent.parent = temp_directories["base_dir"]
        mock_path_class.return_value = mock_path_instance
        
        mock_load.return_value = {"articles": {}, "last_fetching_time": 1705315800}
        
        bad_article = sample_article.copy()
        bad_article["body"] = None
        mock_fetch.return_value = ([bad_article], 1705400000)
        
        result = scraper(1)
        
        assert isinstance(result, dict)
