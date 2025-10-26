#!/usr/bin/env python3
"""
Dev mode runner for edgar-lite-mcp

Watches for file changes and auto-restarts server.
"""
import subprocess
import sys
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ServerRestartHandler(FileSystemEventHandler):
    """Restarts server on Python file changes."""

    def __init__(self):
        self.process = None
        self.start_server()

    def start_server(self):
        """Start the server process."""
        if self.process:
            print("Stopping server...")
            self.process.terminate()
            self.process.wait()

        print("Starting server...")
        self.process = subprocess.Popen(
            ["poetry", "run", "edgar-lite-mcp", "--transport", "streamable-http", "--port", "8080"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        print(f"Server started (PID: {self.process.pid})")
        print("Watching for changes...")

    def on_modified(self, event):
        """Handle file modification events."""
        if event.src_path.endswith('.py'):
            print(f"\n{event.src_path} changed - restarting...")
            time.sleep(0.1)  # Debounce
            self.start_server()

    def stop(self):
        """Stop the server process."""
        if self.process:
            self.process.terminate()
            self.process.wait()


def main():
    """Run dev server with auto-restart."""
    print("edgar-lite-mcp dev mode")
    print("Ctrl+C to stop\n")

    # Set up file watcher
    handler = ServerRestartHandler()
    observer = Observer()
    observer.schedule(handler, str(Path("edgar_lite_mcp")), recursive=True)
    observer.start()

    try:
        # Stream server output
        while True:
            if handler.process:
                line = handler.process.stdout.readline()
                if line:
                    print(line, end='')
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping dev server...")
        observer.stop()
        handler.stop()

    observer.join()


if __name__ == "__main__":
    main()
