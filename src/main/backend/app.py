from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    from .background_worker import enqueue_import, get_job, update_job
    from .ocdsb_lookup import enrich_listing_with_ocdsb, needs_school_enrichment
    from .ocsb_lookup import enrich_listing_with_ocsb
    from .realtor_lookup import enrich_listing_with_realtor, needs_realtor_enrichment
    from .safety_lookup import enrich_listing_with_safety, needs_safety_enrichment
    from .storage import (
        apply_distance_preference_to_listing,
        apply_distance_preferences,
        connect,
        get_distance_preferences,
        get_fee_preferences,
        normalize_url,
        save_distance_preferences,
        save_fee_preferences,
        seed_initial_listings,
        schools_by_listing,
        title_from_slug,
        upsert_listing,
    )
except ImportError:  # pragma: no cover
    from background_worker import enqueue_import, get_job, update_job
    from ocdsb_lookup import enrich_listing_with_ocdsb, needs_school_enrichment
    from ocsb_lookup import enrich_listing_with_ocsb
    from realtor_lookup import enrich_listing_with_realtor, needs_realtor_enrichment
    from safety_lookup import enrich_listing_with_safety, needs_safety_enrichment
    from storage import (
        apply_distance_preference_to_listing,
        apply_distance_preferences,
        connect,
        get_distance_preferences,
        get_fee_preferences,
        normalize_url,
        save_distance_preferences,
        save_fee_preferences,
        seed_initial_listings,
        schools_by_listing,
        title_from_slug,
        upsert_listing,
    )


ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = ROOT / "src" / "main" / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"

SORTS = {
    "school_proximity": "school_distance_km ASC NULLS LAST, price ASC NULLS LAST",
    "safety": (
        "CASE safety_category "
        "WHEN 'Very Safe' THEN 1 WHEN 'Moderate' THEN 2 WHEN 'Risky' THEN 3 ELSE 4 END ASC, "
        "school_distance_km ASC NULLS LAST"
    ),
    "price_asc": "price ASC NULLS LAST",
    "price_desc": "price DESC NULLS LAST",
    "fee_asc": "maintenance_fee ASC NULLS LAST, price ASC NULLS LAST",
    "fee_desc": "maintenance_fee DESC NULLS LAST, price ASC NULLS LAST",
}


app = Flask(__name__, static_folder=str(DIST_DIR if DIST_DIR.exists() else FRONTEND_DIR), static_url_path="")
CORS(app)


def enrich_listing_with_school_boards(listing: dict[str, Any], school_board: str) -> dict[str, Any]:
    if school_board == "ocsb":
        return enrich_listing_with_ocsb(listing)
    if school_board == "both":
        original = dict(listing)
        ocdsb_listing = enrich_listing_with_ocdsb(dict(original))
        ocsb_listing = enrich_listing_with_ocsb(dict(original))
        listing.update(ocdsb_listing)
        listing["school"] = "; ".join(filter(None, [
            f"OCDSB: {ocdsb_listing.get('school')}" if ocdsb_listing.get("school") else None,
            ocsb_listing.get("school"),
        ]))
        listing["confidence"] = " | ".join(filter(None, [
            ocdsb_listing.get("confidence"),
            ocsb_listing.get("confidence"),
        ]))
        listing["source_urls"] = "; ".join(dict.fromkeys(filter(None, [
            *(str(ocdsb_listing.get("source_urls") or "").split("; ")),
            *(str(ocsb_listing.get("source_urls") or "").split("; ")),
        ])))
        return listing
    return enrich_listing_with_ocdsb(listing)


def process_import_job(job_id: str, urls: list[str], school_board: str = "both") -> dict[str, Any]:
    conn = connect()
    imported: list[dict[str, Any]] = []
    skipped = 0
    for index, url in enumerate(urls, start=1):
        update_job(job_id, processed=index - 1, message=f"Processing {index} of {len(urls)}")
        if not url.startswith("https://www.realtor.ca/real-estate/"):
            skipped += 1
            update_job(job_id, skipped=skipped, processed=index)
            continue
        address, community = title_from_slug(url)
        listing = {
            "url": url,
            "address": address,
            "community": community,
            "confidence": "Manual enrichment needed: listing facts could not be fully verified yet.",
            "source_urls": url,
        }
        update_job(job_id, message=f"Fetching Realtor.ca facts for {address}")
        if needs_realtor_enrichment(listing):
            listing = enrich_listing_with_realtor(listing)
        update_job(job_id, message=f"Checking {school_board.upper()} school for {listing.get('address') or address}")
        if school_board != "ocdsb" or needs_school_enrichment(listing):
            listing = enrich_listing_with_school_boards(listing, school_board)
        listing = enrich_listing_with_safety(listing)
        if needs_safety_enrichment(listing):
            listing = enrich_listing_with_safety(listing)
        listing = apply_distance_preference_to_listing(conn, listing)
        upsert_listing(conn, listing)
        imported.append(listing)
        update_job(job_id, imported=len(imported), skipped=skipped, processed=index, listings=imported[-10:])
    return {"processed": len(urls), "imported": len(imported), "skipped": skipped, "listings": imported[-25:]}


