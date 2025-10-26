# CLAUDE.md - edgar-lite-mcp MCP Context

MCP server for SEC EDGAR filings with BBG Lite formatted output.

**Project documentation:**
```
@DEVELOPER.md
```

See `DEVELOPER.md` for complete architecture, tool design, and implementation details.

## Quick Reference

**Repository**: https://github.com/bxxd/idio-edgar-mcp

**Four MCP Tools**:
1. `list_filings(ticker, form_type)` - Discovery (cached + available from SEC)
2. `fetch_filing(ticker, form_type, date=None, preview_lines=50)` - Download + preview
3. `search_filing(ticker, form_type, pattern)` - Content search (grep-like)
4. `list_cached(ticker=None, form_type=None)` - Cache inspection

**Workflow Pattern** (mirrors Glob → Grep → Read):
```python
list_filings("TSLA", "10-K")           # Discover
fetch_filing("TSLA", "10-K")           # Download + preview (first 50 lines)
search_filing("TSLA", "10-K", "risk")  # Search
Read(path, offset, limit)              # Deep dive
```

**Design Philosophy**:
- Design for humans (BBG Lite), AI benefits automatically
- Progressive disclosure (summary first, depth via separate calls)
- The Bitter Lesson (don't dump 241K tokens, save to disk)

**Development**:
```bash
./cli list-filings TSLA 10-K     # Test CLI (fast iteration)
make server                       # Start MCP server
make logs                         # Tail server logs
./dev.py                          # Auto-restart on changes
```

**Implementation Status**: Phases 1-6 complete (see TASKS.md)
- ✅ Async architecture
- ✅ SEC API integration
- ✅ Preview functionality
- ✅ BBG Lite formatting
- 🔄 Testing (in progress)

**Key Files**:
- `DEVELOPER.md` - Complete architecture and patterns
- `TASKS.md` - 7-phase implementation roadmap
- `edgar_lite_mcp/core.py` - Pure async business logic
- `edgar_lite_mcp/server_http.py` - MCP HTTP/SSE server
- `edgar_lite_mcp/cli.py` - CLI for testing

**Note**: Package currently named `edgar_lite_mcp` (philosophical reference to "The Bitter Lesson"). Consider renaming to `edgar_mcp` for clarity.
