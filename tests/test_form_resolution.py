"""
Tests for resolving a form request to ONE filing (EdgarAdapter.get_latest).

list_available() is a family listing: edgartools adds the /A amendments to a
form query, and EDGAR's current feed prefix-matches ('S-1' also returns S-1/A
and S-1MEF). Resolving newest-first over that list handed back an amendment as
the form that was asked for — fetch_filing(CIK 2130357, 'S-1') returned the
11/02 S-1/A, and the original 10/26 S-1 was unreachable by form name. The
header did print 'S-1/A', so the swap was visible only to a reader who checked.

Pure unit tests — list_available is stubbed, no network.
"""
import pytest

from mcp_edgar_ux.adapters.edgar import EdgarAdapter
from mcp_edgar_ux.core.domain import Filing


def _filing(form: str, date: str, accession: str) -> Filing:
    return Filing(
        ticker="CIK0002130357",
        form_type=form,
        filing_date=date,
        accession_number=accession,
        sec_url=f"https://sec.gov/{accession}",
    )


S1_AMEND_2 = _filing("S-1/A", "2026-11-02", "0001628280-26-068676")
S1_MEF = _filing("S-1MEF", "2026-10-30", "0001628280-26-068000")
S1_AMEND_1 = _filing("S-1/A", "2026-10-29", "0001628280-26-067500")
S1 = _filing("S-1", "2026-10-26", "0001628280-26-067168")

# Newest-first, as list_available returns it.
S1_FAMILY = [S1_AMEND_2, S1_MEF, S1_AMEND_1, S1]


@pytest.fixture
def adapter(monkeypatch):
    adapter = EdgarAdapter()
    listings = {}
    monkeypatch.setattr(adapter, "list_available", lambda ticker, form_type: listings[form_type])
    adapter.listings = listings
    return adapter


class TestExactForm:
    def test_original_is_not_shadowed_by_newer_amendment(self, adapter):
        adapter.listings["S-1"] = S1_FAMILY
        assert adapter.get_latest("2130357", "S-1") is S1

    def test_amendment_resolves_when_asked_for(self, adapter):
        adapter.listings["S-1/A"] = [S1_AMEND_2, S1_AMEND_1]
        assert adapter.get_latest("2130357", "S-1/A") is S1_AMEND_2

    def test_date_resolves_within_the_exact_form(self, adapter):
        # The oldest S-1/A on or after the date — not the S-1MEF, not the S-1.
        adapter.listings["S-1/A"] = [S1_AMEND_2, S1_AMEND_1]
        assert adapter.get_latest("2130357", "S-1/A", "2026-10-27") is S1_AMEND_1

    def test_case_and_whitespace_do_not_matter(self, adapter):
        adapter.listings["s-1 "] = S1_FAMILY
        assert adapter.get_latest("2130357", "s-1 ") is S1

    def test_edgartools_alias_resolves_to_its_real_form(self, adapter):
        nport = _filing("NPORT-P", "2026-10-01", "0000000000-26-000001")
        adapter.listings["N-PORT"] = [nport]
        assert adapter.get_latest("2130357", "N-PORT") is nport


class TestFamilies:
    @pytest.mark.parametrize("family", ["CORE", "ALL"])
    def test_family_requests_resolve_across_members(self, adapter, family):
        adapter.listings[family] = S1_FAMILY
        assert adapter.get_latest("2130357", family) is S1_AMEND_2


class TestNoExactMatch:
    def test_error_names_the_related_forms(self, adapter):
        adapter.listings["S-1"] = S1_FAMILY
        with pytest.raises(ValueError) as err:
            adapter.get_latest("2130357", "S-1", "2026-10-27")
        message = str(err.value)
        assert "No S-1 filings found for 2130357 on or after 2026-10-27" in message
        assert "S-1/A, S-1MEF" in message

    def test_empty_listing_has_no_related_clause(self, adapter):
        adapter.listings["10-K"] = []
        with pytest.raises(ValueError) as err:
            adapter.get_latest("2130357", "10-K")
        assert str(err.value) == "No 10-K filings found for 2130357"
