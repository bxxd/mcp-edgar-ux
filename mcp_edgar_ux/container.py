"""
Dependency Injection Container

Wires together the hexagonal architecture by creating and injecting dependencies.
"""
from pathlib import Path

from .adapters import FilesystemCache, EdgarAdapter, GrepSearcher
from .core import (
    FetchFilingService,
    ListFilingsService,
    SearchFilingService,
    ListCachedService,
    FinancialStatementsService,
    ThirteenFHoldingsService
)


class Container:
    """Dependency injection container for the application"""

    def __init__(self, cache_dir: str | Path, user_agent: str = "breed research breed@idio.sh"):
        # Adapters (infrastructure)
        self.cache = FilesystemCache(cache_dir)
        self.fetcher = EdgarAdapter(user_agent)
        self.searcher = GrepSearcher()

        # Services (use cases)
        self.fetch_filing = FetchFilingService(
            repository=self.cache,
            fetcher=self.fetcher,
            searcher=self.searcher
        )

        self.list_filings = ListFilingsService(
            repository=self.cache,
            fetcher=self.fetcher
        )

        self.search_filing = SearchFilingService(
            repository=self.cache,
            fetcher=self.fetcher,
            searcher=self.searcher,
            fetch_service=self.fetch_filing
        )

        self.list_cached = ListCachedService(
            repository=self.cache
        )

        self.get_financials = FinancialStatementsService()
        self.get_13f_holdings = ThirteenFHoldingsService()
