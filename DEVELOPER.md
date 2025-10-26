# bitter-edgar MCP - Developer Context

MCP server for SEC EDGAR filings with Bloomberg Terminal-inspired formatted output.

**Public Repository**

---

## Overview

**SEC filing research tool for investment analysis.**

MCP (Model Context Protocol) server that provides programmatic access to SEC EDGAR filings with human-readable formatted output.

**Design Philosophy:**
- **Design for humans, AI benefits automatically** - BBG Terminal-inspired text formatting
- **Progressive disclosure** - Summary first, depth via separate calls
- **The Bitter Lesson** - Don't dump 241K tokens into context, save to disk and read what you need

**Workflow Pattern** (mirrors `Glob → Grep → Read`):
```python
# 1. Discover (like Glob)
list_filings("TSLA", "10-K")
→ Shows 20 years of 10-Ks, indicates which are cached

# 2. Download + Preview (like Download + head)
fetch_filing("TSLA", "10-K", "2024-01-29")
→ Downloads filing, shows first 50 lines, returns path

# 3. Search (like Grep)
search_filing("TSLA", "10-K", "supply chain")
→ Shows all "supply chain" mentions with line numbers and context

# 4. Deep Dive (use Read/Grep/Bash tools on cached path)
Read(path, offset=648, limit=50)
Grep("rare earth", path=cached_path)
```

---

## Architecture

### Stack

```
Python 3.11+
├── edgartools     → SEC EDGAR API (mature, handles SEC quirks)
├── mcp            → Model Context Protocol (stdio + SSE transports)
├── starlette      → Async web framework (SSE server)
├── markdownify    → HTML → Markdown conversion
└── BeautifulSoup  → XBRL/XML tag stripping
```

### Project Structure

```
bitter-edgar/
├── bitter_edgar/
│   ├── core.py          → Pure async business logic (fetch, search, list)
│   ├── server_http.py   → MCP HTTP/SSE server (Starlette)
│   └── cli.py           → CLI for testing tools (no MCP restart needed)
├── cli                  → Wrapper script (poetry run python -m bitter_edgar.cli)
├── dev.py               → Dev mode with auto-restart (watchdog)
├── TASKS.md             → Implementation roadmap (Phases 1-7)
├── DEVELOPER.md         → This file
└── CLAUDE.md            → Workspace context
```

### Async Architecture

**Pattern**: Sync blocking operations run in thread pool

```python
# Network I/O (edgartools is sync)
result = await asyncio.to_thread(fetcher.fetch_latest, ticker, form_type)

# Subprocess (grep is blocking)
result = await asyncio.to_thread(subprocess.run, grep_args, ...)

# File I/O (reading/writing cache)
path = await asyncio.to_thread(cache.save, ...)
```

**Why**: Keeps server responsive, allows concurrent MCP requests

### MCP Tools (4 tools)

**1. `list_filings(ticker, form_type)` - DISCOVERY**
- Like `Glob` (discover what exists)
- Shows available filings (both cached + available from SEC)
- Returns: Table with cached indicator (✓), dates, sizes

**2. `fetch_filing(ticker, form_type, date=None, preview_lines=50)` - DOWNLOAD + PREVIEW**
- Like `Download + head -n 50`
- Downloads filing (if not cached) + shows first N lines
- Returns: Path + preview with line numbers + metadata

**3. `search_filing(ticker, form_type, pattern, context_lines=2)` - CONTENT SEARCH**
- Like `Grep` with line numbers
- Searches within filing (auto-downloads if not cached)
- Returns: Matches with context + line numbers

**4. `list_cached(ticker=None, form_type=None)` - CACHE INSPECTION**
- Internal tool for cache management
- Shows what's already downloaded

### Cache Strategy

**Default Location**: `/var/idio-mcp-cache/sec-filings/`
**Configurable**: Set `CACHE_DIR` environment variable

**Organization**: `/{TICKER}/{FORM}/{YYYY-MM-DD}.{ext}`
**Formats**: `.txt` (preferred), `.md`, `.html`

---

## BBG Lite Design System

**Six Principles**:

1. **Hierarchy through layout** - Position and spacing convey importance
2. **Density without clutter** - Every character earns its keep
3. **Consistency breeds speed** - Similar data looks similar
4. **Context is self-evident** - Outputs understandable in isolation
5. **Progressive disclosure** - Summary first, depth via separate calls
6. **Guidance in context** - Show what's possible next (affordances)

**Example Output**:

