import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.uploader import (
    delete_old_files,
    upload_added_articles,
    upload_updated_articles,
    uploader
)

class TestDeleteOldFiles:
    def test_deletes_all_files_successfully(self, mock_openai_client):
        file_ids = ["file-1", "file-2", "file-3"]
        vector_store_id = "vs_test123"
        
        delete_old_files(mock_openai_client, vector_store_id, file_ids)
        
        assert mock_openai_client.vector_stores.files.delete.call_count == 3
        assert mock_openai_client.files.delete.call_count == 3
        
        mock_openai_client.vector_stores.files.delete.assert_any_call(
            vector_store_id=vector_store_id,
            file_id="file-1"
        )

    def test_handles_vector_store_delete_error(self, mock_openai_client):
        mock_openai_client.vector_stores.files.delete.side_effect = Exception("API Error")
        
        file_ids = ["file-error"]
        vector_store_id = "vs_test123"
        
        delete_old_files(mock_openai_client, vector_store_id, file_ids)
        
        assert mock_openai_client.files.delete.called

    def test_handles_file_storage_delete_error(self, mock_openai_client):
        mock_openai_client.files.delete.side_effect = Exception("Storage Error")
        
        file_ids = ["file-error"]
        vector_store_id = "vs_test123"
        
        delete_old_files(mock_openai_client, vector_store_id, file_ids)
        
        assert mock_openai_client.vector_stores.files.delete.called

    def test_handles_empty_file_list(self, mock_openai_client):
        delete_old_files(mock_openai_client, "vs_test", [])
        
        assert not mock_openai_client.vector_stores.files.delete.called
        assert not mock_openai_client.files.delete.called

    def test_continues_on_partial_failure(self, mock_openai_client):
        def side_effect_delete(*args, **kwargs):
            if kwargs.get('file_id') == 'file-2':
                raise Exception("Delete failed")
        
        mock_openai_client.vector_stores.files.delete.side_effect = side_effect_delete
        
        file_ids = ["file-1", "file-2", "file-3"]
        delete_old_files(mock_openai_client, "vs_test", file_ids)
        
        assert mock_openai_client.vector_stores.files.delete.call_count == 3

class TestUploadAddedArticles:
    def test_returns_empty_dict_for_no_articles(self, mock_openai_client):
        result = upload_added_articles(mock_openai_client, "vs_test", {})
        
        assert result == {}
        assert not mock_openai_client.files.create.called

    def test_uploads_single_article_single_chunk(self, mock_openai_client, sample_chunk_files):
        added_articles = {"456": sample_chunk_files["456"]}
        
        result = upload_added_articles(mock_openai_client, "vs_test", added_articles)
        
        assert "456" in result
        assert len(result["456"]) == 1
        assert mock_openai_client.files.create.call_count == 1

    def test_uploads_single_article_multiple_chunks(self, mock_openai_client, sample_chunk_files):
        added_articles = {"123": sample_chunk_files["123"]}
        
        result = upload_added_articles(mock_openai_client, "vs_test", added_articles)
        
        assert "123" in result
        assert len(result["123"]) == 2
        assert mock_openai_client.files.create.call_count == 2

    def test_uploads_multiple_articles(self, mock_openai_client, sample_chunk_files):
        result = upload_added_articles(
            mock_openai_client,
            "vs_test",
            sample_chunk_files
        )
        
        assert "123" in result
        assert "456" in result
        assert mock_openai_client.files.create.call_count == 3

    @patch('src.uploader.BATCH_SIZE', 2)
    def test_batches_files_correctly(self, mock_openai_client, sample_chunk_files):
        file_counter = [0]
        
        def create_file_mock(*args, **kwargs):
            file_counter[0] += 1
            file_obj = MagicMock()
            file_obj.id = f"file-{file_counter[0]}"
            return file_obj
        
        mock_openai_client.files.create.side_effect = create_file_mock
        
        result = upload_added_articles(
            mock_openai_client,
            "vs_test",
            sample_chunk_files
        )
        
        assert mock_openai_client.vector_stores.file_batches.create_and_poll.call_count == 2
        
        calls = mock_openai_client.vector_stores.file_batches.create_and_poll.call_args_list
        assert len(calls[0][1]['file_ids']) == 2
        assert len(calls[1][1]['file_ids']) == 1

    def test_uses_correct_chunking_strategy(self, mock_openai_client, sample_chunk_files):
        added_articles = {"456": sample_chunk_files["456"]}
        
        upload_added_articles(mock_openai_client, "vs_test", added_articles)
        
        call_args = mock_openai_client.vector_stores.file_batches.create_and_poll.call_args
        chunking_strategy = call_args[1]['chunking_strategy']
        
        assert chunking_strategy['type'] == 'static'
        assert chunking_strategy['static']['chunk_overlap_tokens'] == 0

    def test_handles_file_upload_error(self, mock_openai_client, sample_chunk_files):
        mock_openai_client.files.create.side_effect = [
            MagicMock(id="file-1"),
            Exception("Upload failed"),
            MagicMock(id="file-3")
        ]
        
        result = upload_added_articles(
            mock_openai_client,
            "vs_test",
            sample_chunk_files
        )
        
        assert isinstance(result, dict)

    def test_handles_batch_creation_error(self, mock_openai_client, sample_chunk_files):
        mock_openai_client.vector_stores.file_batches.create_and_poll.side_effect = Exception("Batch error")
        
        result = upload_added_articles(
            mock_openai_client,
            "vs_test",
            sample_chunk_files
        )
        
        assert isinstance(result, dict)

