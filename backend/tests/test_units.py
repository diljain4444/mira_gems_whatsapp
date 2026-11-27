"""
tests/test_demand_extract.py

Unit tests for demand_extract.py — runs without network/API access.
Tests the deterministic components only (carat regex, fluorescence/certification correction).
The LLM extraction tests require GROQ_API_KEY and are marked accordingly.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'core'))

from demand_extract import extract_carat, correct_fluorescence_certification


class TestExtractCarat:
    def test_exact_carat(self):
        mn, mx = extract_carat("2.6ct round")
        assert mn == 2.6 and mx == 2.6

    def test_range(self):
        mn, mx = extract_carat("1.00 to 1.10ct")
        assert mn == 1.0 and mx == 1.10

    def test_range_dash(self):
        mn, mx = extract_carat("1-1.10")
        assert mn == 1.0 and mx == 1.10

    def test_above(self):
        mn, mx = extract_carat("3ct above")
        assert mn == 3.0 and mx is None

    def test_below(self):
        mn, mx = extract_carat("below 5ct")
        assert mn is None and mx == 5.0

    def test_no_carat(self):
        mn, mx = extract_carat("D VS1 EX EX EX")
        assert mn is None and mx is None


class TestFluorescenceCertificationCorrection:
    def _run(self, text, initial=None):
        result = initial or {"fluorescence": "", "certification": ""}
        return correct_fluorescence_certification(text, result)

    def test_standalone_non_certi(self):
        r = self._run("non certi")
        assert r["fluorescence"] == ""
        assert r["certification"] == "None"

    def test_non_certi_in_full_requirement(self):
        # "rnd 2-2.20 EX vvs-vs non certi" → fluorescence="", certification=None
        r = self._run("rnd 2-2.20 EX vvs-vs non certi", {"fluorescence": "NON", "certification": "Certi"})
        assert r["fluorescence"] == ""
        assert r["certification"] == "None"

    def test_non_certi_with_separate_non_fluorescence(self):
        # "rnd 2-2.20 EX vvs-vs non certi non" → fluorescence=NON, certification=None
        r = self._run("rnd 2-2.20 EX vvs-vs non certi non", {"fluorescence": "NON", "certification": "Certi"})
        assert r["fluorescence"] == "NON"
        assert r["certification"] == "None"

    def test_unrelated_text_unchanged(self):
        r = self._run("D VS1 EX EX EX", {"fluorescence": "SLT", "certification": "IGI"})
        # No non/certi pattern → values unchanged
        assert r["fluorescence"] == "SLT"
        assert r["certification"] == "IGI"


class TestInventoryService:
    """Tests for parse_stone_ids — no network needed."""
    def test_parse(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'services'))
        from inventory_service import parse_stone_ids

        ids = parse_stone_ids("B000216\nB000217, B000218; B000219 B000220")
        assert ids == ["B000216", "B000217", "B000218", "B000219", "B000220"]

    def test_dedup(self):
        from inventory_service import parse_stone_ids
        ids = parse_stone_ids("B001 B001 B001")
        assert ids == ["B001"]

    def test_empty(self):
        from inventory_service import parse_stone_ids
        ids = parse_stone_ids("   ")
        assert ids == []
