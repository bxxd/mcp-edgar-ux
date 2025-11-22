"""
Application Services - Use cases that orchestrate domain logic

These are the entry points to the core. They coordinate between
domain models and ports, but contain no infrastructure concerns.
"""
from typing import Optional, Literal
from edgar import Company, get_filings

from .domain import Filing, FilingContent, SearchResult, CachedFiling
from .ports import FilingRepository, FilingFetcher, FilingSearcher


class FetchFilingService:
    """Use case: Fetch a SEC filing and cache it"""

    def __init__(
        self,
        repository: FilingRepository,
        fetcher: FilingFetcher,
        searcher: FilingSearcher
    ):
        self.repository = repository
        self.fetcher = fetcher
        self.searcher = searcher

    def execute(
        self,
        ticker: str,
        form_type: str,
        date: Optional[str] = None,
        format: str = "text",
        include_exhibits: bool = True,
        preview_lines: int = 50,
        force_refetch: bool = False
    ) -> FilingContent:
        """
        Fetch filing and cache it.

        Returns FilingContent with path, preview, and metadata.
        """
        # Get filing metadata
        filing = self.fetcher.get_latest(ticker, form_type, date)

        # Check if already cached (skip if force_refetch)
        cached_path = self.repository.get(ticker, form_type, filing.filing_date, format) if not force_refetch else None

        if cached_path:
            # Read from cache
            content = cached_path.read_text(encoding='utf-8')
            total_lines = self.searcher.count_lines(cached_path)
        else:
            # Download from SEC
            content = self.fetcher.fetch(filing, format, include_exhibits)

            # Save to cache
            filing_content = FilingContent(
                filing=filing,
                content=content,
                format=format,
                path=None,  # Will be set by repository
                size_bytes=len(content.encode('utf-8')),
                total_lines=content.count('\n') + 1
            )
            cached_path = self.repository.save(filing_content)
            total_lines = filing_content.total_lines

        # Return with metadata
        return FilingContent(
            filing=filing,
            content=content,
            format=format,
            path=cached_path,
            size_bytes=cached_path.stat().st_size,
            total_lines=total_lines
        )


class ListFilingsService:
    """Use case: List available filings (both cached and from SEC)"""

    def __init__(
        self,
        repository: FilingRepository,
        fetcher: FilingFetcher
    ):
        self.repository = repository
        self.fetcher = fetcher

    def execute(self, ticker: Optional[str], form_type: str) -> tuple[list[Filing], list[CachedFiling]]:
        """
        List all available filings and which ones are cached.

        If ticker is None, returns latest filings across all companies.

        Returns:
            (available_filings, cached_filings)
        """
        # Get all available from SEC
        available = self.fetcher.list_available(ticker, form_type)

        # Get cached filings for this ticker/form (or all if ticker is None)
        cached = self.repository.list_all(ticker, form_type)

        return available, cached


class SearchFilingService:
    """Use case: Search for pattern within a filing"""

    def __init__(
        self,
        repository: FilingRepository,
        fetcher: FilingFetcher,
        searcher: FilingSearcher,
        fetch_service: FetchFilingService
    ):
        self.repository = repository
        self.fetcher = fetcher
        self.searcher = searcher
        self.fetch_service = fetch_service

    def execute(
        self,
        ticker: str,
        form_type: str,
        pattern: str,
        date: Optional[str] = None,
        format: str = "text",
        context_lines: int = 2,
        max_results: int = 20,
        offset: int = 0
    ) -> SearchResult:
        """
        Search for pattern in filing.

        Auto-fetches and caches filing if not already cached.
        """
        # Get filing metadata
        filing = self.fetcher.get_latest(ticker, form_type, date)

        # Ensure filing is cached
        cached_path = self.repository.get(ticker, form_type, filing.filing_date, format)

        if not cached_path:
            # Fetch and cache it first
            filing_content = self.fetch_service.execute(
                ticker, form_type, date, format, include_exhibits=True, preview_lines=0
            )
            cached_path = filing_content.path

        # Search in the cached file
        matches, total_count = self.searcher.search(
            cached_path,
            pattern,
            context_lines,
            max_results,
            offset
        )

        return SearchResult(
            filing=filing,
            pattern=pattern,
            matches=matches,
            total_matches=total_count,
            file_path=cached_path
        )


class ListCachedService:
    """Use case: List cached filings"""

    def __init__(self, repository: FilingRepository):
        self.repository = repository

    def execute(
        self,
        ticker: Optional[str] = None,
        form_type: Optional[str] = None
    ) -> tuple[list[CachedFiling], int]:
        """
        List cached filings and disk usage.

        Returns:
            (cached_filings, disk_usage_bytes)
        """
        filings = self.repository.list_all(ticker, form_type)
        disk_usage = self.repository.get_disk_usage()

        return filings, disk_usage


class FinancialStatementsService:
    """Use case: Get structured financial statements from Entity Facts API"""

    def execute(
        self,
        ticker: str,
        statement_type: Literal["all", "income", "balance", "cash_flow"] = "all"
    ) -> dict:
        """
        Get multi-period financial statements using edgartools Entity Facts API.

        This uses edgartools' built-in caching (HTTP cache + LRU cache).
        No custom caching needed - edgartools handles it automatically.

        Args:
            ticker: Stock ticker (e.g., "TSLA", "AAPL")
            statement_type: Which statements to return

        Returns:
            Dict with statement data and metadata:
            {
                "company_name": str,
                "cik": str,
                "ticker": str,
                "statements": {
                    "income": MultiPeriodStatement or None,
                    "balance": MultiPeriodStatement or None,
                    "cash_flow": MultiPeriodStatement or None
                }
            }
        """
        # Get company and facts
        company = Company(ticker)
        facts = company.get_facts()

        # Build result
        result = {
            "company_name": company.name,
            "cik": company.cik,
            "ticker": ticker.upper(),
            "statements": {}
        }

        # Get requested statements
        if statement_type in ("all", "income"):
            result["statements"]["income"] = facts.income_statement()

        if statement_type in ("all", "balance"):
            result["statements"]["balance"] = facts.balance_sheet()

        if statement_type in ("all", "cash_flow"):
            result["statements"]["cash_flow"] = facts.cash_flow()

        return result


