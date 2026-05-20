from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

try:
    from .ocdsb_lookup import category
except ImportError:  # pragma: no cover
    from ocdsb_lookup import category


ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "app_data" / "shortlist.duckdb"

LISTING_COLUMNS = [
    "url", "address", "community", "property_type", "price", "beds", "baths",
    "parking_type", "parking_spaces", "maintenance_fee", "basement", "school",
    "school_distance_km", "school_distance_category", "school_reputation",
    "safety_category", "safety_notes", "overall_verdict", "confidence", "source_urls",
]

SCHOOL_COLUMNS = [
    "url", "board", "school", "distance_km", "distance_category", "reputation",
    "confidence", "source_urls",
]


def connect() -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))
    ensure_schema(conn)
    return conn


def ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS listings (
            url TEXT PRIMARY KEY,
            address TEXT,
            community TEXT,
            property_type TEXT,
            price INTEGER,
            beds DOUBLE,
            baths DOUBLE,
            parking_type TEXT,
            parking_spaces DOUBLE,
            maintenance_fee DOUBLE,
            basement TEXT,
            school TEXT,
            school_distance_km DOUBLE,
            school_distance_category TEXT,
            school_reputation TEXT,
            safety_category TEXT,
            safety_notes TEXT,
            overall_verdict TEXT,
            confidence TEXT,
            source_urls TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS distance_preferences (
            id INTEGER PRIMARY KEY,
            preferred_max_km DOUBLE NOT NULL,
            considerable_max_km DOUBLE NOT NULL,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fee_preferences (
            id INTEGER PRIMARY KEY,
            green_max_fee DOUBLE NOT NULL,
            amber_max_fee DOUBLE NOT NULL,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS listing_schools (
            url TEXT NOT NULL,
            board TEXT NOT NULL,
            school TEXT,
            distance_km DOUBLE,
            distance_category TEXT,
            reputation TEXT,
            confidence TEXT,
            source_urls TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (url, board)
        )
        """
    )
    migrate_listing_schools(conn)


def parse_board_schools(listing: dict[str, Any]) -> list[dict[str, Any]]:
    school_text = str(listing.get("school") or "").strip()
    if not school_text:
        return []

    parts = [part.strip() for part in school_text.split(";") if part.strip()]
    parsed: list[dict[str, Any]] = []
    for part in parts:
        match = re.match(r"^(OCDSB|OCSB)\s*:\s*(.+)$", part, flags=re.I)
        if match:
            board = match.group(1).upper()
            school = match.group(2).strip()
        elif len(parts) == 1:
            board = "OCDSB"
            school = part
        else:
            continue
        parsed.append(
            {
                "url": listing.get("url"),
                "board": board,
                "school": school,
                "distance_km": listing.get("school_distance_km") if board == "OCDSB" else None,
                "distance_category": listing.get("school_distance_category") if board == "OCDSB" else None,
                "reputation": listing.get("school_reputation") if board == "OCDSB" else None,
                "confidence": listing.get("confidence"),
                "source_urls": listing.get("source_urls"),
            }
        )
    return parsed


def upsert_listing_school(conn: duckdb.DuckDBPyConnection, school: dict[str, Any]) -> None:
    if not school.get("url") or not school.get("board"):
        return
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    values = [school.get(col) for col in SCHOOL_COLUMNS] + [now, now]
    conn.execute(
        f"""
        INSERT INTO listing_schools ({", ".join(SCHOOL_COLUMNS)}, created_at, updated_at)
        VALUES ({", ".join(["?"] * (len(SCHOOL_COLUMNS) + 2))})
        ON CONFLICT(url, board) DO UPDATE SET
            school = excluded.school,
            distance_km = excluded.distance_km,
            distance_category = excluded.distance_category,
            reputation = excluded.reputation,
            confidence = excluded.confidence,
            source_urls = excluded.source_urls,
            updated_at = excluded.updated_at
        """,
        values,
    )


def sync_listing_schools(conn: duckdb.DuckDBPyConnection, listing: dict[str, Any]) -> None:
    url = listing.get("url")
    if not url:
        return
    schools = parse_board_schools(listing)
    conn.execute("DELETE FROM listing_schools WHERE url = ?", [url])
    for school in schools:
        upsert_listing_school(conn, school)


def migrate_listing_schools(conn: duckdb.DuckDBPyConnection) -> None:
    if conn.execute("SELECT COUNT(*) FROM listing_schools").fetchone()[0]:
        return
    rows = conn.execute(f"SELECT {', '.join(LISTING_COLUMNS)} FROM listings").fetchall()
    for row in rows:
        sync_listing_schools(conn, dict(zip(LISTING_COLUMNS, row)))


def schools_by_listing(conn: duckdb.DuckDBPyConnection, urls: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not urls:
        return {}
    placeholders = ", ".join(["?"] * len(urls))
    rows = conn.execute(
        f"""
        SELECT {", ".join(SCHOOL_COLUMNS)}
        FROM listing_schools
        WHERE url IN ({placeholders})
        ORDER BY url, CASE board WHEN 'OCDSB' THEN 1 WHEN 'OCSB' THEN 2 ELSE 3 END
        """,
        urls,
    ).fetchall()
    result: dict[str, list[dict[str, Any]]] = {url: [] for url in urls}
    for row in rows:
        item = dict(zip(SCHOOL_COLUMNS, row))
        result.setdefault(str(item["url"]), []).append(item)
    return result


def normalize_url(url: str) -> str:
    url = url.strip()
    url = re.sub(r"[?#].*$", "", url)
    return url.rstrip("/")


def title_from_slug(url: str) -> tuple[str, str]:
    slug = normalize_url(url).split("/")[-1]
    bits = slug.split("-ottawa-")
    address_slug = bits[0]
    community_slug = bits[1] if len(bits) > 1 else ""
    address = " ".join(part.capitalize() for part in address_slug.split("-"))
    address = re.sub(r"\b([A-z])\b\s+(\d+)", r"\1 - \2", address)
    community = community_slug.replace("-", " ").title()
    return address, community


def category_for_distance(distance: Any, preferred_max: float, considerable_max: float) -> str | None:
    if distance in (None, ""):
        return None
    try:
        value = float(distance)
    except (TypeError, ValueError):
        return None
    if value <= preferred_max:
        return "Preferred"
    if value <= considerable_max:
        return "Considerable"
    return "Too Far"


def get_distance_preferences(conn: duckdb.DuckDBPyConnection) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT preferred_max_km, considerable_max_km FROM distance_preferences WHERE id = 1"
    ).fetchone()
    if not row:
        return None
    return {"preferred_max_km": row[0], "considerable_max_km": row[1]}


def save_distance_preferences(conn: duckdb.DuckDBPyConnection, preferred_max: float, considerable_max: float) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    conn.execute(
        """
        INSERT INTO distance_preferences (id, preferred_max_km, considerable_max_km, created_at, updated_at)
        VALUES (1, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            preferred_max_km = excluded.preferred_max_km,
            considerable_max_km = excluded.considerable_max_km,
            updated_at = excluded.updated_at
        """,
        [preferred_max, considerable_max, now, now],
    )


def apply_distance_preferences(conn: duckdb.DuckDBPyConnection) -> None:
    prefs = get_distance_preferences(conn)
    if not prefs:
        return
    conn.execute(
        """
        UPDATE listings
        SET school_distance_category = CASE
            WHEN school_distance_km IS NULL THEN NULL
            WHEN school_distance_km <= ? THEN 'Preferred'
            WHEN school_distance_km <= ? THEN 'Considerable'
            ELSE 'Too Far'
        END
        """,
        [prefs["preferred_max_km"], prefs["considerable_max_km"]],
    )


def apply_distance_preference_to_listing(conn: duckdb.DuckDBPyConnection, listing: dict[str, Any]) -> dict[str, Any]:
    prefs = get_distance_preferences(conn)
    if prefs:
        listing["school_distance_category"] = category_for_distance(
            listing.get("school_distance_km"),
            prefs["preferred_max_km"],
            prefs["considerable_max_km"],
        )
    return listing


def get_fee_preferences(conn: duckdb.DuckDBPyConnection) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT green_max_fee, amber_max_fee FROM fee_preferences WHERE id = 1"
    ).fetchone()
    if not row:
        return None
    return {"green_max_fee": row[0], "amber_max_fee": row[1]}


def save_fee_preferences(conn: duckdb.DuckDBPyConnection, green_max: float, amber_max: float) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    conn.execute(
        """
        INSERT INTO fee_preferences (id, green_max_fee, amber_max_fee, created_at, updated_at)
        VALUES (1, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            green_max_fee = excluded.green_max_fee,
            amber_max_fee = excluded.amber_max_fee,
            updated_at = excluded.updated_at
        """,
        [green_max, amber_max, now, now],
    )


def upsert_listing(conn: duckdb.DuckDBPyConnection, listing: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    values = [listing.get(col) for col in LISTING_COLUMNS] + [now, now]
    conn.execute(
        f"""
        INSERT INTO listings ({", ".join(LISTING_COLUMNS)}, created_at, updated_at)
        VALUES ({", ".join(["?"] * (len(LISTING_COLUMNS) + 2))})
        ON CONFLICT(url) DO UPDATE SET
            address = excluded.address,
            community = excluded.community,
            property_type = excluded.property_type,
            price = excluded.price,
            beds = excluded.beds,
            baths = excluded.baths,
            parking_type = excluded.parking_type,
            parking_spaces = excluded.parking_spaces,
            maintenance_fee = excluded.maintenance_fee,
            basement = excluded.basement,
            school = excluded.school,
            school_distance_km = excluded.school_distance_km,
            school_distance_category = excluded.school_distance_category,
            school_reputation = excluded.school_reputation,
            safety_category = excluded.safety_category,
            safety_notes = excluded.safety_notes,
            overall_verdict = excluded.overall_verdict,
            confidence = excluded.confidence,
            source_urls = excluded.source_urls,
            updated_at = excluded.updated_at
        """,
        values,
    )
    sync_listing_schools(conn, listing)


def seed_initial_listings(conn: duckdb.DuckDBPyConnection) -> int:
    return 0