@app.get("/api/health")
def health() -> Any:
    conn = connect()
    total = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    return jsonify({"ok": True, "total": total})


@app.post("/api/seed")
def seed() -> Any:
    conn = connect()
    count = seed_initial_listings(conn)
    apply_distance_preferences(conn)
    return jsonify({"seeded": count})


@app.get("/api/settings/distance")
def distance_settings() -> Any:
    conn = connect()
    prefs = get_distance_preferences(conn)
    if not prefs:
        return jsonify({"configured": False, "preferred_max_km": 1.0, "considerable_max_km": 1.5})
    return jsonify({"configured": True, **prefs})


@app.post("/api/settings/distance")
def save_distance_settings() -> Any:
    conn = connect()
    payload = request.get_json(silent=True) or {}
    try:
        preferred_max = float(payload.get("preferred_max_km"))
        considerable_max = float(payload.get("considerable_max_km"))
    except (TypeError, ValueError):
        return jsonify({"error": "Distances must be numbers."}), 400
    if preferred_max <= 0 or considerable_max <= preferred_max:
        return jsonify({"error": "Considerable distance must be greater than preferred distance."}), 400
    save_distance_preferences(conn, preferred_max, considerable_max)
    apply_distance_preferences(conn)
    return jsonify({"configured": True, "preferred_max_km": preferred_max, "considerable_max_km": considerable_max})


@app.get("/api/settings/fee")
def fee_settings() -> Any:
    conn = connect()
    prefs = get_fee_preferences(conn)
    if not prefs:
        return jsonify({"configured": False, "green_max_fee": 400.0, "amber_max_fee": 600.0})
    return jsonify({"configured": True, **prefs})


@app.post("/api/settings/fee")
def save_fee_settings() -> Any:
    conn = connect()
    payload = request.get_json(silent=True) or {}
    try:
        green_max = float(payload.get("green_max_fee"))
        amber_max = float(payload.get("amber_max_fee"))
    except (TypeError, ValueError):
        return jsonify({"error": "Condo fee thresholds must be numbers."}), 400
    if green_max < 0 or amber_max <= green_max:
        return jsonify({"error": "Amber maximum must be greater than green maximum."}), 400
    save_fee_preferences(conn, green_max, amber_max)
    return jsonify({"configured": True, "green_max_fee": green_max, "amber_max_fee": amber_max})


@app.post("/api/import")
def import_urls() -> Any:
    payload = request.get_json(silent=True) or {}
    raw = payload.get("urls", "")
    school_board = str(payload.get("school_board") or "both").lower()
    if school_board not in {"ocdsb", "ocsb", "both"}:
        return jsonify({"error": "School board must be OCDSB, OCSB, or both."}), 400
    urls = [normalize_url(line) for line in re.split(r"[\n, ]+", raw) if line.strip()]
    job = enqueue_import(process_import_job, urls, school_board)
    return jsonify(job), 202


@app.get("/api/jobs/<job_id>")
def job_status(job_id: str) -> Any:
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.get("/api/listings")
def listings() -> Any:
    conn = connect()
    apply_distance_preferences(conn)
    sort = request.args.get("sort", "school_proximity")
    order = SORTS.get(sort, SORTS["school_proximity"])
    rows = conn.execute(f"SELECT * FROM listings ORDER BY {order}").fetchall()
    columns = [desc[0] for desc in conn.description]
    listings_payload = [dict(zip(columns, row)) for row in rows]
    school_rows = schools_by_listing(conn, [str(item["url"]) for item in listings_payload])
    for item in listings_payload:
        item["schools"] = school_rows.get(str(item["url"]), [])
    return jsonify({"sort": sort, "listings": listings_payload})


@app.delete("/api/listings")
def clear_listings() -> Any:
    conn = connect()
    conn.execute("DELETE FROM listing_schools")
    conn.execute("DELETE FROM listings")
    return jsonify({"cleared": True})


@app.delete("/api/listings/<path:url>")
def delete_listing(url: str) -> Any:
    conn = connect()
    normalized = normalize_url(url)
    conn.execute("DELETE FROM listing_schools WHERE url = ?", [normalized])
    conn.execute("DELETE FROM listings WHERE url = ?", [normalized])
    return jsonify({"deleted": normalized})


@app.get("/")
def index() -> Any:
    static_dir = DIST_DIR if DIST_DIR.exists() else FRONTEND_DIR
    return send_from_directory(static_dir, "index.html")


@app.get("/<path:path>")
def frontend(path: str) -> Any:
    static_dir = DIST_DIR if DIST_DIR.exists() else FRONTEND_DIR
    target = static_dir / path
    if target.exists():
        return send_from_directory(static_dir, path)
    return send_from_directory(static_dir, "index.html")


if __name__ == "__main__":
    with connect() as conn:
        if conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == 0:
            seed_initial_listings(conn)
    app.run(host="127.0.0.1", port=5001, debug=True)
