from __future__ import annotations

import duckdb

from src.main.backend import storage


def test_normalize_url_strips_tracking_query_fragment_and_trailing_slash() -> None:
    url = " https://www.realtor.ca/real-estate/123/example-listing/?utm_source=x#details "

    assert storage.normalize_url(url) == "https://www.realtor.ca/real-estate/123/example-listing"


def test_title_from_slug_extracts_address_and_community() -> None:
    url = "https://www.realtor.ca/real-estate/29632019/3565-aladdin-lane-ottawa-2605-blossom-parkkemp-parkfindlay-creek"

    address, community = storage.title_from_slug(url)

    assert address == "3565 Aladdin Lane"
    assert community == "2605 Blossom Parkkemp Parkfindlay Creek"


def test_category_for_distance_uses_custom_thresholds() -> None:
    assert storage.category_for_distance(0.8, 1.0, 1.5) == "Preferred"
    assert storage.category_for_distance("1.25", 1.0, 1.5) == "Considerable"
    assert storage.category_for_distance(1.51, 1.0, 1.5) == "Too Far"
    assert storage.category_for_distance(None, 1.0, 1.5) is None
    assert storage.category_for_distance("unknown", 1.0, 1.5) is None


def test_distance_preferences_recalculate_only_school_distance_category(tmp_path) -> None:
    conn = duckdb.connect(str(tmp_path / "shortlist-test.duckdb"))
    storage.ensure_schema(conn)
    storage.upsert_listing(
        conn,
        {
            "url": "https://www.realtor.ca/real-estate/1/test-listing",
            "address": "1 Test Street",
            "school_distance_km": 1.2,
            "school_distance_category": "Preferred",
            "safety_category": "Very Safe",
        },
    )

    storage.save_distance_preferences(conn, preferred_max=1.0, considerable_max=1.5)
    storage.apply_distance_preferences(conn)

    row = conn.execute(
        "SELECT school_distance_category, safety_category FROM listings WHERE url = ?",
        ["https://www.realtor.ca/real-estate/1/test-listing"],
    ).fetchone()

    assert row == ("Considerable", "Very Safe")


def test_fee_preferences_can_be_saved_and_updated(tmp_path) -> None:
    conn = duckdb.connect(str(tmp_path / "shortlist-test.duckdb"))
    storage.ensure_schema(conn)

    storage.save_fee_preferences(conn, green_max=400, amber_max=600)
    storage.save_fee_preferences(conn, green_max=450, amber_max=650)

    assert storage.get_fee_preferences(conn) == {
        "green_max_fee": 450,
        "amber_max_fee": 650,
    }


def test_seed_initial_listings_is_noop_for_clean_public_clone(tmp_path) -> None:
    conn = duckdb.connect(str(tmp_path / "shortlist-test.duckdb"))
    storage.ensure_schema(conn)

    seeded = storage.seed_initial_listings(conn)
    count = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]

    assert seeded == 0
    assert count == 0


def test_upsert_listing_syncs_board_school_rows(tmp_path) -> None:
    conn = duckdb.connect(str(tmp_path / "shortlist-test.duckdb"))
    storage.ensure_schema(conn)
    url = "https://www.realtor.ca/real-estate/1/test-listing"

    storage.upsert_listing(
        conn,
        {
            "url": url,
            "address": "1 Test Street",
            "school": "OCDSB: Test Public School; OCSB: Test Catholic School",
            "school_distance_km": 0.9,
            "school_distance_category": "Preferred",
            "school_reputation": "Strong",
        },
    )
    rows = conn.execute(
        "SELECT board, school, distance_km, distance_category FROM listing_schools WHERE url = ? ORDER BY board",
        [url],
    ).fetchall()

    assert rows == [
        ("OCDSB", "Test Public School", 0.9, "Preferred"),
        ("OCSB", "Test Catholic School", None, None),
    ]
