"""
Tests for the exhibit text render.

fetch() appends every EX-* exhibit to the primary document. Exhibits are
rendered with the same parser Filing.text() uses for the primary. edgartools'
own Attachment.text() runs the legacy parser, which drops any <h1>-<h6> it does
not read as a short title, and DFIN lays credit agreements out with whole
sections inside <h2> (VITL 10-Q 2026-11-03, EX-10.2 SECTION 6.06 and EX-10.3
Section 7.12 were missing from the render).

Pure unit tests — no network.
"""
import re

from mcp_edgar_ux.adapters.edgar import _exhibit_text

FONT = '<font style="color:#000000;white-space:pre-wrap;font-size:11pt;font-family:Times New Roman;">'

SECTION_IN_H2 = (
    "<html><body>"
    "<p>SECTION 6.05. Dispositions. The Borrower may sell inventory.</p>"
    '<h2 style="text-indent:6.667%;font-size:11pt;text-align:justify;">'
    f"{FONT}SECTION 6.06.\t</font>"
    f"{FONT}Sale and Leaseback Transactions</font>"
    f"{FONT}.  No Loan Party will, nor will it permit any Subsidiary to, enter into any "
    "arrangement whereby it shall sell or transfer any property and thereafter rent or "
    "lease such property (a “Sale and Leaseback Transaction”).</font>"
    "</h2>"
    "<p>SECTION 6.07. Swap Agreements. No Loan Party will enter into any Swap Agreement.</p>"
    "</body></html>"
)


class FakeExhibit:
    def __init__(self, content, html=True, text=True):
        self.content = content
        self._html = html
        self._text = text

    def is_text(self):
        return self._text

    def is_html(self):
        return self._html

    def text(self):
        return self.content if self._text else None


def _flat(s):
    return re.sub(r"\s+", " ", s)


class TestExhibitText:
    def test_section_body_inside_h2_is_rendered(self):
        out = _flat(_exhibit_text(FakeExhibit(SECTION_IN_H2)))
        assert "Sale and Leaseback Transactions" in out
        assert "No Loan Party will, nor will it permit any Subsidiary" in out
        assert "Sale and Leaseback Transaction”)." in out

    def test_neighbouring_paragraphs_kept_in_order(self):
        out = _flat(_exhibit_text(FakeExhibit(SECTION_IN_H2)))
        assert out.index("SECTION 6.05") < out.index("SECTION 6.06") < out.index("SECTION 6.07")

    def test_plain_text_exhibit_passes_through(self):
        body = "EXHIBIT 99.1\n\nPress release text.\n"
        assert _exhibit_text(FakeExhibit(body, html=False)) == body

    def test_binary_exhibit_renders_nothing(self):
        assert _exhibit_text(FakeExhibit(b"%PDF-1.7", html=False, text=False)) is None