class ThirteenFHoldingsService:
    """Use case: Get 13F-HR institutional holdings"""

    def execute(
        self,
        identifier: str,
        top_n: int = 20
    ) -> dict:
        """
        Get 13F-HR institutional holdings.

        Shows what an institution owns (their portfolio holdings).

        Args:
            identifier: Ticker or CIK of institutional investor (e.g., "BRK-A", "1067983" for Berkshire)
            top_n: Number of top holdings to return (default: 20)

        Returns:
            Dict with holdings data and metadata:
            {
                "manager_name": str,
                "cik": str,
                "report_period": str,  # e.g., "2024-09-30"
                "filing_date": str,
                "total_holdings": int,
                "total_value": int,
                "holdings": DataFrame with top N holdings
            }
        """
        # Try to resolve identifier to CIK if it's a ticker
        try:
            company = Company(identifier)
            cik = company.cik
        except:
            # Assume it's already a CIK
            cik = identifier

        # Get latest 13F-HR filing for this CIK
        filings = get_filings(form="13F-HR", amendments=False).filter(cik=cik).head(1)

        if len(filings) == 0:
            raise ValueError(f"No 13F-HR filings found for {identifier}")

        filing = filings[0]
        f13 = filing.obj()

        # Get holdings DataFrame
        holdings_df = f13.infotable

        if holdings_df is None or len(holdings_df) == 0:
            raise ValueError(f"No holdings data found in 13F filing")

        # Sort by value (descending) and take top N
        holdings_df = holdings_df.sort_values('Value', ascending=False).head(top_n)

        # Build result
        result = {
            "manager_name": f13.management_company_name,
            "cik": cik,
            "report_period": str(f13.report_period),
            "filing_date": str(filing.filing_date),
            "total_holdings": f13.total_holdings,
            "total_value": f13.total_value,
            "holdings": holdings_df
        }

        return result


class InsiderTransactionsService:
    """Use case: Get insider buy/sell transactions from Form 4 filings"""

    def execute(
        self,
        ticker: str,
        days: int = 90,
        transaction_type: str = "all"
    ) -> dict:
        """
        Get insider transactions from Form 4 filings.

        Args:
            ticker: Stock ticker (e.g., "TSLA", "AAPL")
            days: Lookback period in days (default: 90)
            transaction_type: Filter - "buy", "sell", or "all" (default: "all")

        Returns:
            Dict with transaction data:
            {
                "company": str,
                "ticker": str,
                "cik": str,
                "transactions": DataFrame with columns:
                    - filing_date: When Form 4 was filed
                    - transaction_date: When transaction occurred
                    - insider_name: Name of insider
                    - transaction_type: "Purchase" or "Sale"
                    - shares: Number of shares
                    - price: Price per share
                    - value: Total value (shares * price)
                    - remaining: Shares remaining after transaction
                    - ownership: "Direct" or "Indirect"
            }
        """
        from datetime import datetime, timedelta
        import pandas as pd

        # Get company info
        company = Company(ticker)
        cik = company.cik

        # Get Form 4 filings
        filings = get_filings(form="4", amendments=False).filter(cik=cik)

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)

        # Collect transactions
        all_transactions = []

        for filing in filings:
            # Check if filing is within date range
            if filing.filing_date < cutoff_date.date():
                break  # Filings are sorted newest first

            try:
                form4 = filing.obj()
                table = form4.non_derivative_table

                if not table.has_transactions:
                    continue

                # Get market trades (actual buys/sells)
                market = table.market_trades

                if market is None or market.empty:
                    continue

                # Extract transaction data
                for _, row in market.iterrows():
                    txn_type = row.get('TransactionType', '')

                    # Filter by transaction type if specified
                    if transaction_type != "all":
                        if transaction_type.lower() == "buy" and txn_type != "Purchase":
                            continue
                        if transaction_type.lower() == "sell" and txn_type != "Sale":
                            continue

                    all_transactions.append({
                        'filing_date': filing.filing_date,
                        'transaction_date': row.get('Date'),
                        'insider_name': form4.insider_name,
                        'transaction_type': txn_type,
                        'shares': row.get('Shares', 0),
                        'price': row.get('Price', 0),
                        'value': row.get('Shares', 0) * row.get('Price', 0),
                        'remaining': row.get('Remaining', 0),
                        'ownership': row.get('DirectIndirect', 'N/A')
                    })

            except Exception:
                # Skip filings that fail to parse
                continue

        # Convert to DataFrame
        if not all_transactions:
            # Return empty result
            return {
                "company": company.name,
                "ticker": ticker.upper(),
                "cik": cik,
                "days": days,
                "transaction_type": transaction_type,
                "transaction_count": 0,
                "transactions": pd.DataFrame()
            }

        df = pd.DataFrame(all_transactions)

        # Sort by transaction date (newest first)
        df = df.sort_values('transaction_date', ascending=False)

        return {
            "company": company.name,
            "ticker": ticker.upper(),
            "cik": cik,
            "days": days,
            "transaction_type": transaction_type,
            "transaction_count": len(df),
            "transactions": df
        }
