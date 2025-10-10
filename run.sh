#!/bin/bash
# bitter-edgar runner script

set -e

# Default config
TRANSPORT="${BITTER_EDGAR_TRANSPORT:-streamable-http}"
PORT="${BITTER_EDGAR_PORT:-8080}"
HOST="${BITTER_EDGAR_HOST:-0.0.0.0}"
CACHE_DIR="${BITTER_EDGAR_CACHE_DIR:-/tmp/sec-filings}"
LOG_FILE="${BITTER_EDGAR_LOG:-/tmp/bitter-edgar.log}"
PID_FILE="${BITTER_EDGAR_PID:-/tmp/bitter-edgar.pid}"

CMD="$1"

function start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "bitter-edgar already running (PID: $PID)"
            exit 1
        fi
    fi

    echo "Starting bitter-edgar..."
    echo "  Transport: $TRANSPORT"
    echo "  Port: $PORT"
    echo "  Cache: $CACHE_DIR"
    echo "  Log: $LOG_FILE"

    nohup poetry run bitter-edgar \
        --transport "$TRANSPORT" \
        --host "$HOST" \
        --port "$PORT" \
        --cache-dir "$CACHE_DIR" \
        > "$LOG_FILE" 2>&1 &

    PID=$!
    echo $PID > "$PID_FILE"
    echo "Started bitter-edgar (PID: $PID)"
    echo "Logs: tail -f $LOG_FILE"
}

function stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "bitter-edgar not running (no PID file)"
        exit 1
    fi

    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping bitter-edgar (PID: $PID)..."
        kill "$PID"
        rm -f "$PID_FILE"
        echo "Stopped"
    else
        echo "bitter-edgar not running (stale PID file)"
        rm -f "$PID_FILE"
    fi
}

function status() {
    if [ ! -f "$PID_FILE" ]; then
        echo "bitter-edgar is not running"
        exit 1
    fi

    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "bitter-edgar is running (PID: $PID)"
        echo "URL: http://$HOST:$PORT"
        echo "Logs: $LOG_FILE"
    else
        echo "bitter-edgar not running (stale PID file)"
        rm -f "$PID_FILE"
        exit 1
    fi
}

function logs() {
    tail -f "$LOG_FILE"
}

function restart() {
    stop || true
    sleep 1
    start
}

case "$CMD" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Environment variables:"
        echo "  BITTER_EDGAR_TRANSPORT=streamable-http (or stdio)"
        echo "  BITTER_EDGAR_PORT=8080"
        echo "  BITTER_EDGAR_HOST=0.0.0.0"
        echo "  BITTER_EDGAR_CACHE_DIR=/tmp/sec-filings"
        echo "  BITTER_EDGAR_LOG=/tmp/bitter-edgar.log"
        echo "  BITTER_EDGAR_PID=/tmp/bitter-edgar.pid"
        exit 1
        ;;
esac
