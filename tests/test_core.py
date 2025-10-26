"""
Unit tests for bitter_edgar.core

Tests the core business logic (FilingCache, EdgarFetcher) without MCP.
"""
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from edgar_lite_mcp.core import FilingCache, EdgarFetcher, fetch_filing, list_cached_filings


class TestFilingCache:
    """Test FilingCache class."""

    def test_init(self, tmp_path):
        """Test cache initialization."""
        cache = FilingCache(str(tmp_path))
        assert cache.cache_dir == tmp_path

    def test_ensure_dir(self, tmp_path):
        """Test directory creation."""
        cache = FilingCache(str(tmp_path))
        path = cache.ensure_dir("TSLA", "10-K")
        assert path == tmp_path / "TSLA" / "10-K"
        assert path.exists()

    def test_get_path(self, tmp_path):
        """Test path generation."""
        cache = FilingCache(str(tmp_path))
        path = cache.get_path("TSLA", "10-K", "2024-01-30", "markdown")
        assert path == tmp_path / "TSLA" / "10-K" / "2024-01-30.md"

    def test_get_path_formats(self, tmp_path):
        """Test different format extensions."""
        cache = FilingCache(str(tmp_path))

        md_path = cache.get_path("TSLA", "10-K", "2024-01-30", "markdown")
        assert md_path.suffix == ".md"

        txt_path = cache.get_path("TSLA", "10-K", "2024-01-30", "text")
        assert txt_path.suffix == ".txt"

        html_path = cache.get_path("TSLA", "10-K", "2024-01-30", "html")
        assert html_path.suffix == ".html"

    def test_is_cached(self, tmp_path):
        """Test cache check."""
        cache = FilingCache(str(tmp_path))

        # Not cached yet
        assert not cache.is_cached("TSLA", "10-K", "2024-01-30")

        # Create file
        path = cache.get_path("TSLA", "10-K", "2024-01-30", "markdown")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test content")

        # Now cached
        assert cache.is_cached("TSLA", "10-K", "2024-01-30")

    def test_save(self, tmp_path):
        """Test saving content."""
        cache = FilingCache(str(tmp_path))
        content = "Test filing content"

        path = cache.save("TSLA", "10-K", "2024-01-30", content, "markdown")

        assert path.exists()
        assert path.read_text() == content
        assert path == tmp_path / "TSLA" / "10-K" / "2024-01-30.md"

    def test_list_cached_empty(self, tmp_path):
        """Test listing when cache is empty."""
        cache = FilingCache(str(tmp_path))
        filings = cache.list_cached()
        assert filings == []

    def test_list_cached_single(self, tmp_path):
        """Test listing single filing."""
        cache = FilingCache(str(tmp_path))
        cache.save("TSLA", "10-K", "2024-01-30", "content", "markdown")

        filings = cache.list_cached()
        assert len(filings) == 1
        assert filings[0]["ticker"] == "TSLA"
        assert filings[0]["form_type"] == "10-K"
        assert filings[0]["filing_date"] == "2024-01-30"
        assert filings[0]["format"] == "md"

    def test_list_cached_multiple(self, tmp_path):
        """Test listing multiple filings."""
        cache = FilingCache(str(tmp_path))
        cache.save("TSLA", "10-K", "2024-01-30", "content1", "markdown")
        cache.save("TSLA", "10-Q", "2024-04-30", "content2", "markdown")
        cache.save("AAPL", "10-K", "2024-11-01", "content3", "markdown")

        filings = cache.list_cached()
        assert len(filings) == 3

    def test_list_cached_ticker_filter(self, tmp_path):
        """Test filtering by ticker."""
        cache = FilingCache(str(tmp_path))
        cache.save("TSLA", "10-K", "2024-01-30", "content1", "markdown")
        cache.save("AAPL", "10-K", "2024-11-01", "content2", "markdown")

        filings = cache.list_cached(ticker="TSLA")
        assert len(filings) == 1
        assert filings[0]["ticker"] == "TSLA"

    def test_list_cached_form_filter(self, tmp_path):
        """Test filtering by form type."""
        cache = FilingCache(str(tmp_path))
        cache.save("TSLA", "10-K", "2024-01-30", "content1", "markdown")
        cache.save("TSLA", "10-Q", "2024-04-30", "content2", "markdown")

        filings = cache.list_cached(form_type="10-K")
        assert len(filings) == 1
        assert filings[0]["form_type"] == "10-K"

    def test_get_disk_usage_empty(self, tmp_path):
        """Test disk usage for empty cache."""
        cache = FilingCache(str(tmp_path))
        usage = cache.get_disk_usage()
        assert usage == 0

    def test_get_disk_usage(self, tmp_path):
        """Test disk usage calculation."""
        cache = FilingCache(str(tmp_path))
        cache.save("TSLA", "10-K", "2024-01-30", "x" * 1000, "markdown")

        usage = cache.get_disk_usage()
        assert usage >= 1000  # At least 1000 bytes


