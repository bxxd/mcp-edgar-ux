"""
Unit tests for bitter_edgar.server

Tests the MCP server layer (tool wrappers, not full MCP protocol).
"""
import pytest
from unittest.mock import patch, MagicMock
from mcp_edgar_ux.server import fetch_filing, list_cached


class TestFetchFilingTool:
    """Test fetch_filing MCP tool."""

    @patch('bitter_edgar.server.core_fetch_filing')
    def test_success(self, mock_core):
        """Test successful filing fetch."""
        mock_core.return_value = {
            "success": True,
            "path": "/tmp/sec-filings/TSLA/10-K/2024-01-30.md",
            "company": "Tesla, Inc."
        }

        result = fetch_filing("TSLA", "10-K")

        assert result["success"] is True
        assert "TSLA" in result["path"]
        mock_core.assert_called_once()

    @patch('bitter_edgar.server.core_fetch_filing')
    def test_with_date(self, mock_core):
        """Test fetch with date filter."""
        mock_core.return_value = {"success": True}

        fetch_filing("TSLA", "10-K", date="2024-01-01")

        call_args = mock_core.call_args
        assert call_args.kwargs["date"] == "2024-01-01"

    @patch('bitter_edgar.server.core_fetch_filing')
    def test_with_format(self, mock_core):
        """Test fetch with different format."""
        mock_core.return_value = {"success": True}

        fetch_filing("AAPL", "10-Q", format="html")

        call_args = mock_core.call_args
        assert call_args.kwargs["format"] == "html"

    @patch('bitter_edgar.server.core_fetch_filing')
    def test_error_handling(self, mock_core):
        """Test error handling."""
        mock_core.side_effect = Exception("Network error")

        result = fetch_filing("TSLA", "10-K")

        assert result["success"] is False
        assert "Network error" in result["error"]


class TestListCachedTool:
    """Test list_cached MCP tool."""

    @patch('bitter_edgar.server.core_list_cached')
    def test_success(self, mock_core):
        """Test successful listing."""
        mock_core.return_value = {
            "success": True,
            "filings": [{"ticker": "TSLA", "form_type": "10-K"}],
            "count": 1
        }

        result = list_cached()

        assert result["success"] is True
        assert result["count"] == 1

    @patch('bitter_edgar.server.core_list_cached')
    def test_with_ticker_filter(self, mock_core):
        """Test with ticker filter."""
        mock_core.return_value = {"success": True, "filings": [], "count": 0}

        list_cached(ticker="TSLA")

        call_args = mock_core.call_args
        assert call_args.kwargs["ticker"] == "TSLA"

    @patch('bitter_edgar.server.core_list_cached')
    def test_with_form_filter(self, mock_core):
        """Test with form type filter."""
        mock_core.return_value = {"success": True, "filings": [], "count": 0}

        list_cached(form_type="10-K")

        call_args = mock_core.call_args
        assert call_args.kwargs["form_type"] == "10-K"

    @patch('bitter_edgar.server.core_list_cached')
    def test_error_handling(self, mock_core):
        """Test error handling."""
        mock_core.side_effect = Exception("Disk error")

        result = list_cached()

        assert result["success"] is False
        assert "Disk error" in result["error"]
