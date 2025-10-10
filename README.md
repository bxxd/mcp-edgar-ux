# bitter-edgar

*Scale beats cleverness. Save to disk, read what you need.*

MCP server for SEC filings that returns file paths, not content.

## The Bitter Lesson

Current SEC MCPs dump 241K tokens into your context per filing. This is the clever approach.

The bitter lesson: Just save to disk. Use Read/Grep/Bash. Scale storage, not prompts.

## Installation

```bash
poetry install
```

## Usage

### Production (Background Daemon)

```bash
make start      # Start server on http://localhost:8080
make stop       # Stop server
make restart    # Restart server
make status     # Check status
make logs       # Tail logs
```

### Development (Auto-restart)

```bash
make dev        # Watch for file changes, auto-restart
```

### Configure Claude Code

**Option 1: Standalone executable (recommended)**

Use the provided `bitter-edgar-mcp` executable for easy setup:

```json
{
  "projects": {
    "/your/project/path": {
      "mcpServers": {
        "bitter-edgar": {
          "command": "/path/to/bitter-edgar/bitter-edgar-mcp"
        }
      }
    }
  }
}
```

Or add via Claude Code UI: Settings → MCP → Add Server → Command: `/path/to/bitter-edgar/bitter-edgar-mcp`

Restart Claude Code and the server will start automatically.

**Option 2: Using Poetry directly**

If you prefer to use Poetry:

```json
{
  "projects": {
    "/your/project/path": {
      "mcpServers": {
        "bitter-edgar": {
          "command": "poetry",
          "args": ["run", "bitter-edgar"],
          "cwd": "/path/to/bitter-edgar"
        }
      }
    }
  }
}
```

**Option 3: Background HTTP server**

For advanced use cases (multiple clients, debugging without restart):

```bash
make start      # Start server on http://localhost:6660
make status     # Check if running
```

Then configure Claude Code with HTTP transport (see docs).

**Usage in Claude Code:**

```bash
# Fetch a filing
fetch_filing("TSLA", "10-K")
→ {path: "/tmp/sec-filings/TSLA/10-K/2025-04-30.txt", ...}

# Read what you need
Read("/tmp/sec-filings/TSLA/10-K/2025-04-30.txt", offset=1200, limit=50)

# Search for terms
Grep("supply chain", path="/tmp/sec-filings/TSLA/10-K/2025-04-30.txt")

# List cached filings
list_cached()
```

## Tools

### `fetch_filing(ticker, form_type, date=None, format="text")`

Download SEC filing to disk, return path.

**Args:**
- `ticker`: Stock ticker (e.g., "TSLA", "AAPL")
- `form_type`: Form type ("10-K", "10-Q", "8-K", etc.)
- `date`: Optional date filter (YYYY-MM-DD). Returns filing closest >= date.
- `format`: Output format - "text" (default, clean), "markdown" (may have XBRL), or "html"

**Returns:**
```json
{
  "success": true,
  "path": "/tmp/sec-filings/TSLA/10-K/2025-04-30.txt",
  "company": "Tesla, Inc.",
  "ticker": "TSLA",
  "form_type": "10-K",
  "filing_date": "2025-04-30",
  "format": "text",
  "size_bytes": 427000,
  "sec_url": "https://...",
  "cached": false
}
```

**Examples:**
```python
# Latest filing (text format, clean)
fetch_filing("TSLA", "10-K")

# Filing on or after specific date
fetch_filing("TSLA", "10-K", date="2024-01-01")

# Markdown format (may contain XBRL artifacts)
fetch_filing("AAPL", "10-Q", format="markdown")
```

### `list_cached(ticker=None, form_type=None)`

List filings cached on disk.

**Args:**
- `ticker`: Optional ticker filter
- `form_type`: Optional form type filter

**Returns:**
```json
{
  "success": true,
  "filings": [
    {
      "ticker": "TSLA",
      "form_type": "10-K",
      "filing_date": "2025-04-30",
      "path": "/tmp/sec-filings/TSLA/10-K/2025-04-30.md",
      "size_bytes": 247217
    }
  ],
  "count": 1,
  "disk_usage_mb": 0.24
}
```

## Configuration

**Cache Directory:**
- Default: `/tmp/sec-filings`
- Env var: `export BITTER_EDGAR_CACHE_DIR=/custom/path`
- CLI arg: `--cache-dir /custom/path`

**User Agent:**
- Hardcoded: `breed research breed@idio.sh`
- SEC requires this for API access

## Workflow Example

```bash
# 1. Fetch Tesla's latest 10-K
fetch_filing("TSLA", "10-K")
→ /tmp/sec-filings/TSLA/10-K/2025-04-30.txt (427KB, clean text)

# 2. Search for supply chain mentions
Grep("supply chain", path="/tmp/sec-filings/TSLA/10-K/2025-04-30.txt")
→ 12 matches, lines [1234, 2456, ...]

# 3. Read specific section
Read("/tmp/sec-filings/TSLA/10-K/2025-04-30.txt", offset=1200, limit=50)
→ Only 50 lines in context (not 241K tokens)

# 4. Analyze
"What are Tesla's supply chain risks?"
```

## Why File-Based?

**Problem:** Current MCPs dump full filing into tool response
- TSLA 10-K = 241,120 tokens
- AAPL 10-K = 268,922 tokens
- Blows through context window
- Forces LLM to process everything

**Solution:** Save to disk, read selectively
- Zero context pollution on fetch
- Use Read/Grep to view exactly what you need
- Can work with multiple filings simultaneously
- Filings persist between sessions

**The Bitter Lesson:** Scale (disk) beats cleverness (context).

## Development

```bash
# Install dependencies
poetry install

# Run tests
make test

# Dev mode (auto-restart)
make dev

# Clean cache
make clean
```

## Architecture

**Separation of concerns:**

- `bitter_edgar/core.py` - Pure business logic
  - `FilingCache` class (disk management)
  - `EdgarFetcher` class (SEC API)
  - Pure functions (no global state)

- `bitter_edgar/server.py` - MCP delivery
  - MCP tool decorators
  - Transport config (stdio/HTTP)
  - Thin wrapper around core

**Benefits:**
- Core is testable without MCP
- Server is just delivery
- Can swap delivery layer (REST, CLI, etc.)

## Credits

Inspired by [sec-edgar-mcp](https://github.com/stefanoamorelli/sec-edgar-mcp)
Built with [edgartools](https://github.com/dgunning/edgartools)
Named after [The Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html) by Rich Sutton

## License

MIT
