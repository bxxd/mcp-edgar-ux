.PHONY: install start stop restart status logs run-http run-stdio test clean

# Install dependencies
install:
	poetry install

# Start as background daemon (HTTP)
start:
	./run.sh start

# Stop daemon
stop:
	./run.sh stop

# Restart daemon
restart:
	./run.sh restart

# Check daemon status
status:
	./run.sh status

# Tail logs
logs:
	./run.sh logs

# Run HTTP server (foreground, for testing)
run-http:
	poetry run bitter-edgar --transport streamable-http --port 8080

# Run stdio (for Claude Code MCP)
run-stdio:
	poetry run bitter-edgar --transport stdio

# Test fetch_filing
test:
	poetry run python -c "from bitter_edgar.server import fetch_filing; import json; print(json.dumps(fetch_filing('TSLA', '10-K'), indent=2))"

# Clean cache
clean:
	rm -rf /tmp/sec-filings

# Show cache contents
show-cache:
	ls -lhR /tmp/sec-filings || echo "Cache empty"
