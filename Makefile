.PHONY: install run-http run-stdio stop test clean

# Install dependencies
install:
	poetry install

# Run HTTP server (for development/iteration)
run-http:
	poetry run bitter-edgar --transport streamable-http --port 8080

# Run stdio (for Claude Code MCP)
run-stdio:
	poetry run bitter-edgar --transport stdio

# Stop any running servers
stop:
	pkill -f "bitter-edgar" || true

# Test fetch_filing
test:
	poetry run python -c "from bitter_edgar.server import fetch_filing; import json; print(json.dumps(fetch_filing('TSLA', '10-K'), indent=2))"

# Clean cache
clean:
	rm -rf /tmp/sec-filings

# Show cache contents
show-cache:
	ls -lhR /tmp/sec-filings || echo "Cache empty"
