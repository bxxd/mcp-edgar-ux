"""
Tests for the text render's line shape.

edgartools 5.x emits each prose paragraph as a single line. Cached filings are
read by line (Read offset/limit, search_filing), and Read truncates past 2,000
chars, so prose is re-wrapped at 80 columns while table rows stay verbatim.

Pure unit tests — no network.
"""
from mcp_edgar_ux.adapters.edgar import _wrap_prose

PARAGRAPH = ("Total product sales increased 10% in 2025, driven by volume growth "
             "of 13%, partially offset by declines in net selling price of 3%. ") * 40


class TestWrapProse:
    def test_long_paragraph_wraps_at_80(self):
        out = _wrap_prose(PARAGRAPH)
        lines = out.split("\n")
        assert len(lines) > 1
        assert all(len(line) <= 80 for line in lines)

    def test_no_words_lost(self):
        assert _wrap_prose(PARAGRAPH).split() == PARAGRAPH.split()

    def test_indent_kept_on_continuation_lines(self):
        out = _wrap_prose("    " + PARAGRAPH)
        assert all(line.startswith("    ") for line in out.split("\n"))

    def test_aligned_table_row_untouched(self):
        row = ("  Total product sales" + " " * 28 + "35,148" + " " * 9 + "10%"
               + " " * 28 + "32,026" + " " * 40 + "29,000")
        assert len(row) > 80
        assert _wrap_prose(row) == row

    def test_box_drawing_rule_untouched(self):
        rule = " " + "─" * 120
        assert _wrap_prose(rule) == rule

    def test_short_lines_and_blank_lines_untouched(self):
        text = "Item 1.02\n\nTermination of a Material Definitive Agreement.\n"
        assert _wrap_prose(text) == text
