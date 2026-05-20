from __future__ import annotations

from src.main.backend import ocsb_lookup


def test_split_address_handles_unit_prefix() -> None:
    civic, street = ocsb_lookup.split_address("65 - 24 Sherway Drive Ottawa")

    assert civic == "24"
    assert street == "Sherway Drive"


def test_street_variants_include_busplanner_abbreviation() -> None:
    variants = ocsb_lookup.street_variants("Sherway Drive")

    assert "Sherway Drive" in variants
    assert "SHERWAY DR" in variants


def test_ocsb_school_lookup_parses_school_from_eligibility_page(monkeypatch) -> None:
    monkeypatch.setattr(ocsb_lookup, "ocsb_street_autocomplete", lambda street: ["SHERWAY DR"])
    monkeypatch.setattr(ocsb_lookup, "cache", lambda: {"version": 1, "autocomplete": {}, "school": {}})
    monkeypatch.setattr(ocsb_lookup, "save_cache", lambda data: None)
    monkeypatch.setattr(
        ocsb_lookup,
        "request_ocsb_page",
        lambda civic, street: """
            <script>
            SchoolPositions = JSON.parse('[[{"Name":"ST. PATRICK SCHOOL","Address":"68 LARKIN DR, OTTAWA","Grades":["JK","KG","1","2"],"ContactPhone":"613-825-4012","Programs":["MFI"]}]]');
            </script>
        """,
    )

    result = ocsb_lookup.ocsb_school_lookup("65 - 24 Sherway Drive Ottawa")

    assert result["locator_address"] == "24 SHERWAY DR"
    assert result["matched_street"] == "SHERWAY DR"
    assert result["school"] == "ST. PATRICK SCHOOL"
    assert result["school_address"] == "68 LARKIN DR, OTTAWA"
    assert result["grade_verified"] is True
