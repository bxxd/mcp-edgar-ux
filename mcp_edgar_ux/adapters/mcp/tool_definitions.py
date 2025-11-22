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

The Bitter Lesson: Don't dump 241K tokens into context.
Save to disk, read what you need (Read/Grep/Bash on the path).

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- form_type: Form type ("10-K", "10-Q", "8-K", "DEF 14A", etc.)
- date: Optional date filter (YYYY-MM-DD). Returns filing >= date. Defaults to most recent.
- format: Output format - "text" (default, clean), "markdown" (may have XBRL), or "html"

Returns:
- path: File path to cached filing (use Read/Grep/Bash on the path)
- metadata: company, ticker, form_type, filing_date, size_bytes, total_lines, etc.
- cached: whether filing was already cached (true) or newly downloaded (false)

Example:
  fetch_filing(ticker="TSLA", form_type="10-K")
  → Returns path + metadata

  Then use the path:
  - Read(path, offset=0, limit=100) to read specific lines
  - search_filing("TSLA", "10-K", "supply chain") to search content
  - Grep(pattern, path) for advanced regex searches
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
Search for pattern in SEC filing with fuzzy matching.

Uses ugrep with fuzzy=1 (tolerates 1 character typo/substitution).
Auto-fetches filing if not cached. Returns matches with surrounding context.

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- form_type: Form type ("10-K", "10-Q", "8-K", etc.)
- pattern: Search pattern (extended regex: use | for alternation, case-insensitive)
- date: Optional date filter (YYYY-MM-DD). Defaults to most recent.
- context_lines: Lines of context before/after match (default: 2)
- max_results: Maximum matches to return (default: 20)

Returns:
- matches: List of matching passages with line numbers
- file_path: Cached filing path (use Read for deep dive)
- match_count: Total number of matches found

Example:
  search_filing(ticker="TSLA", form_type="10-K", pattern="supply chain")
  → Finds "supply chain", "supply-chain", even with typos like "suply chain"

  search_filing(ticker="LNG", form_type="10-Q", pattern="Corpus Christi|Stage 3|expansion")
  → Matches ANY of these terms (| = OR in regex)

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
    "get_financial_statements": {
        "name": "get_financial_statements",
        "description": """
Get simplified financial statements (high-level view only).

IMPORTANT: These are SIMPLIFIED statements showing key metrics only.
For detailed analysis, use fetch_filing() to get the full 10-K/10-Q filing.

What you get:
- Key financial metrics: Revenue, Assets, Cash Flow, Net Income, etc.
- Last 4 annual periods (standardized GAAP concepts)
- Clean, formatted output

What you DON'T get:
- Detailed footnotes, exhibits, or MD&A sections
- Non-GAAP metrics or company-specific line items
- Forward-looking statements or risk factors
- Full granularity of the original filing

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- statement_type: Which statements - "all" (default), "income", "balance", or "cash_flow"

Returns:
- Income: Revenue, expenses, net income
- Balance: Assets, liabilities, equity
- Cash flow: Operating, investing, financing

Example:
  get_financial_statements(ticker="TSLA")
  → Simplified 4-year view of all statements

Use case:
- Quick revenue/margin trend checks
- High-level balance sheet assessment
- Cash flow pattern analysis

For deep analysis: Use fetch_filing() + search_filing() for full 10-K/10-Q content.
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