class TestEdgarFetcher:
    """Test EdgarFetcher class."""

    def test_init(self):
        """Test fetcher initialization."""
        with patch('bitter_edgar.core.set_identity') as mock_set:
            fetcher = EdgarFetcher("test@example.com")
            mock_set.assert_called_once_with("test@example.com")

    def test_get_company(self):
        """Test company lookup."""
        with patch('bitter_edgar.core.set_identity'):
            fetcher = EdgarFetcher()

        with patch('bitter_edgar.core.Company') as mock_company:
            mock_company.return_value = MagicMock()
            company = fetcher.get_company("TSLA")
            mock_company.assert_called_once_with("TSLA")

    def test_fetch_latest_no_filings(self):
        """Test when no filings found."""
        with patch('bitter_edgar.core.set_identity'):
            fetcher = EdgarFetcher()

        mock_company = MagicMock()
        mock_company.get_filings.return_value = []

        with patch.object(fetcher, 'get_company', return_value=mock_company):
            with pytest.raises(ValueError, match="No 10-K filings found"):
                fetcher.fetch_latest("TSLA", "10-K")

    def test_fetch_latest_success(self):
        """Test successful filing fetch."""
        with patch('bitter_edgar.core.set_identity'):
            fetcher = EdgarFetcher()

        # Mock filing
        mock_filing = MagicMock()
        mock_filing.filing_date = datetime(2024, 1, 30)
        mock_filing.cik = "0001318605"
        mock_filing.form = "10-K"
        mock_filing.accession_number = "0001628280-24-002390"
        mock_filing.url = "https://sec.gov/..."

        # Mock company
        mock_company = MagicMock()
        mock_company.name = "Tesla, Inc."
        mock_company.get_filings.return_value = [mock_filing]

        with patch.object(fetcher, 'get_company', return_value=mock_company):
            result = fetcher.fetch_latest("TSLA", "10-K")

            assert result["company"] == "Tesla, Inc."
            assert result["ticker"] == "TSLA"
            assert result["cik"] == "0001318605"
            assert result["form_type"] == "10-K"
            assert result["filing_date"] == "2024-01-30"
            assert result["filing"] == mock_filing

    def test_fetch_latest_with_date_filter(self):
        """Test date filtering."""
        with patch('bitter_edgar.core.set_identity'):
            fetcher = EdgarFetcher()

        # Mock filings with different dates
        filing1 = MagicMock()
        filing1.filing_date = datetime(2023, 1, 31).date()
        filing1.cik = "0001318605"
        filing1.form = "10-K"
        filing1.accession_number = "123"
        filing1.url = "url1"

        filing2 = MagicMock()
        filing2.filing_date = datetime(2024, 1, 30).date()
        filing2.cik = "0001318605"
        filing2.form = "10-K"
        filing2.accession_number = "456"
        filing2.url = "url2"

        mock_company = MagicMock()
        mock_company.name = "Tesla, Inc."
        mock_company.get_filings.return_value = [filing2, filing1]

        with patch.object(fetcher, 'get_company', return_value=mock_company):
            result = fetcher.fetch_latest("TSLA", "10-K", date="2024-01-01")

            # Should return filing2 (2024-01-30) as it's >= 2024-01-01
            assert result["filing_date"] == "2024-01-30"

    def test_download_content_html(self):
        """Test HTML content download."""
        with patch('bitter_edgar.core.set_identity'):
            fetcher = EdgarFetcher()

        mock_filing = MagicMock()
        mock_filing.html.return_value = "<html>content</html>"

        content, format = fetcher.download_content(mock_filing, "html")
        assert content == "<html>content</html>"
        assert format == "html"

    def test_download_content_text(self):
        """Test text content download."""
        with patch('bitter_edgar.core.set_identity'):
            fetcher = EdgarFetcher()

        mock_filing = MagicMock()
        mock_filing.text.return_value = "text content"

        content, format = fetcher.download_content(mock_filing, "text")
        assert content == "text content"
        assert format == "text"

    def test_download_content_markdown(self):
        """Test markdown conversion."""
        with patch('bitter_edgar.core.set_identity'):
            fetcher = EdgarFetcher()

        mock_filing = MagicMock()
        mock_filing.html.return_value = "<h1>Title</h1>"

        # Patch the import statement, not the module attribute
        with patch('markdownify.markdownify', return_value="# Title"):
            content, format = fetcher.download_content(mock_filing, "markdown")

            assert content == "# Title"
            assert format == "markdown"

    def test_download_content_markdown_fallback(self):
        """Test markdown fallback to text."""
        with patch('bitter_edgar.core.set_identity'):
            fetcher = EdgarFetcher()

        mock_filing = MagicMock()
        mock_filing.text.return_value = "fallback text"
        mock_filing.html.return_value = "<h1>Title</h1>"

        # Simulate ImportError by making the import fail
        with patch.dict('sys.modules', {'markdownify': None}):
            content, format = fetcher.download_content(mock_filing, "markdown")

            assert content == "fallback text"
            assert format == "text"


