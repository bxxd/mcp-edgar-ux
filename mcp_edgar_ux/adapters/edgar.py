"""
EDGAR Adapter

Implements FilingFetcher port using edgartools library.
"""
from typing import Optional

from edgar import Company, set_identity, get_current_filings

from ..core.domain import Filing
from ..core.ports import FilingFetcher


class EdgarAdapter(FilingFetcher):
    """EDGAR filing fetcher using edgartools"""

    def __init__(self, user_agent: str = "breed research breed@idio.sh"):
        set_identity(user_agent)

    def list_available(self, ticker: str, form_type: str) -> list[Filing]:
        """
        List all available filings from SEC (historical + current).

        Combines historical filings (via company.get_filings) with current/recent
        filings (via get_current_filings) to ensure same-day filings are included.
        """
        company = Company(ticker)

        # Get historical filings (up to ~10 PM EST previous day)
        historical_filings = company.get_filings(form=form_type)

        # Get current/recent filings (same-day and recent)
        try:
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

    def get_latest(self, ticker: str, form_type: str, date: Optional[str] = None) -> Filing:
        """Get metadata for latest filing (or first filing >= date)"""
        filings = self.list_available(ticker, form_type)

        if not filings:
            raise ValueError(f"No {form_type} filings found for {ticker}")

        # Filter by date if specified
        if date:
            filtered = [f for f in filings if f.filing_date >= date]
            if not filtered:
                raise ValueError(
                    f"No {form_type} filings found for {ticker} on or after {date}"
                )
            return filtered[0]

        # Return most recent
        return filings[0]
