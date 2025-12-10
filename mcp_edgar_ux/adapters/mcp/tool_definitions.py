"""
MCP Tool Definitions

Single source of truth for tool schemas and descriptions.
Used by both stdio and HTTP/SSE servers.
"""

# Tool schemas for MCP
TOOL_SCHEMAS = {
    "fetch_filing": {
        "name": "fetch_filing",
        "description": """Download SEC filing to disk. Returns path for Read/Grep/search_filing.

fetch_filing("TSLA", "10-K") → {path: ".../TSLA/10-K/2024-01-29.txt", cached: true}
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker (e.g. TSLA, AAPL)"
                },
                "form_type": {
                    "type": "string",
                    "description": "Form type (e.g. 10-K, 10-Q, 8-K, DEF 14A)"
                },
                "date": {
                    "type": "string",
                    "description": "Date filter (YYYY-MM-DD). Returns filing >= date, or most recent if omitted."
                },
                "format": {
                    "type": "string",
                    "enum": ["text", "markdown", "html"],
                    "description": "Output format (text=clean, markdown=may have XBRL, html=raw)"
                },
                "preview_lines": {
                    "type": "integer",
                    "description": "Deprecated - preview removed",
                    "default": 0
                },
                "force_refetch": {
                    "type": "boolean",
                    "description": "Re-download even if cached (use if cached version seems incorrect)",
                    "default": False
                }
            },
            "required": ["ticker", "form_type"]
        }
    },
    "search_filing": {
        "name": "search_filing",
        "description": """Search SEC filing for pattern. Auto-fetches if not cached. Fuzzy matching (1-char tolerance).

search_filing("TSLA", "10-K", "supply chain") → matches with line numbers + context
search_filing("LNG", "10-Q", "Corpus|Stage 3") → OR patterns with |
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker (e.g. TSLA, AAPL)"
                },
                "form_type": {
                    "type": "string",
                    "description": "Form type (e.g. 10-K, 10-Q, 8-K)"
                },
                "pattern": {
                    "type": "string",
                    "description": "Search pattern (extended regex, case-insensitive, fuzzy=1)"
                },
                "date": {
                    "type": "string",
                    "description": "Date filter (YYYY-MM-DD). Returns filing >= date, or most recent if omitted."
                },
                "context_lines": {
                    "type": "integer",
                    "description": "Lines of context before/after each match",
                    "default": 2
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum matches to return",
                    "default": 20
                },
                "offset": {
                    "type": "integer",
                    "description": "Skip first N matches (pagination)",
                    "default": 0
                }
            },
            "required": ["ticker", "form_type", "pattern"]
        }
    },
    "list_filings": {
        "name": "list_filings",
        "description": """List available SEC filings with cached status. Newest first.

list_filings(form_type="10-K") → latest 15 10-Ks across all companies
list_filings(form_type="ALL") → latest 15 filings of any type across all companies
list_filings("TSLA", "10-K") → TSLA's 10-Ks
list_filings("TSLA", "ALL") → all of TSLA's filings
list_filings("TSLA", "10-K", start=15) → pagination
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker (e.g. TSLA, AAPL). Omit to see latest across all companies."
                },
                "form_type": {
                    "type": "string",
                    "description": "Form type (e.g. 10-K, 10-Q, 8-K, ALL). Use 'ALL' for all form types."
                },
                "start": {
                    "type": "integer",
                    "description": "Starting index (newest first)",
                    "default": 0
                },
                "max": {
                    "type": "integer",
                    "description": "Maximum filings to return",
                    "default": 15
                }
            },
            "required": ["form_type"]
        }
    },
    "get_financial_statements": {
        "name": "get_financial_statements",
        "description": """Get simplified GAAP financials (last 4 years). Quick trend checks only.

get_financial_statements("TSLA") → income, balance, cash_flow summary
get_financial_statements("TSLA", "income") → income statement only

For detailed analysis: use fetch_filing() for complete 10-K/10-Q.
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker (e.g. TSLA, AAPL)"
                },
                "statement_type": {
                    "type": "string",
                    "enum": ["all", "income", "balance", "cash_flow"],
                    "description": "Which statements to return",
                    "default": "all"
                }
            },
            "required": ["ticker"]
        }
    }
}