```
TSLA 10-K FILINGS AVAILABLE
──────────────────────────────────────────────────────────────────────
FILED       CACHED  SIZE     [ACTIONS]
2025-04-30  ✓       423 KB
2025-01-30  ✓       313 KB
2024-01-29  ✓       814 KB
2023-01-31          -

Showing 15 of 20 filings (3 cached)

Try: fetch_filing(ticker, form, date) | search_filing(ticker, form, pattern)
```

**Key Features**:
- Dense, scannable tables
- Clear section headers
- Affordances ("Try:") show next steps
- Line numbers match Read tool format (6 digits + →)
- Professional, terminal-friendly aesthetic

---

## Development Workflow

### Quick Start

```bash
# Install dependencies
poetry install

# Run CLI (fast iteration, no server restart)
./cli list-tools                        # Show MCP tool definitions
./cli list-filings TSLA 10-K            # List available filings
./cli fetch TSLA 10-K                   # Fetch with preview
./cli search TSLA 10-K "vehicle"        # Search filing

# Run MCP server (for Claude Code integration)
make server                             # Start on port 5002
make logs                               # Tail server logs
make kill                               # Stop server

# Development mode (auto-restart on changes)
./dev.py                                # Watchdog-based auto-restart
```

### Testing Pattern

**1. Test CLI first** (fastest iteration):
```bash
./cli fetch TSLA 10-K --date 2024-01-29
./cli search TSLA 10-K "supply chain" --context 3
```

**2. Test MCP server** (via stdio transport):
```bash
poetry run python -m bitter_edgar.server --transport stdio
# Test with MCP inspector or Claude Code
```

**3. Test HTTP/SSE server** (for web integration):
```bash
poetry run uvicorn bitter_edgar.server_http:app --host 127.0.0.1 --port 5002
curl http://127.0.0.1:5002/health
```

### Code Quality

**Before committing**:
```bash
# Format
poetry run black bitter_edgar/

# Type check
poetry run mypy bitter_edgar/

# Lint
poetry run ruff check bitter_edgar/
```

### Cache Configuration

**Default**: `/var/idio-mcp-cache/sec-filings/`
**Override**: Set `CACHE_DIR` environment variable

```bash
# Test with isolated cache
CACHE_DIR=/tmp/sec-filings-test ./cli fetch TSLA 10-K
```

---

## Tool Design Principles

### "UI not API" Principle

**Philosophy**: Tools return human-readable formatted output, not raw data

**Pattern**:
- Same output humans see = same output AI sees
- Iterate tool design based on human validation
- If formatted output is useful to humans → useful to AI

### Progressive Disclosure

**Philosophy**: Don't dump entire 200-page filing into context

**Pattern**:
- Return path + preview (first 50 lines)
- User/AI decides what to read next (Read/Grep/Bash)
- This scales: filing size doesn't matter

### Affordances

**Philosophy**: Every tool output shows "Try: ..." with next steps

**Example**: `Try: search_filing("TSLA", "10-K", "SEARCH TERM")`

**Why**: Guides AI toward effective research workflows

---

## Implementation Roadmap

See `TASKS.md` for complete 7-phase roadmap.

**Status**: Phases 1-6 complete, Phase 7 (testing) in progress

**Phase 1**: Core Async Conversion ✅
- All core functions async
- asyncio.to_thread() for blocking I/O

**Phase 2**: SEC API Integration ✅
- list_available() queries SEC
- list_filings() merges cached + available

**Phase 3**: Fetch Filing with Preview ✅
- preview_lines parameter
- First N lines with line numbers

**Phase 4**: Create list_filings Tool ✅
- Discovery tool for available filings

**Phase 5**: MCP Tool Consolidation ✅
- Four tools: fetch, search, list_filings, list_cached
- Clear descriptions, affordances

**Phase 6**: CLI Updates ✅
- Commands: list-tools, fetch, search, list, list-filings

**Phase 7**: Testing (In Progress)
- CLI tested ✅
- MCP server testing next

---

## Philosophy

### KISS (Keep It Simple, Stupid)
- Python is appropriate (network I/O is bottleneck, not Python)
- edgartools is too valuable to replace (handles SEC quirks)
- Text format scales (vs. clever markdown with XBRL issues)

### Detective Debugging
- Investigate first, implement second
- Form theories, gather evidence from logs/errors
- Follow the data, don't rush to code

### Divide the World (Separation of Concerns)
- `core.py` = Pure business logic (no MCP, no HTTP)
- `server_http.py` = MCP protocol (thin wrapper)
- `cli.py` = Testing interface (no MCP restart needed)

