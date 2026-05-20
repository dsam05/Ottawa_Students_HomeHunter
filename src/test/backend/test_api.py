from __future__ import annotations

import duckdb
import pytest

from src.main.backend import app as app_module
from src.main.backend import storage


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    conn = duckdb.connect(str(tmp_path / "api-test.duckdb"))
    storage.ensure_schema(conn)
    monkeypatch.setattr(app_module, "connect", lambda: conn)
    app_module.app.config.update(TESTING=True)

    yield app_module.app.test_client(), conn

    conn.close()


def test_health_reports_listing_count(api_client) -> None:
    client, conn = api_client
    storage.upsert_listing(
        conn,
        {
            "url": "https://www.realtor.ca/real-estate/1/test-listing",
            "address": "1 Test Street",
        },
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json == {"ok": True, "total": 1}


def test_listings_returns_rows_sorted_by_fee(api_client) -> None:
    client, conn = api_client
    storage.upsert_listing(
        conn,
        {
            "url": "https://www.realtor.ca/real-estate/2/higher-fee",
            "address": "2 Test Street",
            "maintenance_fee": 650,
        },
    )
    storage.upsert_listing(
        conn,
        {
            "url": "https://www.realtor.ca/real-estate/1/lower-fee",
            "address": "1 Test Street",
            "maintenance_fee": 350,
        },
    )

    response = client.get("/api/listings?sort=fee_asc")

    assert response.status_code == 200
    assert [row["address"] for row in response.json["listings"]] == ["1 Test Street", "2 Test Street"]


def test_listings_returns_school_rows(api_client) -> None:
    client, conn = api_client
    storage.upsert_listing(
        conn,
        {
            "url": "https://www.realtor.ca/real-estate/1/test-listing",
            "address": "1 Test Street",
            "school": "OCDSB: Test Public School; OCSB: Test Catholic School",
            "school_distance_km": 1.2,
            "school_distance_category": "Considerable",
        },
    )

    response = client.get("/api/listings")

    assert response.status_code == 200
    [listing] = response.json["listings"]
    assert [school["board"] for school in listing["schools"]] == ["OCDSB", "OCSB"]
    assert listing["schools"][0]["distance_km"] == 1.2


def test_distance_settings_validate_and_recalculate_categories(api_client) -> None:
    client, conn = api_client
    storage.upsert_listing(
        conn,
        {
            "url": "https://www.realtor.ca/real-estate/1/test-listing",
            "address": "1 Test Street",
            "school_distance_km": 1.4,
            "school_distance_category": "Preferred",
        },
    )

    invalid = client.post(
        "/api/settings/distance",
        json={"preferred_max_km": 1.5, "considerable_max_km": 1.0},
    )
    valid = client.post(
        "/api/settings/distance",
        json={"preferred_max_km": 1.0, "considerable_max_km": 1.5},
    )
    listing = conn.execute(
        "SELECT school_distance_category FROM listings WHERE url = ?",
        ["https://www.realtor.ca/real-estate/1/test-listing"],
    ).fetchone()

    assert invalid.status_code == 400
    assert valid.status_code == 200
    assert valid.json == {
        "configured": True,
        "preferred_max_km": 1.0,
        "considerable_max_km": 1.5,
    }
    assert listing == ("Considerable",)


def test_fee_settings_validate_and_save(api_client) -> None:
    client, _ = api_client

    invalid = client.post(
        "/api/settings/fee",
        json={"green_max_fee": 700, "amber_max_fee": 600},
    )
    valid = client.post(
        "/api/settings/fee",
        json={"green_max_fee": 425, "amber_max_fee": 625},
    )

    assert invalid.status_code == 400
    assert valid.status_code == 200
    assert valid.json == {
        "configured": True,
        "green_max_fee": 425.0,
        "amber_max_fee": 625.0,
    }


def test_import_rejects_unknown_school_board(api_client) -> None:
    client, _ = api_client

    response = client.post(
        "/api/import",
        json={"urls": "https://www.realtor.ca/real-estate/1/test-listing", "school_board": "unknown"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "School board must be OCDSB, OCSB, or both."}


def test_delete_listing_normalizes_url_before_delete(api_client) -> None:
    client, conn = api_client
    url = "https://www.realtor.ca/real-estate/1/test-listing"
    storage.upsert_listing(conn, {"url": url, "address": "1 Test Street"})

    response = client.delete(f"/api/listings/{url}/?utm_source=test")
    remaining = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]

    assert response.status_code == 200
    assert response.json == {"deleted": url}
    assert remaining == 0
