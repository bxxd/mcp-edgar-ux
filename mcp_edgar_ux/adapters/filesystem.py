"""
Filesystem Cache Adapter

Implements FilingRepository port using local filesystem.
"""
import re
from pathlib import Path
from typing import Optional

from ..core.domain import CachedFiling, FilingContent
from ..core.ports import FilingRepository
from .edgar import CORE_FORM_TYPES


class FilesystemCache(FilingRepository):
    """Filesystem-based filing cache"""

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir)

    def _sanitize_form_type(self, form_type: str) -> str:
        """Sanitize form type for use as directory name (replace / and space with _)"""
        return form_type.upper().replace('/', '_').replace(' ', '_')

    def _form_dir(self, ticker: str, form_type: str) -> Path:
        """Directory holding one ticker's filings of one form type."""
        return self.cache_dir / ticker.upper() / self._sanitize_form_type(form_type)

    @staticmethod
    def _stem(filing_date: str, accession_number: str) -> str:
        """Filename stem: date first so the directory sorts chronologically.

        The accession number is what makes it unique. A company files more than
        once a day routinely, so the date alone addresses two filings at once.
        """
        return f"{filing_date}-{accession_number}"

    @staticmethod
    def _split_stem(stem: str) -> tuple[str, str]:
        """Inverse of _stem: (filing_date, accession_number)."""
        return stem[:10], stem[11:]

    def _get_path(
        self,
        ticker: str,
        form_type: str,
        filing_date: str,
        accession_number: str,
        format: str,
        document: Optional[str] = None
    ) -> Path:
        """Get path for cached filing.

        Primary documents are {DATE}-{ACCESSION}.{ext}. Named documents from an
        accession go one level down ({DATE}-{ACCESSION}/{document}) so list_all,
        which reads a filename stem, never mistakes one for a filing.

        Pure — creates nothing. Only save() writes.
        """
        form_dir = self._form_dir(ticker, form_type)
        stem = self._stem(filing_date, accession_number)
        if document:
            return form_dir / stem / Path(document).name
        ext = {"markdown": ".md", "text": ".txt", "html": ".html", "xml": ".xml"}[format]
        return form_dir / f"{stem}{ext}"

    def get(
        self,
        ticker: str,
        form_type: str,
        filing_date: str,
        accession_number: str,
        format: str,
        document: Optional[str] = None
    ) -> Optional[Path]:
        """Get path to cached filing if it exists"""
        path = self._get_path(
            ticker, form_type, filing_date, accession_number, format, document
        )
        return path if path.exists() else None

    def save(self, content: FilingContent) -> Path:
        """Save filing content to cache, return path"""
        filing = content.filing
        path = self._get_path(
            filing.ticker,
            filing.form_type,
            filing.filing_date,
            filing.accession_number,
            content.format,
            content.document
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.content, encoding='utf-8')
        return path

    def list_all(
        self,
        ticker: Optional[str] = None,
        form_type: Optional[str] = None
    ) -> list[CachedFiling]:
        """List all cached filings, optionally filtered"""
        if not self.cache_dir.exists():
            return []

        filings = []
        for ticker_dir in self.cache_dir.iterdir():
            if not ticker_dir.is_dir():
                continue
            if ticker and ticker_dir.name.upper() != ticker.upper():
                continue

            for form_dir in ticker_dir.iterdir():
                if not form_dir.is_dir():
                    continue
                # Handle special form_type filters
                # Directory names have / and space replaced with _ (sanitized)
                dir_form_type = form_dir.name.upper()
                if form_type:
                    if form_type.upper() == 'ALL':
                        pass  # Include all form types
                    elif form_type.upper() == 'CORE':
                        # Compare sanitized directory name against sanitized CORE_FORM_TYPES
                        sanitized_core = {f.upper().replace('/', '_').replace(' ', '_') for f in CORE_FORM_TYPES}
                        if dir_form_type not in sanitized_core:
                            continue
                    elif dir_form_type != self._sanitize_form_type(form_type):
                        continue

                for file_path in form_dir.iterdir():
                    if file_path.is_file() and file_path.suffix in ['.md', '.txt', '.html', '.xml']:
                        stat = file_path.stat()
                        filing_date, accession_number = self._split_stem(file_path.stem)
                        filings.append(CachedFiling(
                            ticker=ticker_dir.name,
                            form_type=dir_form_type,  # Use unsanitized form type (e.g., "10-K/A" not "10-K_A")
                            filing_date=filing_date,
                            accession_number=accession_number,
                            path=file_path,
                            size_bytes=stat.st_size,
                            format=file_path.suffix[1:]
                        ))

        # Sort by date descending
        filings.sort(key=lambda x: x.filing_date, reverse=True)
        return filings

    def get_disk_usage(self) -> int:
        """Get total disk usage in bytes"""
        if not self.cache_dir.exists():
            return 0

        total = 0
        for ticker_dir in self.cache_dir.iterdir():
            if not ticker_dir.is_dir():
                continue
            for form_dir in ticker_dir.iterdir():
                if not form_dir.is_dir():
                    continue
                # rglob, not iterdir: named documents live one level down under
                # {DATE}-{ACCESSION}/ and are exactly what this needs to count.
                for file_path in form_dir.rglob('*'):
                    if file_path.is_file():
                        total += file_path.stat().st_size
        return total

    def resolve(self, path: str) -> Path:
        """Resolve a caller's path to a file or folder inside the cache.

        Path is the key: fetch_filing, search_filing and list_filings all hand
        one back, and read()/grep() take it. The cache lives on this server, so
        a remote agent cannot open it itself. Anything that resolves outside
        the cache root (../, an absolute path elsewhere, a symlink out) is
        refused, so these verbs read filings and nothing else on the host.
        """
        root = self.cache_dir.resolve()
        raw = Path(path.strip())
        candidate = (raw if raw.is_absolute() else root / raw).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError(f"path is outside the filing cache ({self.cache_dir}): {path}")
        if not candidate.exists():
            raise FileNotFoundError(
                f"not in the cache: {path} (fetch_filing() or search_filing() downloads it)"
            )
        return candidate

    def files_under(self, path: Path) -> list[Path]:
        """Every text file at or under path, newest first.

        Every cached file carries its filing date — in its own name, or in
        its accession folder's name for a named document — so files sort by
        that date across form folders. Binary files (images riding along in
        an accession) are skipped: they have no lines to match.
        """
        if path.is_file():
            return [path]
        files = [f for f in path.rglob('*') if f.is_file() and not _is_binary(f)]
        return sorted(files, key=_newest_first_key, reverse=True)

    def exists(
        self,
        ticker: str,
        form_type: str,
        filing_date: str,
        accession_number: str,
        format: str
    ) -> bool:
        """Check if filing is cached"""
        path = self._get_path(
            ticker, form_type, filing_date, accession_number, format
        )
        return path.exists()


def _is_binary(path: Path) -> bool:
    """A NUL byte in the first 8 KB marks a file as binary (grep's own rule)."""
    try:
        with open(path, 'rb') as f:
            return b'\0' in f.read(8192)
    except OSError:
        return True


# Anchored to the start of a path component: an accession number
# (0001045810-26-000075) holds a date-shaped run of its own.
_FILING_DATE = re.compile(r"(?:^|/)(\d{4}-\d{2}-\d{2})")


def _newest_first_key(path: Path) -> tuple[str, str]:
    """(filing date, path): the date that starts the last dated path component."""
    dates = _FILING_DATE.findall(str(path))
    return (dates[-1] if dates else "", str(path))