### DRY (Don't Repeat Yourself)
- Single BBG Lite formatter per output type
- Formatters shared between CLI and MCP server
- One true path: asyncio.to_thread() for all blocking I/O

### The Bitter Lesson (Rich Sutton)
- Scale > cleverness
- Build systems that improve with data/compute
- Don't dump 241K tokens into context
- Save to disk, read what you need
- [The Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)

---

## Common Patterns

### Adding a New Tool

1. **Add core function to core.py** (pure async, no MCP):
```python
async def new_tool(param: str, cache_dir: str = "/tmp/sec-filings") -> Dict[str, Any]:
    # Business logic here (use asyncio.to_thread for blocking I/O)
    return {"success": True, "data": ...}
```

2. **Add formatter to server_http.py** (BBG Lite design):
```python
def format_new_tool_result(result: dict) -> str:
    # Dense, scannable output with affordances
    lines = [
        "HEADER",
        "─" * 70,
        "Data here",
        "",
        "Try: next_step(...)"
    ]
    return "\n".join(lines)
```

3. **Add MCP tool definition** (in list_tools()):
```python
Tool(
    name="new_tool",
    description="Clear description with examples",
    inputSchema={...}
)
```

4. **Add tool handler** (in call_tool()):
```python
if name == "new_tool":
    result = await core_new_tool(...)
    formatted = format_new_tool_result(result)
    return [TextContent(type="text", text=formatted)]
```

5. **Add CLI command** (in cli.py):
```python
async def new_tool_command(...) -> int:
    result = await core_new_tool(...)
    output = format_new_tool_result(result)
    print(output)
    return 0
```

6. **Test via CLI first**:
```bash
./cli new-tool PARAM
```

### Debugging Async Issues

**Pattern**: Use print statements with flush=True
```python
print(f"[DEBUG] Starting operation: {param}", flush=True)
result = await asyncio.to_thread(blocking_function, param)
print(f"[DEBUG] Completed: {result}", flush=True)
```

**Why**: Async can interleave logs, flush=True ensures immediate output

### BBG Lite Formatting Checklist

- [ ] Dense, scannable layout
- [ ] Clear section headers (uppercase + separators)
- [ ] Consistent column widths
- [ ] Line numbers (if showing file content): `  1234→content`
- [ ] Affordances ("Try:") at end
- [ ] Professional tone
- [ ] Context-independent (readable in isolation)

---

## Future Enhancements (Post-MVP)

**FAISS Indexing**:
- Semantic search across filings
- "Find all mentions of supply chain risk across 10 years of 10-Ks"
- Background indexing when filing cached

**Cross-Filing Analysis**:
- Search all TSLA filings at once
- Track narrative changes over time

**Trend Detection**:
- Compare 10-K sections year-over-year
- Flag new risk disclosures
- Track management tone shifts

---

## Key Files

**Core Implementation**:
- `bitter_edgar/core.py` - Business logic (fetch, search, list)
- `bitter_edgar/server_http.py` - MCP HTTP/SSE server
- `bitter_edgar/cli.py` - CLI for testing

**Documentation**:
- `TASKS.md` - Implementation roadmap (7 phases)
- `DEVELOPER.md` - This file (architecture, patterns)
- `CLAUDE.md` - Workspace context (references this file)

**Development**:
- `dev.py` - Auto-restart server on file changes
- `Makefile` - Server management (start, stop, logs)

**Configuration**:
- `pyproject.toml` - Poetry dependencies
- `.gitignore` - Excludes logs/, __pycache__, etc.

---

## MCP Protocol Notes

**Transports Supported**:
- `stdio` - Standard input/output (for Claude Code integration)
- `streamable-http` - HTTP/SSE (for web integration)

**Tool Discovery**:
- MCP clients call `list_tools()` to discover available tools
- Returns Tool objects with name, description, inputSchema

**Tool Execution**:
- Client calls `call_tool(name, arguments)`
- Server executes tool, returns list of TextContent
- All output is human-readable formatted text (BBG Lite)

**Error Handling**:
- Tools return `{"success": False, "error": "message"}` on failure
- Formatters display errors in consistent format
- No exceptions leak to client

---

## Contributing

**Before submitting PR**:
1. Test via CLI: `./cli <command>` works
2. Code quality: `poetry run black . && poetry run mypy . && poetry run ruff check .`
3. Update TASKS.md if adding features
4. Add examples to tool descriptions
5. Ensure BBG Lite formatting consistency

**Design Principles to Follow**:
- Design for humans, AI benefits automatically
- Progressive disclosure (summary first, depth via separate calls)
- Affordances (show next steps in output)
- The Bitter Lesson (scale > cleverness)