class TestUploadUpdatedArticles:
    def test_returns_empty_dict_for_no_updates(self, mock_openai_client, empty_hash_store):
        result = upload_updated_articles(
            mock_openai_client,
            "vs_test",
            {},
            empty_hash_store
        )
        
        assert result == {}

    def test_deletes_old_files_before_upload(self, mock_openai_client, sample_chunk_files, hash_store_with_files):
        updated_articles = {"123": sample_chunk_files["123"]}
        
        upload_updated_articles(
            mock_openai_client,
            "vs_test",
            updated_articles,
            hash_store_with_files
        )
        
        assert mock_openai_client.vector_stores.files.delete.call_count == 2
        mock_openai_client.vector_stores.files.delete.assert_any_call(
            vector_store_id="vs_test",
            file_id="file-old1"
        )
        mock_openai_client.vector_stores.files.delete.assert_any_call(
            vector_store_id="vs_test",
            file_id="file-old2"
        )

    def test_uploads_new_files_after_deletion(self, mock_openai_client, sample_chunk_files, hash_store_with_files):
        updated_articles = {"123": sample_chunk_files["123"]}
        
        result = upload_updated_articles(
            mock_openai_client,
            "vs_test",
            updated_articles,
            hash_store_with_files
        )
        
        assert "123" in result
        assert mock_openai_client.files.create.called

    def test_handles_article_without_old_files(self, mock_openai_client, sample_chunk_files, empty_hash_store):
        updated_articles = {"456": sample_chunk_files["456"]}
        
        result = upload_updated_articles(
            mock_openai_client,
            "vs_test",
            updated_articles,
            empty_hash_store
        )
        
        assert "456" in result
        assert not mock_openai_client.vector_stores.files.delete.called

