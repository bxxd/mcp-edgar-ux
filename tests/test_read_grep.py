"""
Tests for read() and grep(): the cache served over MCP, addressed by path.

These exist because the cache lives on the server. fetch_filing hands back a
path, and an agent on another host (or in a walled container) cannot open it:
the hint said Read(path) and the file was not there. read() and grep() let the
server read for it. The path is the key, and nothing outside the cache root
may be reached through it.

Drives the real services against the real FilesystemCache and GrepSearcher
(ugrep). No network.
"""
import asyncio
import shutil
from pathlib import Path

import pytest

from mcp_edgar_ux.adapters.filesystem import FilesystemCache
from mcp_edgar_ux.adapters.mcp import MCPHandlers
from mcp_edgar_ux.adapters.search import GrepSearcher
from mcp_edgar_ux.core.services import (
    GREP_MAX_FILES,
    MAX_LINE_CHARS,
    READ_MAX_LINES,
    GrepService,
    ReadFileService,
)
from mcp_edgar_ux.container import Container
from mcp_edgar_ux.formatters import format_grep, format_read

pytestmark = pytest.mark.skipif(shutil.which("ugrep") is None, reason="ugrep not installed")


@pytest.fixture
def cache(tmp_path: Path) -> Path:
    root = tmp_path / "sec-filings"
    q = root / "NVDA" / "10-Q"
    q.mkdir(parents=True)
    (q / "2026-08-26-0001045810-26-000075.txt").write_text(
        "".join(f"line {n}\n" for n in range(1, 101))
        + "enterprises, research organizations and sovereign customers\n"
    )
    (q / "2026-05-28-0001045810-26-000050.txt").write_text(
        "header\nsovereign AI demand grew\nfooter\n"
    )
    k = root / "NVDA" / "10-K"
    k.mkdir(parents=True)
    (k / "2026-02-25-0001045810-26-000021.txt").write_text("no match here\n")
    # an image riding along in an accession: no lines to match
    doc = q / "2026-08-26-0001045810-26-000075"
    doc.mkdir()
    (doc / "logo.jpg").write_bytes(b"\xff\xd8\x00\x00sovereign\x00")
    # something on the host that is NOT a filing
    (tmp_path / "secret.txt").write_text("sovereign key\n")
    return root


def _read(cache: Path) -> ReadFileService:
    return ReadFileService(repository=FilesystemCache(cache), searcher=GrepSearcher())


def _grep(cache: Path) -> GrepService:
    return GrepService(repository=FilesystemCache(cache), searcher=GrepSearcher())


def _handlers(cache: Path) -> MCPHandlers:
    return MCPHandlers(Container(cache_dir=cache))


Q3 = "NVDA/10-Q/2026-08-26-0001045810-26-000075.txt"


class TestRead:
    def test_window_is_1_based_and_reports_total(self, cache):
        sl = _read(cache).execute(str(cache / Q3), offset=10, limit=3)
        assert sl.start_line == 10
        assert sl.lines == ["line 10", "line 11", "line 12"]
        assert sl.total_lines == 101

    def test_relative_path_resolves_from_cache_root(self, cache):
        sl = _read(cache).execute(Q3, offset=1, limit=1)
        assert sl.path == (cache / Q3).resolve()
        assert sl.lines == ["line 1"]

    def test_offset_zero_means_start(self, cache):
        assert _read(cache).execute(Q3, offset=0, limit=1).lines == ["line 1"]

    def test_limit_is_capped(self, cache):
        big = cache / "NVDA" / "10-Q" / "2026-01-01-big.txt"
        big.write_text("x\n" * (READ_MAX_LINES + 50))
        assert len(_read(cache).execute(str(big), limit=10**6).lines) == READ_MAX_LINES

    def test_long_line_is_clipped(self, cache):
        wide = cache / "NVDA" / "10-Q" / "2026-01-02-wide.txt"
        wide.write_text("y" * (MAX_LINE_CHARS + 123) + "\n")
        (line,) = _read(cache).execute(str(wide)).lines
        assert line.startswith("y" * MAX_LINE_CHARS)
        assert line.endswith("[+123 chars]")

    @pytest.mark.parametrize("escape", ["../secret.txt", "NVDA/../../secret.txt", "/etc/passwd"])
    def test_cannot_leave_the_cache(self, cache, escape):
        with pytest.raises(ValueError, match="outside the filing cache"):
            _read(cache).execute(escape)

    def test_symlink_out_of_the_cache_is_refused(self, cache):
        (cache / "NVDA" / "link.txt").symlink_to(cache.parent / "secret.txt")
        with pytest.raises(ValueError, match="outside the filing cache"):
            _read(cache).execute("NVDA/link.txt")

    def test_missing_file_says_how_to_get_it(self, cache):
        with pytest.raises(FileNotFoundError, match="fetch_filing"):
            _read(cache).execute("NVDA/10-Q/2099-01-01.txt")

    def test_folder_points_at_grep(self, cache):
        with pytest.raises(IsADirectoryError, match="grep"):
            _read(cache).execute("NVDA")


