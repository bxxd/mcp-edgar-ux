"""
Adapters - External implementations of ports

This package contains implementations of the core ports:
- filesystem.py: Filesystem-based filing cache
- edgar.py: EDGAR/edgartools filing fetcher
- search.py: Grep-based file searcher
"""
from .filesystem import FilesystemCache
from .edgar import EdgarAdapter
from .search import GrepSearcher

__all__ = [
    "FilesystemCache",
    "EdgarAdapter",
    "GrepSearcher",
]
