"""
Minimal tests for hexagonal architecture

Basic smoke tests to verify the architecture works.
"""
from pathlib import Path

from mcp_edgar_ux.core.domain import Filing, CachedFiling
from mcp_edgar_ux.container import Container


class TestDomainModels:
    """Test domain models are simple dataclasses."""

    def test_filing_creation(self):
        """Test Filing model."""
        filing = Filing(
            ticker="TSLA",
            form_type="10-K",
            filing_date="2024-01-30",
            accession_number="0001628280-24-002390",
            sec_url="https://sec.gov/...",
            company_name="Tesla, Inc.",
            cik="0001318605"
        )
        assert filing.ticker == "TSLA"
        assert filing.form_type == "10-K"

    def test_cached_filing_creation(self):
        """Test CachedFiling model."""
        cached = CachedFiling(
            ticker="TSLA",
            form_type="10-K",
            filing_date="2024-01-30",
            path=Path("/tmp/test.txt"),
            size_bytes=1000,
            format="text"
        )
        assert cached.ticker == "TSLA"
        assert cached.size_bytes == 1000


class TestContainer:
    """Test dependency injection container."""

    def test_container_creates_all_services(self, tmp_path):
        """Test container initializes all dependencies."""
        container = Container(cache_dir=tmp_path, user_agent="test@example.com")

        # Check adapters exist
        assert container.cache is not None
        assert container.fetcher is not None
        assert container.searcher is not None

        # Check services exist
        assert container.fetch_filing is not None
        assert container.list_cached is not None
        assert container.search_filing is not None
        assert container.list_filings is not None

    def test_list_cached_integration(self, tmp_path):
        """Test list_cached service via container."""
        container = Container(cache_dir=tmp_path, user_agent="test@example.com")

        # Execute service
        result = container.list_cached.execute()

        # Service returns tuple (filings, disk_usage_mb)
        assert isinstance(result, tuple)
        filings, disk_usage = result
        assert isinstance(filings, list)
        assert len(filings) == 0  # Empty cache
        assert disk_usage == 0


class TestMCPHandlers:
    """Test MCP handlers use the container."""

    def test_handlers_initialization(self, tmp_path):
        """Test MCP handlers can be created."""
        from mcp_edgar_ux.adapters.mcp.handlers import MCPHandlers

        container = Container(cache_dir=tmp_path, user_agent="test@example.com")
        handlers = MCPHandlers(container)

        assert handlers.container is container

    def test_list_cached_handler(self, tmp_path):
        """Test list_cached handler returns proper dict."""
        from mcp_edgar_ux.adapters.mcp.handlers import MCPHandlers
        import asyncio

        container = Container(cache_dir=tmp_path, user_agent="test@example.com")
        handlers = MCPHandlers(container)

        # Run async handler
        result = asyncio.run(handlers.list_cached())

        # Handlers return dicts (wrapped service results)
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["count"] == 0