class TestFetchFiling:
    """Test fetch_filing function (integration)."""

    def test_fetch_filing_cached(self, tmp_path):
        """Test fetching when filing is already cached."""
        # Pre-populate cache
        cache = FilingCache(str(tmp_path))
        cache.save("TSLA", "10-K", "2024-01-30", "cached content", "markdown")

        # Mock EdgarFetcher to avoid SEC API calls
        with patch('bitter_edgar.core.set_identity'):
            with patch('bitter_edgar.core.EdgarFetcher') as mock_fetcher_class:
                mock_fetcher = MagicMock()
                mock_fetcher_class.return_value = mock_fetcher

                # Mock metadata
                metadata = {
                    "filing": MagicMock(),
                    "company": "Tesla, Inc.",
                    "ticker": "TSLA",
                    "cik": "0001318605",
                    "form_type": "10-K",
                    "filing_date": "2024-01-30",
                    "accession_number": "123",
                    "sec_url": "https://sec.gov"
                }
                mock_fetcher.fetch_latest.return_value = metadata

                result = fetch_filing("TSLA", "10-K", cache_dir=str(tmp_path))

        assert result["success"] is True
        assert result["cached"] is True
        assert "cached content" in Path(result["path"]).read_text()

    def test_fetch_filing_download(self, tmp_path):
        """Test downloading new filing."""
        with patch('bitter_edgar.core.set_identity'):
            with patch('bitter_edgar.core.EdgarFetcher') as mock_fetcher_class:
                # Mock fetcher
                mock_fetcher = MagicMock()
                mock_fetcher_class.return_value = mock_fetcher

                # Mock metadata
                mock_filing = MagicMock()
                metadata = {
                    "filing": mock_filing,
                    "company": "Tesla, Inc.",
                    "ticker": "TSLA",
                    "cik": "0001318605",
                    "form_type": "10-K",
                    "filing_date": "2024-01-30",
                    "accession_number": "123",
                    "sec_url": "https://sec.gov"
                }
                mock_fetcher.fetch_latest.return_value = metadata
                mock_fetcher.download_content.return_value = ("filing content", "markdown")

                result = fetch_filing("TSLA", "10-K", cache_dir=str(tmp_path))

                assert result["success"] is True
                assert result["cached"] is False
                assert result["company"] == "Tesla, Inc."
                assert Path(result["path"]).read_text() == "filing content"


class TestListCachedFilings:
    """Test list_cached_filings function."""

    def test_list_empty(self, tmp_path):
        """Test listing empty cache."""
        result = list_cached_filings(cache_dir=str(tmp_path))

        assert result["success"] is True
        assert result["count"] == 0
        assert result["disk_usage_mb"] == 0

    def test_list_with_filings(self, tmp_path):
        """Test listing with filings."""
        cache = FilingCache(str(tmp_path))
        cache.save("TSLA", "10-K", "2024-01-30", "x" * 10000, "markdown")

        result = list_cached_filings(cache_dir=str(tmp_path))

        assert result["success"] is True
        assert result["count"] == 1
        assert result["disk_usage_mb"] >= 0.01  # At least 10KB
        assert result["filings"][0]["ticker"] == "TSLA"
