# bitter-edgar

*Scale beats cleverness. Save to disk, read what you need.*

MCP server for SEC filings that returns file paths, not content.

## The Bitter Lesson

Current SEC MCPs dump 241K tokens into your context per filing. This is the clever approach.

The bitter lesson: Just save to disk. Use Read/Grep/Bash. Scale storage, not prompts.

## Tools

- `fetch_filing(ticker, form_type)` → Downloads filing, returns path
- `list_cached()` → What's on disk
- `extract_section(path, section)` → Save Item 1A, 7, etc. to separate file

## Usage

```python
# Fetch Tesla's latest 10-K (saves to disk)
fetch_filing("TSLA", "10-K")
→ {path: "/tmp/sec-filings/TSLA/10-K/2025-01-30.md"}

# Read just the part you need
Read("/tmp/sec-filings/TSLA/10-K/2025-01-30.md", offset=1200, limit=50)

# Zero context waste. Scale > cleverness.
```

## Credits

Inspired by [sec-edgar-mcp](https://github.com/stefanoamorelli/sec-edgar-mcp)
Built with [edgartools](https://github.com/dgunning/edgartools)
Named after [The Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html) by Rich Sutton

## License

MIT
