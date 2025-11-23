"""
MCP Tool Definitions

Single source of truth for tool schemas and descriptions.
Used by both stdio and HTTP/SSE servers.
"""

# Tool schemas for MCP
TOOL_SCHEMAS = {
    "fetch_filing": {
        "name": "fetch_filing",
        "description": """
Download SEC filing to disk, return path.

Filing is saved to disk (not loaded into context). Use Read/Grep/search_filing on the returned path.

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- form_type: Form type ("10-K", "10-Q", "8-K", "DEF 14A", etc.)
- date: Optional date filter (YYYY-MM-DD). Returns filing >= date. Defaults to most recent.
- format: "text" (default, clean), "markdown" (may have XBRL), or "html"

Returns:
- path: File path to cached filing
- metadata: company, ticker, form_type, filing_date, size_bytes, total_lines
- cached: true if already cached, false if newly downloaded

Example:
  fetch_filing(ticker="TSLA", form_type="10-K")
  → Returns: {path: "/var/.../TSLA/10-K/2024-01-29.txt", ...}

  Then: Read(path, offset=0, limit=100) or Grep("risk factors", path)
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker (e.g., 'TSLA', 'AAPL')"
                },
                "form_type": {
                    "type": "string",
                    "description": "Form type (e.g., '10-K', '10-Q', '8-K', 'DEF 14A')"
                },
                "date": {
                    "type": "string",
                    "description": "Optional date filter (YYYY-MM-DD). Returns filing >= date. Defaults to most recent."
                },
                "format": {
                    "type": "string",
                    "enum": ["text", "markdown", "html"],
                    "description": "Output format: 'text' (default, clean), 'markdown' (may have XBRL), 'html'"
                },
                "preview_lines": {
                    "type": "integer",
                    "description": "Deprecated: Preview removed. Use Read(path, offset=0, limit=N) instead.",
                    "default": 0
                },
                "force_refetch": {
                    "type": "boolean",
                    "description": "Force re-download even if cached (use if cached version seems incorrect). Default: false",
                    "default": False
                }
            },
            "required": ["ticker", "form_type"]
        }
    },
    "search_filing": {
        "name": "search_filing",
        "description": """
Search for pattern in SEC filing. Auto-fetches if not cached.

Fuzzy matching: tolerates 1-character differences (fuzzy=1).
Returns matches with line numbers and surrounding context.

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- form_type: Form type ("10-K", "10-Q", "8-K", etc.)
- pattern: Search pattern (extended regex: use | for OR, case-insensitive)
- date: Optional date filter (YYYY-MM-DD). Defaults to most recent.
- context_lines: Lines of context before/after match (default: 2)
- max_results: Maximum matches to return (default: 20)

Returns:
- matches: List with line numbers and context
- file_path: Path to cached filing
- match_count: Total matches found

Example:
  search_filing(ticker="TSLA", form_type="10-K", pattern="supply chain")
  → Finds: "supply chain", "supply-chain", "Supply Chain" (case/hyphen variations)

  search_filing(ticker="LNG", form_type="10-Q", pattern="Corpus Christi|Stage 3")
  → Finds either term (| = OR)

  Then: Read(file_path, offset=1230, limit=50) to read around a match
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker (e.g., 'TSLA', 'AAPL')"
                },
                "form_type": {
                    "type": "string",
                    "description": "Form type (e.g., '10-K', '10-Q', '8-K')"
                },
                "pattern": {
                    "type": "string",
                    "description": "Search pattern (regex supported, case-insensitive)"
                },
                "date": {
                    "type": "string",
                    "description": "Optional date filter (YYYY-MM-DD). Defaults to most recent."
                },
                "context_lines": {
                    "type": "integer",
                    "description": "Lines of context before/after match (default: 2)",
                    "default": 2
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum matches to return (default: 20)",
                    "default": 20
                },
                "offset": {
                    "type": "integer",
                    "description": "Skip first N matches (for pagination, default: 0)",
                    "default": 0
                }
            },
            "required": ["ticker", "form_type", "pattern"]
        }
    },
    "list_filings": {
        "name": "list_filings",
        "description": """
List available SEC filings and their cached status.

Shows filings available from SEC, marks which are already cached locally.
Use before fetch_filing to see what exists.

Args:
- ticker: Optional stock ticker (e.g., "TSLA", "AAPL"). Omit to see latest across all companies.
- form_type: Form type (e.g., "10-K", "10-Q", "8-K")
- start: Starting index (default: 0, newest first)
- max: Maximum filings to return (default: 15)

Returns:
- filings: List sorted by date (newest first)
- Each shows: ticker, filing_date, cached status (✓ = cached), size

Example:
  list_filings(form_type="10-K")
  → Latest 15 10-K filings across all companies

  list_filings(ticker="TSLA", form_type="10-K")
  → TSLA's 15 most recent 10-Ks

  list_filings(ticker="TSLA", form_type="10-K", start=15, max=15)
  → Next 15 (pagination)

  Then: fetch_filing("TSLA", "10-K", "2023-01-31") to download specific filing
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Optional stock ticker (e.g., 'TSLA', 'AAPL'). Omit to see latest filings across all companies."
                },
                "form_type": {
                    "type": "string",
                    "description": "Form type (e.g., '10-K', '10-Q', '8-K')"
                },
                "start": {
                    "type": "integer",
                    "description": "Starting index (default: 0, latest filings first)",
                    "default": 0
                },
                "max": {
                    "type": "integer",
                    "description": "Maximum filings to return (default: 15)",
                    "default": 15
                }
            },
            "required": ["form_type"]
        }
    },
    "get_financial_statements": {
        "name": "get_financial_statements",
        "description": """
Get simplified financial statements (key metrics only, last 4 years).

Returns standardized GAAP metrics: Revenue, Net Income, Assets, Cash Flow, etc.
Data from SEC aggregated filings (clean, fast).

LIMITATIONS - This does NOT include:
- Footnotes, exhibits, MD&A, or detailed line items
- Non-GAAP metrics or forward-looking statements
- Full filing granularity

For detailed analysis: Use fetch_filing() to get complete 10-K/10-Q.

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- statement_type: "all" (default), "income", "balance", or "cash_flow"

Returns:
- Income: Revenue, expenses, net income
- Balance: Assets, liabilities, equity
- Cash flow: Operating, investing, financing

Example:
  get_financial_statements(ticker="TSLA")
  → 4-year summary of all statements

  get_financial_statements(ticker="TSLA", statement_type="income")
  → Income statement only

Use for: Quick trend checks (revenue growth, margins, cash generation)
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker (e.g., 'TSLA', 'AAPL')"
                },
                "statement_type": {
                    "type": "string",
                    "enum": ["all", "income", "balance", "cash_flow"],
                    "description": "Which statements to return: 'all', 'income', 'balance', 'cash_flow'",
                    "default": "all"
                }
            },
            "required": ["ticker"]
        }
    }
}
