# edgar-lite-mcp MCP Development Tasks

## Design Goals

**Principle**: Design for human analysts (BBG Lite), Claude benefits automatically
**Pattern**: Mirror Glob → Grep → Read workflow (familiar to Claude)
**Async**: All core functions async (one right path, Starlette-compatible)

## Tool Design (Final)

### 1. `list_filings(ticker, form_type)` - DISCOVERY
**Purpose**: Show available filings (both cached + available from SEC)
**Like**: Glob (discover what exists)
**Returns**: Table with cached indicator, dates, sizes
**Output**: BBG Lite formatted table

```
TSLA 10-K FILINGS AVAILABLE
────────────────────────────────────────────────────────────────────
FILED       CACHED  SIZE     [ACTIONS]
2025-04-30  ✓       423 KB   fetch_filing("TSLA", "10-K", "2025-04-30")
2024-01-29  ✓       790 KB
2023-01-31          -        fetch_filing("TSLA", "10-K", "2023-01-31")
2022-02-07          -
...

Try: fetch_filing(ticker, form, date) | search_filing(ticker, form, pattern)
```

### 2. `fetch_filing(ticker, form_type, date=None, preview_lines=50)` - DOWNLOAD + PREVIEW
**Purpose**: Download filing (if not cached) + show preview
**Like**: Download + head -n 50
**Returns**: Path + first N lines + metadata
**Output**: BBG Lite formatted preview

```
TSLA 10-K/A | 2025-04-30 | FETCHED (cached)

COMPANY:     Tesla, Inc.
FORM:        10-K/A
FILED:       2025-04-30
SIZE:        423 KB (5,819 lines)

PATH: /var/idio-mcp-cache/sec-filings/TSLA/10-K/2025-04-30.txt

PREVIEW (first 50 lines):
────────────────────────────────────────────────────────────────────
     1→                                 UNITED STATES
     2→                       SECURITIES AND EXCHANGE COMMISSION
     3→                             Washington, D.C. 20549
...
    50→

Try: search_filing("TSLA", "10-K", "supply chain") | Read(path, offset=100, limit=100)
```

### 3. `search_filing(ticker, form_type, pattern, context_lines=2, max_results=20)` - CONTENT SEARCH
**Purpose**: Search within filing (auto-downloads if not cached)
**Like**: Grep with line numbers
**Returns**: Matches with context + line numbers
**Output**: BBG Lite formatted search results (already implemented)

```
TSLA 10-K | 2025-04-30 | SEARCH "vehicle"

MATCHES (5 found | 5,819 lines)
────────────────────────────────────────────────────────────────────
     648→  ·  Model Y was the best-selling vehicle, of any kind...

PATH: /var/idio-mcp-cache/sec-filings/TSLA/10-K/2025-04-30.txt
Try: Read(path, offset=648, limit=50)
```

## Implementation Tasks

### Phase 1: Core Async Conversion (COMPLETE)
- [x] Convert `fetch_filing()` to async
- [x] Convert `search_filing()` to async
- [x] Convert `list_cached_filings()` to async
- [x] Update server_http.py to await async calls
- [x] Update CLI to await async calls
- [x] Test async implementation works

### Phase 2: Add SEC API Integration (COMPLETE)
- [x] Add `EdgarFetcher.list_available()` to query SEC for available filings (not just cached)
- [x] Returns list of available filings with metadata (date, form, accession number)
- [x] Add `list_filings()` core function to merge cached + available
- [x] Add `format_filings_list()` BBG Lite formatter
- [x] Add CLI command `list-filings`
- [x] Test list-filings command

### Phase 3: Update `fetch_filing` Tool (COMPLETE)
- [x] Add `preview_lines` parameter (default: 50)
- [x] Add `_read_preview()` helper function with line numbers
- [x] Return preview in BBG Lite format (first N lines with line numbers)
- [x] Update formatter: `format_filing_result()` to include preview
- [x] Test fetch with preview
- [ ] Update MCP tool description (clear, example-driven)

### Phase 4: Create `list_filings` Tool (COMPLETE - done in Phase 2)
- [x] New core function: `list_filings(ticker, form_type)`
- [x] Combines cached + SEC available filings
- [x] New formatter: `format_filings_list()` (BBG Lite table)
- [x] Add to CLI with `list-filings` command
- [ ] Add to MCP tools in server_http.py

### Phase 5: MCP Tool Consolidation (COMPLETE)
- [x] Four tools: `fetch_filing` (with preview), `search_filing`, `list_filings`, `list_cached`
- [x] Update fetch_filing tool description (mentions preview)
- [x] Add list_filings MCP tool (discovery tool)
- [x] Add list_filings tool handler
- [x] Add preview_lines parameter to fetch_filing handler
- [x] Keep list_cached for cache inspection
- [x] Tool descriptions clear and example-driven
- [x] Affordances present in all formatters

### Phase 6: CLI Updates (COMPLETE)
- [x] Update CLI to match new async signatures
- [x] Commands: `list`, `list-filings`, `fetch`, `search`
- [x] Test commands work correctly

### Phase 7: Testing (IN PROGRESS)
- [x] Test async implementation (Phase 1)
- [x] Test list-filings CLI command (shows cached + available)
- [x] Test fetch with preview (shows first 50 lines)
- [x] Test search_filing (already works)
- [ ] Test MCP server with new tools
- [ ] Test full workflow end-to-end via MCP

## BBG Lite Design Principles

From `meta/BBG_LITE_DESIGN_SYSTEM.md`:
1. **Hierarchy through layout** - position and spacing convey importance
2. **Density without clutter** - every character earns its keep
3. **Consistency breeds speed** - similar data looks similar
4. **Context is self-evident** - outputs understandable in isolation
5. **Progressive disclosure** - summary first, depth via separate calls
6. **Guidance in context** - Show what's possible next (affordances)

## Async Architecture

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

## Future Enhancements (Post-MVP)

- **FAISS indexing**: Semantic search across filings
- **Cross-filing analysis**: Search all TSLA filings at once
- **Trend detection**: Compare 10-K sections year-over-year
- **Background indexing**: Pre-build indexes when filing cached

## alpha-server Integration (Future)

**Two interfaces:**
1. **MCP proxy** (`/api/edgar/*`): Same outputs Claude sees
2. **File manager** (`/api/files/sec-filings/*`): Browse/download cached files

**Shared experience**: Both human and Claude work on `/var/idio-mcp-cache/sec-filings/`

## Notes

- Cache location: `/var/idio-mcp-cache/sec-filings/` (shared, public data)
- Format: Text preferred (scales), markdown as fallback
- SEC rate limit: 10 req/sec (Python is fine, network is bottleneck)
- Keep Python stack (edgartools is too good to replace)