class TestUploaderIntegration:
    @patch('src.uploader.OpenAI')
    @patch('src.uploader.save_hash_store')
    @patch('src.uploader.load_hash_store')
    @patch('src.uploader.Path')
    def test_successful_upload_workflow(self, mock_path_class, mock_load, mock_save, mock_openai_class, sample_chunk_files, temp_directories):
        mock_path_instance = MagicMock()
        mock_path_instance.parent.parent = temp_directories["base_dir"]
        mock_path_class.return_value = mock_path_instance
        
        hash_store_with_articles = {
            "articles": {
                "123": {"hash": "hash123", "openai_file_ids": [], "updated_at": "", "num_chunks": 2},
                "456": {"hash": "hash456", "openai_file_ids": [], "updated_at": "", "num_chunks": 1}
            },
            "last_fetching_time": None
        }
        mock_load.return_value = hash_store_with_articles
        
        mock_client = MagicMock()
        file_obj = MagicMock()
        file_obj.id = "file-new"
        mock_client.files.create.return_value = file_obj
        
        batch_result = MagicMock()
        batch_result.file_counts.completed = 1
        mock_client.vector_stores.file_batches.create_and_poll.return_value = batch_result
        
        mock_openai_class.return_value = mock_client
        
        changed_articles = {
            "added": sample_chunk_files,
            "updated": {}
        }
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('src.uploader.VECTOR_STORE_ID', 'vs_test123'):
                uploader(changed_articles)
        
        assert mock_save.called
        assert mock_openai_class.called

    @patch('src.uploader.OpenAI')
    def test_raises_error_without_api_key(self, mock_openai_class):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY not found"):
                uploader({"added": {}, "updated": {}})

    @patch('src.uploader.OpenAI')
    def test_handles_none_input(self, mock_openai_class):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            uploader(None)
        
        assert not mock_openai_class.called

    @patch('src.uploader.OpenAI')
    @patch('src.uploader.load_hash_store')
    @patch('src.uploader.Path')
    def test_handles_empty_changed_articles(self, mock_path_class, mock_load, mock_openai_class, empty_hash_store):
        mock_load.return_value = empty_hash_store
        
        mock_path_instance = MagicMock()
        mock_markdown_dir = MagicMock()
        mock_markdown_dir.exists.return_value = True
        mock_path_instance.parent.parent = MagicMock()
        mock_path_class.return_value = mock_path_instance
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('src.uploader.Path.__truediv__', return_value=mock_markdown_dir):
                uploader({"added": {}, "updated": {}})

    @patch('src.uploader.OpenAI')
    @patch('src.uploader.save_hash_store')
    @patch('src.uploader.load_hash_store')
    @patch('src.uploader.Path')
    def test_updates_hash_store_with_file_ids(self, mock_path_class, mock_load, mock_save, mock_openai_class, sample_chunk_files, temp_directories):
        mock_path_instance = MagicMock()
        mock_path_instance.parent.parent = temp_directories["base_dir"]
        mock_path_class.return_value = mock_path_instance
        
        hash_store_with_article = {
            "articles": {
                "123": {"hash": "hash123", "openai_file_ids": [], "updated_at": "", "num_chunks": 2}
            },
            "last_fetching_time": None
        }
        mock_load.return_value = hash_store_with_article
        
        mock_client = MagicMock()
        file_obj = MagicMock()
        file_obj.id = "file-test"
        mock_client.files.create.return_value = file_obj
        
        batch_result = MagicMock()
        batch_result.file_counts.completed = 1
        mock_client.vector_stores.file_batches.create_and_poll.return_value = batch_result
        
        mock_openai_class.return_value = mock_client
        
        changed_articles = {
            "added": {"123": sample_chunk_files["123"]},
            "updated": {}
        }
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('src.uploader.VECTOR_STORE_ID', 'vs_test'):
                uploader(changed_articles)
        
        saved_hash_store = mock_save.call_args[0][0]
        assert "123" in saved_hash_store["articles"]
        assert "openai_file_ids" in saved_hash_store["articles"]["123"]

    @patch('src.uploader.OpenAI')
    @patch('src.uploader.save_hash_store')
    @patch('src.uploader.load_hash_store')
    @patch('src.uploader.Path')
    def test_handles_mixed_added_and_updated(self, mock_path_class, mock_load, mock_save, mock_openai_class, sample_chunk_files, temp_directories):
        mock_path_instance = MagicMock()
        mock_path_instance.parent.parent = temp_directories["base_dir"]
        mock_path_class.return_value = mock_path_instance
        
        hash_store_both = {
            "articles": {
                "123": {
                    "hash": "oldhash123",
                    "openai_file_ids": ["file-old1", "file-old2"],
                    "updated_at": "2024-01-15T10:30:00Z",
                    "num_chunks": 2
                },
                "456": {"hash": "hash456", "openai_file_ids": [], "updated_at": "", "num_chunks": 1}
            },
            "last_fetching_time": 1705315800
        }
        mock_load.return_value = hash_store_both
        
        mock_client = MagicMock()
        file_obj = MagicMock()
        file_obj.id = "file-new"
        mock_client.files.create.return_value = file_obj
        
        batch_result = MagicMock()
        batch_result.file_counts.completed = 1
        mock_client.vector_stores.file_batches.create_and_poll.return_value = batch_result
        
        mock_openai_class.return_value = mock_client
        
        changed_articles = {
            "added": {"456": sample_chunk_files["456"]},
            "updated": {"123": sample_chunk_files["123"]}
        }
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('src.uploader.VECTOR_STORE_ID', 'vs_test'):
                uploader(changed_articles)
        
        assert mock_client.vector_stores.files.delete.called
        assert mock_save.called

class TestEdgeCases:
    def test_file_read_error_during_upload(self, mock_openai_client, temp_directories):
        markdown_dir = temp_directories["markdown_dir"]
        
        corrupted_file = markdown_dir / "corrupted.md"
        corrupted_file.write_text("Some content")
        
        with patch('builtins.open', side_effect=IOError("Cannot read file")):
            added_articles = {"999": [corrupted_file]}
            
            result = upload_added_articles(
                mock_openai_client,
                "vs_test",
                added_articles
            )
            
            assert isinstance(result, dict)

    @patch('src.uploader.BATCH_SIZE', 1)
    def test_large_number_of_files(self, mock_openai_client, temp_directories):
        markdown_dir = temp_directories["markdown_dir"]
        
        chunks = []
        for i in range(10):
            chunk = markdown_dir / f"article-{i}-part1.md"
            chunk.write_text(f"Content {i}")
            chunks.append(chunk)
        
        added_articles = {str(i): [chunks[i]] for i in range(10)}
        
        result = upload_added_articles(
            mock_openai_client,
            "vs_test",
            added_articles
        )
        
        assert len(result) == 10
        assert mock_openai_client.vector_stores.file_batches.create_and_poll.call_count == 10

    def test_delete_with_nonexistent_file_ids(self, mock_openai_client):
        mock_openai_client.vector_stores.files.delete.side_effect = Exception("File not found")
        
        delete_old_files(mock_openai_client, "vs_test", ["nonexistent-id"])
        
        assert mock_openai_client.vector_stores.files.delete.called