class TestGrep:
    def test_one_file(self, cache):
        r = _grep(cache).execute("sovereign", Q3)
        assert not r.is_folder
        assert r.total_matches == 1
        assert r.files[0].matches[0].line_number == 101

    def test_folder_sweeps_cached_files_newest_first(self, cache):
        r = _grep(cache).execute("sovereign", "NVDA")
        assert r.is_folder
        assert r.files_searched == 3          # the .jpg is skipped, the 10-K is searched
        assert r.files_matched == 2
        assert [f.path.name for f in r.files] == [
            "2026-08-26-0001045810-26-000075.txt",
            "2026-05-28-0001045810-26-000050.txt",
        ]

    def test_newest_first_across_form_folders(self, cache):
        k = cache / "NVDA" / "10-K" / "2026-09-01-0001045810-26-000099.txt"
        k.write_text("sovereign\n")
        r = _grep(cache).execute("sovereign", "NVDA")
        assert r.files[0].path.name == k.name

    def test_long_match_lines_are_clipped(self, cache):
        html = cache / "NVDA" / "10-Q" / "2026-08-26-0001045810-26-000075" / "2"
        html.write_text("<div>" + "z" * (MAX_LINE_CHARS * 3) + " sovereign</div>\n")
        r = _grep(cache).execute("sovereign", str(html))
        assert len(r.files[0].matches[0].line_content) < MAX_LINE_CHARS + 40

    def test_pages_across_files(self, cache):
        first = _grep(cache).execute("sovereign", "NVDA", max_results=1, offset=0)
        second = _grep(cache).execute("sovereign", "NVDA", max_results=1, offset=1)
        assert first.total_matches == second.total_matches == 2
        assert first.files[0].path != second.files[0].path

    def test_cannot_leave_the_cache(self, cache):
        with pytest.raises(ValueError, match="outside the filing cache"):
            _grep(cache).execute("sovereign", "..")

    def test_too_broad_a_folder_is_refused(self, cache, monkeypatch):
        monkeypatch.setattr("mcp_edgar_ux.core.services.GREP_MAX_FILES", 2)
        with pytest.raises(ValueError, match="narrow it"):
            _grep(cache).execute("sovereign", "NVDA")
        assert GREP_MAX_FILES > 2


class TestFormat:
    """The affordances are the point: they must name verbs a remote agent can call.

    Driven through MCPHandlers, the same path the MCP server takes.
    """

    def test_read_offers_the_next_window(self, cache):
        text = format_read(asyncio.run(_handlers(cache).read(Q3, offset=1, limit=5)))
        assert "LINES 1-5 of 101" in text
        assert "     1\tline 1" in text
        assert "read(path, offset=6, limit=5)" in text

    def test_folder_grep_says_it_saw_only_the_cache(self, cache):
        text = format_grep(asyncio.run(_handlers(cache).grep("sovereign", "NVDA")))
        assert "3 cached files searched, 2 matched" in text
        assert "not yet fetched was not searched" in text
        assert "Read(" not in text

    def test_errors_come_back_as_text(self, cache):
        text = format_read(asyncio.run(_handlers(cache).read("/etc/passwd")))
        assert text.startswith("ERROR: read failed: path is outside the filing cache")
