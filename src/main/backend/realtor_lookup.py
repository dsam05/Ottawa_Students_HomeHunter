from __future__ import annotations

import html
import json
import re
import ssl
import urllib.parse
import urllib.request
from typing import Any


DETAILS_URL = "https://api2.realtor.ca/Listing.svc/PropertyDetails"
REALTOR_URL_PREFIX = "https://www.realtor.ca/real-estate/"


def append_note(existing: Any, note: str) -> str:
    current = str(existing or "").strip()
    if not current:
        return note
    if note in current:
        return current
    return f"{current} {note}"


def append_source(existing: Any, source: str) -> str:
    values = [item.strip() for item in str(existing or "").split(";") if item.strip()]
    if source not in values:
        values.append(source)
    return "; ".join(values)


def listing_id_from_url(url: str) -> str | None:
    match = re.search(r"/real-estate/(\d+)/", url)
    return match.group(1) if match else None


def request_text(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "application/json,text/html,application/xhtml+xml",
        "Accept-Language": "en-CA,en;q=0.9",
        "Referer": "https://www.realtor.ca/",
    }
    request_obj = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request_obj, timeout=25, context=ssl._create_unverified_context()) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_json_response(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    next_data = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, flags=re.S)
    if next_data:
        try:
            data = json.loads(html.unescape(next_data.group(1)))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def clean_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return " ".join(html.unescape(str(value)).split())


def parse_money(value: Any) -> int | None:
    if value in (None, ""):
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else None


def parse_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def walk(value: Any) -> list[Any]:
    items = [value]
    if isinstance(value, dict):
        for child in value.values():
            items.extend(walk(child))
    elif isinstance(value, list):
        for child in value:
            items.extend(walk(child))
    return items


def first_key(data: dict[str, Any], keys: set[str]) -> Any:
    lowered = {key.lower() for key in keys}
    for item in walk(data):
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if key.lower() in lowered and value not in (None, "", [], {}):
                return value
    return None


def first_nested(data: dict[str, Any], parent_key: str, keys: set[str]) -> Any:
    parent_key = parent_key.lower()
    lowered = {key.lower() for key in keys}
    for item in walk(data):
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if key.lower() != parent_key or not isinstance(value, dict):
                continue
            for child_key, child_value in value.items():
                if child_key.lower() in lowered and child_value not in (None, "", [], {}):
                    return child_value
    return None


def parse_address(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("AddressText", "AddressLine1", "StreetAddress", "Text", "Address"):
            if value.get(key):
                return clean_text(value[key])
    return clean_text(value)


def parse_parking_type(value: Any) -> str | None:
    if isinstance(value, list):
        names = []
        for item in value:
            if isinstance(item, dict):
                names.append(item.get("Name") or item.get("Type") or item.get("ParkingType"))
            else:
                names.append(item)
        return ", ".join(filter(None, [clean_text(item) for item in names])) or None
    return clean_text(value)


def classify_basement(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    lowered = text.lower()
    if "part" in lowered or "semi" in lowered:
        return "Semi-finished / Partly finished"
    if "unfinished" in lowered:
        return "Unfinished"
    if "finished" in lowered:
        return "Finished"
    if "none" in lowered or "no basement" in lowered or "not applicable" in lowered:
        return "No basement"
    return text


def fetch_realtor_data(url: str) -> dict[str, Any] | None:
    property_id = listing_id_from_url(url)
    candidates = []
    if property_id:
        candidates.append(f"{DETAILS_URL}?{urllib.parse.urlencode({'PropertyID': property_id})}")
    candidates.append(url)
    for candidate in candidates:
        try:
            text = request_text(candidate)
        except Exception:
            continue
        data = parse_json_response(text)
        if data:
            return data
    return None


def extract_listing_fields(data: dict[str, Any]) -> dict[str, Any]:
    address = parse_address(first_key(data, {"Address", "PropertyAddress"}))
    parking_type = parse_parking_type(first_key(data, {"ParkingType", "Parking"}))
    basement = classify_basement(first_key(data, {"BasementDevelopment", "Basement", "BasementFeatures"}))
    return {
        "address": address,
        "property_type": clean_text(first_nested(data, "Building", {"Type"}) or first_key(data, {"Type", "PropertyType"})),
        "price": parse_money(first_key(data, {"PriceUnformattedValue", "Price", "PriceValue"})),
        "beds": parse_number(first_nested(data, "Building", {"Bedrooms", "BedroomsTotal"}) or first_key(data, {"Bedrooms", "BedroomsTotal"})),
        "baths": parse_number(first_nested(data, "Building", {"BathroomTotal", "Bathrooms"}) or first_key(data, {"BathroomTotal", "Bathrooms"})),
        "parking_type": parking_type,
        "parking_spaces": parse_number(first_key(data, {"ParkingSpaceTotal", "ParkingSpaces"})),
        "maintenance_fee": parse_money(first_key(data, {"MaintenanceFee", "MaintenanceFees", "CondoFee", "CondoFees"})),
        "basement": basement,
    }


def needs_realtor_enrichment(listing: dict[str, Any]) -> bool:
    return any(listing.get(key) in (None, "") for key in (
        "property_type", "price", "beds", "baths", "parking_type", "parking_spaces", "maintenance_fee", "basement"
    ))


def enrich_listing_with_realtor(listing: dict[str, Any]) -> dict[str, Any]:
    url = str(listing.get("url") or "")
    if not url.startswith(REALTOR_URL_PREFIX):
        return listing
    data = fetch_realtor_data(url)
    if not data:
        listing["confidence"] = append_note(
            listing.get("confidence"),
            "Manual verification needed: Realtor.ca listing facts could not be fetched automatically.",
        )
        return listing
    fields = extract_listing_fields(data)
    found = []
    for key, value in fields.items():
        if value in (None, ""):
            continue
        if listing.get(key) in (None, "", "No information"):
            listing[key] = value
            found.append(key)
    if listing.get("basement") in (None, ""):
        listing["basement"] = "No information"
    listing["source_urls"] = append_source(listing.get("source_urls"), url)
    if found:
        listing["confidence"] = append_note(listing.get("confidence"), "Realtor.ca listing facts fetched automatically.")
    else:
        listing["confidence"] = append_note(
            listing.get("confidence"),
            "Manual verification needed: Realtor.ca response did not include additional listing facts.",
        )
    return listing
