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
Download SEC filing to disk, return path + preview.

The Bitter Lesson: Don't dump 241K tokens into context.
Save to disk, read what you need (Read/Grep/Bash on the path).

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- form_type: Form type ("10-K", "10-Q", "8-K", "DEF 14A", etc.)
- date: Optional date filter (YYYY-MM-DD). Returns filing >= date. Defaults to most recent.
- format: Output format - "text" (default, clean), "markdown" (may have XBRL), or "html"
- preview_lines: Number of lines to preview (default: 50, 0 to disable)

Returns:
- path: File path to cached filing (use Read/Grep/Bash)
- preview: First N lines with line numbers (like Read tool)
- metadata: company, ticker, form_type, filing_date, size_bytes, total_lines, etc.

Example:
  fetch_filing(ticker="TSLA", form_type="10-K")
  → Shows path, preview (first 50 lines), metadata

  Then: search_filing("TSLA", "10-K", "supply chain")
  Or: Read(path, offset=100, limit=100)
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
                    "description": "Force re-download even if cached (useful after edgartools updates). Default: false",
                    "default": False
                }
            },
            "required": ["ticker", "form_type"]
        }
    },
    "search_filing": {
        "name": "search_filing",
        "description": """
Search for pattern in SEC filing (like grep with line numbers).

Auto-fetches filing if not cached. Returns matches with surrounding context.
Use this to find specific content in filings without reading the entire document.

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- form_type: Form type ("10-K", "10-Q", "8-K", etc.)
- pattern: Search pattern (extended regex: use | for alternation, case-insensitive by default)
- date: Optional date filter (YYYY-MM-DD). Defaults to most recent.
- context_lines: Lines of context before/after match (default: 2)
- max_results: Maximum matches to return (default: 20)

Returns:
- matches: List of matching passages with line numbers
- file_path: Cached filing path (use Read for deep dive)
- match_count: Total number of matches found

Example:
  search_filing(ticker="TSLA", form_type="10-K", pattern="supply chain")
  → Shows all "supply chain" mentions with line numbers and context

  search_filing(ticker="LNG", form_type="10-Q", pattern="Corpus Christi|Stage 3|expansion")
  → Shows matches for ANY of these terms (extended regex with | alternation)

  Then: Read(path, offset=1230, limit=50)  # Deep dive at specific line
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
List available SEC filings (both cached + available from SEC).

Discovery tool - shows which filings exist and which are already cached.
Use this BEFORE fetch_filing to see what's available.

Args:
- ticker: Optional stock ticker (e.g., "TSLA", "AAPL"). If omitted, shows latest filings across all companies.
- form_type: Form type (e.g., "10-K", "10-Q", "8-K")
- start: Starting index (default: 0, latest filings first)
- max: Maximum filings to return (default: 15)

Returns:
- filings: List of available filings (sorted by date, newest first)
- Each filing shows: ticker, filing_date, cached (✓ or blank), size (if cached)
- Shows which filings need to be fetched vs already cached

Example:
  list_filings(form_type="10-K")
  → Shows first 15 recent 10-K filings across all companies

  list_filings(ticker="TSLA", form_type="10-K")
  → Shows first 15 TSLA 10-K filings (latest)

  list_filings(ticker="TSLA", form_type="10-K", start=15, max=15)
  → Shows next 15 filings (pagination)

  Then: fetch_filing("TSLA", "10-K", "2023-01-31")  # Fetch specific filing
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
    "list_cached": {
        "name": "list_cached",
        "description": """
List SEC filings cached on disk.

Returns all cached filings with paths, or filter by ticker/form_type.

Args:
- ticker: Optional ticker filter (e.g., "TSLA")
- form_type: Optional form type filter (e.g., "10-K")

Returns:
- filings: List of cached filings with path, ticker, form_type, filing_date, size
- count: Total number of cached filings
- disk_usage_mb: Total disk usage

Example:
  list_cached()  # All cached filings
  list_cached(ticker="TSLA")  # TSLA filings only
  list_cached(form_type="10-K")  # All 10-Ks
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Optional ticker filter"
                },
                "form_type": {
                    "type": "string",
                    "description": "Optional form type filter"
                }
            },
            "required": []
        }
    },
    "get_financial_statements": {
        "name": "get_financial_statements",
        "description": """
Get structured financial statements from SEC Entity Facts API.

Fast, structured financial data (income statement, balance sheet, cash flow).
Uses edgartools' built-in caching for performance.

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- periods: Number of periods to return (default: 4 years)
- statement_type: Which statements - "all" (default), "income", "balance", or "cash_flow"

Returns:
- Formatted multi-year financial statements with BBG Lite styling
- Income statement: Revenue, expenses, net income
- Balance sheet: Assets, liabilities, equity
- Cash flow: Operating, investing, financing activities

Example:
  get_financial_statements(ticker="TSLA")
  → Returns last 4 years of all statements

  get_financial_statements(ticker="TSLA", periods=10, statement_type="income")
  → Returns 10 years of income statement only

Use case:
- Revenue growth trends
- Margin analysis (gross, operating, net)
- Balance sheet strength
- Cash flow quality
- YoY comparisons
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker (e.g., 'TSLA', 'AAPL')"
                },
                "periods": {
                    "type": "integer",
                    "description": "Number of periods to return (default: 4)",
                    "default": 4
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
    },
    "get_13f_holdings": {
        "name": "get_13f_holdings",
        "description": """
Get 13F-HR institutional holdings data.

Shows what an institutional investor owns (their portfolio holdings).
13F-HR filings are required for managers with >$100M AUM.

Args:
- identifier: Ticker or CIK of institutional investor (e.g., "BRK-A", "1067983" for Berkshire)
- top_n: Number of top holdings to return (default: 20)

Returns:
- Formatted holdings table with BBG Lite styling
- Manager name, report period, filing date
- Total holdings count and portfolio value
- Top N positions with: Ticker, Issuer, Shares, Value, % of portfolio

Example:
  get_13f_holdings(identifier="BRK-A")
  → Shows Berkshire Hathaway's top 20 holdings

  get_13f_holdings(identifier="1067983", top_n=50)
  → Shows top 50 holdings using CIK directly

Use case:
- Institutional positioning (what smart money owns)
- Portfolio concentration (top holdings %)
- Position sizing (shares, value)
- Peer comparison (multiple managers)
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Ticker or CIK of institutional investor (e.g., 'BRK-A', '1067983' for Berkshire)"
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top holdings to return (default: 20)",
                    "default": 20
                }
            },
            "required": ["identifier"]
        }
    }
}
