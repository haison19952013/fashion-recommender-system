import json
import os
import tempfile
from unittest.mock import Mock, mock_open, patch

import pytest
import requests

from data_pipeline.crawl_data import fetch_image, get_keys
from utils.utils import key_to_url

# Test data directory path
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data_test')


class TestGetKeys:
    @patch('os.path.exists')
    def test_get_keys_valid_data(self, mock_exists):
        """Test get_keys with valid JSON data."""
        mock_exists.return_value = True
        test_data = [
            '{"product": "abc123", "scene": "def456"}\n',
            '{"product": "ghi789", "scene": "jkl012"}\n',
            '{"product": "abc123", "scene": "mno345"}\n'  # duplicate product
        ]
        
        with patch("builtins.open", mock_open(read_data="".join(test_data))):
            keys = get_keys("dummy_file.json", 10)
            
        assert len(keys) == 5  # 3 products + 3 scenes - 1 duplicate = 5 unique
        assert "abc123" in keys
        assert "def456" in keys
        assert "ghi789" in keys

    @patch('os.path.exists')
    def test_get_keys_max_lines(self, mock_exists):
        """Test get_keys respects max_lines parameter."""
        mock_exists.return_value = True
        test_data = [
            '{"product": "abc123", "scene": "def456"}\n',
            '{"product": "ghi789", "scene": "jkl012"}\n',
            '{"product": "mno345", "scene": "pqr678"}\n'
        ]
        
        with patch("builtins.open", mock_open(read_data="".join(test_data))):
            keys = get_keys("dummy_file.json", 2)  # Only read first 2 lines
            
        assert len(keys) == 4  # Only keys from first 2 lines
        assert "abc123" in keys
        assert "def456" in keys
        assert "ghi789" in keys
        assert "jkl012" in keys
        assert "mno345" not in keys

    @patch('os.path.exists')
    def test_get_keys_invalid_json(self, mock_exists):
        """Test get_keys handles invalid JSON gracefully."""
        mock_exists.return_value = True
        test_data = [
            '{"product": "abc123", "scene": "def456"}\n',
            'invalid json line\n',
            '{"product": "ghi789", "scene": "jkl012"}\n'
        ]
        
        with patch("builtins.open", mock_open(read_data="".join(test_data))):
            keys = get_keys("dummy_file.json", 10)
            
        # Should skip invalid line and continue
        assert "abc123" in keys
        assert "def456" in keys
        assert "ghi789" in keys
        assert "jkl012" in keys

    def test_get_keys_file_not_found(self):
        """Test get_keys raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            get_keys("nonexistent_file.json", 10)


class TestKeyToUrl:
    def test_key_to_url_valid(self):
        """Test key_to_url with valid hex key."""
        key = "abcdef123456"
        expected = "https://i.pinimg.com/400x/ab/cd/ef/abcdef123456.jpg"
        assert key_to_url(key) == expected

    def test_key_to_url_short_key(self):
        """Test key_to_url raises ValueError for short key."""
        with pytest.raises(ValueError, match="must be at least 6 characters"):
            key_to_url("abc")

    def test_key_to_url_invalid_hex(self):
        """Test key_to_url raises ValueError for non-hex characters."""
        with pytest.raises(ValueError, match="must be hexadecimal"):
            key_to_url("ghijkl123456")

    def test_key_to_url_empty(self):
        """Test key_to_url raises ValueError for empty key."""
        with pytest.raises(ValueError, match="must be at least 6 characters"):
            key_to_url("")


class TestFetchImage:
    @patch('utils.utils.key_to_url')
    @patch('requests.get')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_fetch_image_success(self, mock_makedirs, mock_exists, mock_get, mock_key_to_url):
        """Test successful image fetch."""
        # Setup mocks
        mock_exists.return_value = False  # File doesn't exist yet
        mock_key_to_url.return_value = "https://example.com/test.jpg"
        mock_response = Mock()
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.content = b'fake image data'
        mock_get.return_value = mock_response
        
        with patch("builtins.open", mock_open()) as mock_file:
            result = fetch_image("test123", "/output", 1.0, 1)
            
        assert result is True
        expected_path = os.path.join("/output", "test123.jpg")
        mock_file.assert_called_once_with(expected_path, "wb")
        mock_file().write.assert_called_once_with(b'fake image data')

    @patch('requests.get')
    @patch('os.path.exists')
    def test_fetch_image_already_exists(self, mock_exists, mock_get):
        """Test fetch_image returns False when image already exists."""
        mock_exists.return_value = True
        
        result = fetch_image("test123", "/output", 1.0, 1)
        
        assert result is False
        mock_get.assert_not_called()

    @patch('utils.utils.key_to_url')
    @patch('requests.get')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_fetch_image_network_error(self, mock_makedirs, mock_exists, mock_get, mock_key_to_url):
        """Test fetch_image handles network errors."""
        mock_exists.return_value = False
        mock_key_to_url.return_value = "https://example.com/test.jpg"
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        result = fetch_image("test123", "/output", 0.1, 2)  # Short sleep for faster test
        
        assert result is False
        assert mock_get.call_count == 2  # Should retry once

    @patch('utils.utils.key_to_url')
    @patch('requests.get')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_fetch_image_invalid_content_type(self, mock_makedirs, mock_exists, mock_get, mock_key_to_url):
        """Test fetch_image rejects non-image content."""
        mock_exists.return_value = False
        mock_key_to_url.return_value = "https://example.com/test.jpg"
        mock_response = Mock()
        mock_response.headers = {'content-type': 'text/html'}
        mock_get.return_value = mock_response
        
        result = fetch_image("test123", "/output", 1.0, 1)
        
        assert result is False


class TestIntegrationWithRealData:
    """Integration tests using real data samples from the data folder."""
    
    def test_get_keys_with_fashion_data(self):
        """Test get_keys with real fashion.json data."""
        fashion_file = os.path.join(DATA_DIR, 'fashion.json')
        
        if not os.path.exists(fashion_file):
            pytest.skip(f"Real data file not found: {fashion_file}")
        
        # Test with small number of lines for speed
        keys = get_keys(fashion_file, 10)
        
        # Verify we got keys
        assert len(keys) > 0
        assert len(keys) <= 20  # Max 20 keys from 10 lines (10 products + 10 scenes)
        
        # Check that all keys are hex strings (Pinterest format)
        for key in keys:
            assert isinstance(key, str)
            assert len(key) >= 6  # Pinterest keys should be at least 6 chars
            assert all(c in '0123456789abcdefABCDEF' for c in key)
    
    def test_key_to_url_with_real_keys(self):
        """Test key_to_url with real Pinterest keys from data."""
        fashion_file = os.path.join(DATA_DIR, 'fashion.json')
        
        if not os.path.exists(fashion_file):
            pytest.skip(f"Real data file not found: {fashion_file}")
        
        # Get a few real keys
        keys = get_keys(fashion_file, 2)
        
        for key in list(keys)[:3]:  # Test first 3 keys
            url = key_to_url(key)
            
            # Verify URL format
            assert url.startswith('https://i.pinimg.com/400x/')
            assert url.endswith(f'/{key}.jpg')
            assert f'/{key[0:2]}/{key[2:4]}/{key[4:6]}/' in url
    
    @patch('requests.get')
    def test_fetch_image_integration_flow(self, mock_get):
        """Test fetch_image with real key but mocked network request."""
        fashion_file = os.path.join(DATA_DIR, 'fashion.json')
        
        if not os.path.exists(fashion_file):
            pytest.skip(f"Real data file not found: {fashion_file}")
        
        # Get a real key
        keys = get_keys(fashion_file, 1)
        real_key = list(keys)[0]
        
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.content = b'fake image data'
        mock_get.return_value = mock_response
        
        # Use a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            result = fetch_image(real_key, temp_dir, 0.1, 1)
            
            # Should succeed
            assert result is True
            
            # Check file was created
            expected_file = os.path.join(temp_dir, f"{real_key}.jpg")
            assert os.path.exists(expected_file)
            
            # Check file content
            with open(expected_file, 'rb') as f:
                content = f.read()
                assert content == b'fake image data'
    
    def test_data_file_structure(self):
        """Test that the real data files have expected structure."""
        filename = 'fashion.json'
        filepath = os.path.join(DATA_DIR, filename)
        
        if not os.path.exists(filepath):
            pytest.skip(f"Real data file not found: {filepath}")
        
        # Read first line and verify structure
        with open(filepath, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            
        data = json.loads(first_line)
        
        # Verify expected fields
        assert 'product' in data
        assert 'scene' in data
        assert 'bbox' in data
        
        # Verify data types
        assert isinstance(data['product'], str)
        assert isinstance(data['scene'], str)
        assert isinstance(data['bbox'], list)
        assert len(data['bbox']) == 4  # Should be [x, y, w, h]


if __name__ == "__main__":
    pytest.main([__file__])