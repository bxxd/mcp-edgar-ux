"""
EDGAR Adapter

Implements FilingFetcher port using edgartools library.
"""
from typing import Optional

from edgar import Company, set_identity, get_current_filings, get_ticker_to_cik_lookup
from edgar.current_filings import get_current_entries_on_page

from ..core.domain import Filing
from ..core.ports import FilingFetcher


class EdgarAdapter(FilingFetcher):
    """EDGAR filing fetcher using edgartools"""

    def __init__(self, user_agent: str = "breed research breed@idio.sh"):
        set_identity(user_agent)
        # Lazy-load CIK-to-ticker mapping (only when needed)
        self._cik_to_ticker = None

    def _get_cik_to_ticker_mapping(self) -> dict[int, str]:
        """Get CIK-to-ticker mapping (lazy-loaded and cached)"""
        if self._cik_to_ticker is None:
            ticker_to_cik = get_ticker_to_cik_lookup()
            self._cik_to_ticker = {int(cik): ticker.upper() for ticker, cik in ticker_to_cik.items()}
        return self._cik_to_ticker

    def list_available(self, ticker: Optional[str], form_type: str) -> list[Filing]:
        """
        List all available filings from SEC (historical + current).

        If ticker is None, returns latest filings across all companies.
        Otherwise, combines historical filings (via company.get_filings) with current/recent
        filings (via get_current_filings) to ensure same-day filings are included.
        """
        # If no ticker specified, get latest filings across all companies
        if ticker is None:
            try:
                # Clear edgartools' lru_cache to get fresh data (not stale cached results)
                get_current_entries_on_page.cache_clear()
                current_filings = get_current_filings(form=form_type, page_size=100)
            except Exception as e:
                raise ValueError(f"Failed to get latest filings: {str(e)}")

            # Get CIK-to-ticker mapping for ticker lookups
            cik_to_ticker = self._get_cik_to_ticker_mapping()

            # Helper to convert edgar filing to domain model (no ticker override)
            def to_domain_filing_no_ticker(edgar_filing) -> Filing:
                # Format filing date
                filing_date = edgar_filing.filing_date
                if hasattr(filing_date, 'strftime'):
                    date_str = filing_date.strftime('%Y-%m-%d')
                elif hasattr(filing_date, 'date'):
                    date_str = filing_date.date().strftime('%Y-%m-%d')
                else:
                    date_str = str(filing_date)

                # Look up ticker from CIK, fallback to CIK if not found
                cik = int(edgar_filing.cik) if hasattr(edgar_filing, 'cik') and str(edgar_filing.cik).isdigit() else None
                if cik and cik in cik_to_ticker:
                    ticker_from_cik = cik_to_ticker[cik]
                elif cik:
                    # No ticker found - use CIK formatted as string
                    ticker_from_cik = str(cik)
                else:
                    ticker_from_cik = 'UNKNOWN'

                return Filing(
                    ticker=ticker_from_cik,
                    form_type=edgar_filing.form,
                    filing_date=date_str,
                    accession_number=edgar_filing.accession_number,
                    sec_url=edgar_filing.url,
                    company_name=getattr(edgar_filing, 'company', None),
                    cik=str(cik) if cik else None
                )

            # Convert to domain models
            result = [to_domain_filing_no_ticker(f) for f in current_filings]

            # Sort by date descending (most recent first)
            result.sort(key=lambda x: x.filing_date, reverse=True)
            return result

        # If ticker specified, get filings for that specific company
        company = Company(ticker)

        # Get historical filings (up to ~10 PM EST previous day)
        historical_filings = company.get_filings(form=form_type)

        # Get current/recent filings (same-day and recent)
        try:
            # Clear edgartools' lru_cache to get fresh data
            get_current_entries_on_page.cache_clear()
            current_filings = get_current_filings(form=form_type, page_size=100)
            # Filter for this company's CIK
            current_for_company = [f for f in current_filings if f.cik == int(company.cik)]
        except Exception:
            # If current filings fail, just use historical
            current_for_company = []

        # Helper to convert edgar filing to domain model
        def to_domain_filing(edgar_filing, ticker: str) -> Filing:
            # Format filing date
            filing_date = edgar_filing.filing_date
            if hasattr(filing_date, 'strftime'):
                date_str = filing_date.strftime('%Y-%m-%d')
            elif hasattr(filing_date, 'date'):
                date_str = filing_date.date().strftime('%Y-%m-%d')
            else:
                date_str = str(filing_date)

            return Filing(
                ticker=ticker.upper(),
                form_type=edgar_filing.form,
                filing_date=date_str,
                accession_number=edgar_filing.accession_number,
                sec_url=edgar_filing.url,
                company_name=getattr(edgar_filing, 'company', None),
                cik=str(edgar_filing.cik) if hasattr(edgar_filing, 'cik') else None
            )

        # Convert all filings to domain models
        result = []

        # Add historical filings
        if historical_filings:
            for filing in historical_filings:
                result.append(to_domain_filing(filing, ticker))

        # Add current filings (deduplicate by accession number)
        seen_accessions = {f.accession_number for f in result}
        for filing in current_for_company:
            if filing.accession_number not in seen_accessions:
                result.append(to_domain_filing(filing, ticker))
                seen_accessions.add(filing.accession_number)

        # Sort by date descending (most recent first)
        result.sort(key=lambda x: x.filing_date, reverse=True)
        return result

    def fetch(self, filing: Filing, format: str = "text", include_exhibits: bool = True) -> str:
        """Download filing content from SEC"""
        company = Company(filing.ticker)
        edgar_filing = company.get_filings(
            form=filing.form_type,
            accession_number=filing.accession_number
        )[0]

        # Download content in requested format
        if format == "markdown":
            return edgar_filing.markdown(include_exhibits=include_exhibits)
        elif format == "html":
            return edgar_filing.html()
        else:  # text
            return edgar_filing.text()

    def get_latest(self, ticker: Optional[str], form_type: str, date: Optional[str] = None) -> Filing:
        """Get metadata for latest filing (or first filing >= date)

        If ticker is None, returns latest filing across all companies.
        """
        filings = self.list_available(ticker, form_type)

        if not filings:
            ticker_str = ticker if ticker else "any ticker"
            raise ValueError(f"No {form_type} filings found for {ticker_str}")

        # Filter by date if specified
        if date:
            filtered = [f for f in filings if f.filing_date >= date]
            if not filtered:
                ticker_str = ticker if ticker else "any ticker"
                raise ValueError(
                    f"No {form_type} filings found for {ticker_str} on or after {date}"
                )
            # Return the oldest filing that matches (closest to the target date)
            # filings are sorted newest-first, so filtered[-1] is the oldest match
            return filtered[-1]

        # Return most recent
        return filings[0]
