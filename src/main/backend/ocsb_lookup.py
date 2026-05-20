from __future__ import annotations

import html
import http.cookiejar
import json
from pathlib import Path
import re
import ssl
import time
import urllib.parse
import urllib.request
from typing import Any

try:
    from .ocdsb_lookup import category, driving_distance_km
except ImportError:  # pragma: no cover
    from ocdsb_lookup import category, driving_distance_km


ROOT = Path(__file__).resolve().parents[3]
OCSB_CACHE_PATH = ROOT / "app_data" / "ocsb_cache.json"
OCSB_LOCATOR_URL = "https://schoollocator.ocsb.ca:8081/Eligibility.aspx?Page=School"
OCSB_AUTOCOMPLETE_URL = "https://schoollocator.ocsb.ca:8081/Eligibility.aspx/GetCompletionList"
OCSB_GRADE = "1"
OCSB_DISTRICT = "OCSB"
OCSB_CITY = "OTTAWA"
OCSB_DATABASE_FALLBACK = "eaee5363-36d3-4a06-a07e-27eabc90059d"
CACHE_VERSION = 1


def split_address(address: str) -> tuple[str | None, str | None]:
    cleaned = re.sub(r"\s+", " ", address.replace(",", " ")).strip()
    cleaned = re.sub(r"\bOttawa\b.*$", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"^[A-Za-z0-9]+\s*-\s*", "", cleaned)
    match = re.match(r"^(\d+[A-Za-z]?)\s+(.+)$", cleaned)
    if not match:
        return None, cleaned or None
    civic, street = match.groups()
    street = re.sub(r"\s+(ON|Canada)$", "", street, flags=re.I).strip()
    return civic, street


def street_variants(street: str | None) -> list[str]:
    if not street:
        return []
    base = re.sub(r"\s+", " ", street.replace(".", "")).strip()
    variants = []

    def add(value: str) -> None:
        value = re.sub(r"\s+", " ", value).strip()
        if value and value.lower() not in {item.lower() for item in variants}:
            variants.append(value)

    add(base)
    replacements = {
        "Avenue": "AVE", "Boulevard": "BLVD", "Crescent": "CRES", "Court": "CRT",
        "Circle": "CIR", "Drive": "DR", "Lane": "LANE", "Place": "PL", "Private": "PVT",
        "Road": "RD", "Street": "ST", "Terrace": "TERR", "Way": "WAY",
    }
    shortened = base
    for long, abbr in replacements.items():
        shortened = re.sub(rf"\b{long}\b", abbr, shortened, flags=re.I)
    add(shortened.upper())
    add(re.sub(r"\bSt\s+Laurent\b", "St-Laurent", base, flags=re.I).upper())
    add(re.sub(r"\bSt\s+Andre\b", "St-Andre", base, flags=re.I).upper())
    add(re.sub(r"\bSt\s+Laurent\b", "St-Laurent", shortened, flags=re.I).upper())
    add(re.sub(r"\bSt\s+Andre\b", "St-Andre", shortened, flags=re.I).upper())
    add(re.sub(r"\bJeanne\s+d['’]?Arc\b", "Jeanne D'Arc", base, flags=re.I).upper())
    no_direction = re.sub(r"\s+(N|S|E|W)$", "", shortened, flags=re.I)
    add(no_direction.upper())
    without_suffix = re.sub(
        r"\s+(AVE|AVENUE|BLVD|BOULEVARD|CIR|CIRCLE|CRES|CRESCENT|CRT|COURT|DR|DRIVE|LANE|PL|PLACE|PVT|PRIVATE|RD|ROAD|ST|STREET|TERR|TERRACE|WAY)$",
        "",
        shortened,
        flags=re.I,
    )
    add(without_suffix.upper())
    return variants


def civic_variants(civic: str | None) -> list[str]:
    if not civic:
        return [""]
    variants: list[str] = []

    def add(value: str) -> None:
        value = re.sub(r"\s+", " ", value).strip()
        if value and value.lower() not in {item.lower() for item in variants}:
            variants.append(value)

    add(civic)
    compact = re.match(r"^(\d+)([A-Za-z])$", civic)
    if compact:
        add(f"{compact.group(1)} {compact.group(2)}")
        add(compact.group(1))
    return variants


def cache() -> dict[str, Any]:
    empty = {"version": CACHE_VERSION, "autocomplete": {}, "school": {}}
    if not OCSB_CACHE_PATH.exists():
        return empty
    try:
        data = json.loads(OCSB_CACHE_PATH.read_text())
        return data if data.get("version") == CACHE_VERSION else empty
    except json.JSONDecodeError:
        return empty


def save_cache(data: dict[str, Any]) -> None:
    OCSB_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    OCSB_CACHE_PATH.write_text(json.dumps(data, indent=2, sort_keys=True))


def request_ocsb_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent": "homehunter-app/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    context = ssl._create_unverified_context()
    with urllib.request.urlopen(request, timeout=25, context=context) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def hidden_fields(page: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in re.finditer(r"<input[^>]+type=[\"']hidden[\"'][^>]*>", page, flags=re.I):
        tag = match.group(0)
        name = re.search(r"name=[\"']([^\"']+)[\"']", tag, flags=re.I)
        value = re.search(r"value=[\"']([^\"']*)[\"']", tag, flags=re.I)
        if name:
            fields[html.unescape(name.group(1))] = html.unescape(value.group(1) if value else "")
    return fields


def selected_database(page: str) -> str:
    match = re.search(
        r"<select[^>]+id=[\"']cbDefaultDatabase[\"'][^>]*>(.*?)</select>",
        page,
        flags=re.I | re.S,
    )
    if not match:
        return OCSB_DATABASE_FALLBACK
    selected = re.search(r"<option[^>]+selected=[\"']selected[\"'][^>]+value=[\"']([^\"']+)[\"']", match.group(1), flags=re.I)
    if selected:
        return html.unescape(selected.group(1))
    first = re.search(r"<option[^>]+value=[\"']([^\"']+)[\"']", match.group(1), flags=re.I)
    return html.unescape(first.group(1)) if first else OCSB_DATABASE_FALLBACK


def request_ocsb_page(civic: str, street: str) -> str:
    context = ssl._create_unverified_context()
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar),
        urllib.request.HTTPSHandler(context=context),
    )
    headers = {
        "User-Agent": "homehunter-app/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Referer": OCSB_LOCATOR_URL,
    }
    initial = opener.open(urllib.request.Request(OCSB_LOCATOR_URL, headers=headers), timeout=25).read().decode("utf-8", errors="replace")
    fields = hidden_fields(initial)
    fields.update({
        "ctl00$MainContent$eaSchool$txtStreetNumber": civic,
        "ctl00$MainContent$eaSchool$meeStreetNumber_ClientState": "",
        "ctl00$MainContent$eaSchool$txtStreetName": street,
        "ctl00$MainContent$eaSchool$ddlCity": OCSB_CITY,
        "ctl00$MainContent$eaSchool$hfPostCode": "",
        "ctl00$MainContent$eaSchool$ddlDistrict": OCSB_DISTRICT,
        "ctl00$MainContent$btnSubmit": "Submit",
        "ctl00$ddlLanguages": "en-CA",
        "ctl00$cbDefaultDatabase": selected_database(initial),
    })
    request = urllib.request.Request(
        OCSB_LOCATOR_URL,
        data=urllib.parse.urlencode(fields).encode("utf-8"),
        headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
    )
    return opener.open(request, timeout=25).read().decode("utf-8", errors="replace")


def extract_quoted_json(page: str, variable: str) -> Any | None:
    match = re.search(rf"{re.escape(variable)}\s*=\s*JSON\.parse\('((?:\\.|[^'])*)'\)", page)
    if not match:
        return None
    text = match.group(1)
    text = text.replace(r"\'", "'").replace(r'\"', '"').replace(r"\/", "/")
    try:
        return json.loads(text)
    except Exception:
        return None


def parse_ocsb_result(page: str) -> dict[str, Any]:
    positions = extract_quoted_json(page, "SchoolPositions")
    if positions:
        schools = [school for group in positions for school in group]
        grade_one = [school for school in schools if OCSB_GRADE in {str(grade) for grade in school.get("Grades", [])}]
        selected = grade_one[0] if grade_one else schools[0]
        return {
            "school": selected.get("Name"),
            "school_address": selected.get("Address"),
            "grades": selected.get("Grades", []),
            "phone": selected.get("ContactPhone"),
            "programs": selected.get("Programs", []),
            "grade_verified": bool(grade_one),
        }

    name = re.search(r'<span[^>]+class=["\']SchoolName["\'][^>]*>\s*([^<]+)', page, flags=re.I)
    address = re.search(r'id=["\']MainContent_repSchoolDetail_lblAddressValue_0["\'][^>]*>\s*([^<]+)', page, flags=re.I)
    grades = re.search(r'id=["\']MainContent_repSchoolDetail_rBoundary_0_lblGrades_0["\'][^>]*>\s*([^<]+)', page, flags=re.I)
    return {
        "school": " ".join(html.unescape(name.group(1)).split()) if name else None,
        "school_address": " ".join(html.unescape(address.group(1)).split()) if address else None,
        "grades": [item.strip() for item in html.unescape(grades.group(1)).split(",")] if grades else [],
        "grade_verified": bool(grades and OCSB_GRADE in {item.strip() for item in html.unescape(grades.group(1)).split(",")}),
    }


def ocsb_street_autocomplete(street: str, city: str = "OTTAWA") -> list[str]:
    data = cache()
    key = f"{city.lower()}:{street.lower()}"
    if key in data["autocomplete"]:
        return data["autocomplete"][key]
    try:
        data = request_ocsb_json(
            OCSB_AUTOCOMPLETE_URL,
            {"prefixText": street, "count": 100, "contextKey": city.upper()},
        )
        values = data.get("d", [])
        result = [str(value) for value in values if value]
        cache_data = cache()
        cache_data["autocomplete"][key] = result
        save_cache(cache_data)
        time.sleep(0.2)
        return result
    except Exception:
        return []


def ordered_street_matches(matches: list[str], variant: str) -> list[str]:
    variant_normalized = re.sub(r"\s+", " ", variant).strip().upper()
    return sorted(
        matches,
        key=lambda match: (
            "ACC" in match.upper(),
            match.upper() != variant_normalized,
            len(match),
        ),
    )


def ocsb_school_lookup(address: str) -> dict[str, Any]:
    data = cache()
    cache_key = address.lower()
    cached = data["school"].get(cache_key)
    if cached and cached.get("school"):
        return cached
    civic, street = split_address(address)
    tried: list[str] = []
    last_result: dict[str, Any] | None = None
    for variant in street_variants(street):
        tried.append(variant)
        matches = ordered_street_matches(ocsb_street_autocomplete(variant), variant)
        for matched_street in matches:
            for civic_variant in civic_variants(civic):
                locator_address = f"{civic_variant} {matched_street}".strip()
                tried.append(locator_address)
                result: dict[str, Any] = {
                    "locator_address": locator_address,
                    "matched_street": matched_street,
                    "tried": tried,
                }
                try:
                    page = request_ocsb_page(civic_variant, matched_street)
                    result.update(parse_ocsb_result(page))
                    if not result.get("school"):
                        result["error"] = "OCSB returned no school for the matched address."
                    elif not result.get("grade_verified"):
                        result["error"] = f"OCSB school found, but Grade {OCSB_GRADE} coverage was not verified."
                except Exception as exc:
                    result["error"] = f"OCSB lookup failed: {exc}"
                if result.get("school") and not result.get("error"):
                    data = cache()
                    data["school"][cache_key] = result
                    save_cache(data)
                    return result
                last_result = result
    if last_result:
        data = cache()
        data["school"][cache_key] = last_result
        save_cache(data)
        return last_result
    return {
        "school": None,
        "locator_address": None,
        "tried": tried,
        "error": "Address not found in OCSB street autocomplete.",
    }


def enrich_listing_with_ocsb(listing: dict[str, Any]) -> dict[str, Any]:
    address = str(listing.get("address") or "").strip()
    listing["source_urls"] = "; ".join(filter(None, [str(listing.get("source_urls") or listing.get("url") or ""), OCSB_LOCATOR_URL]))
    if not address:
        listing["school"] = "OCSB: Manual verification needed"
        listing["school_distance_km"] = None
        listing["school_distance_category"] = None
        listing["confidence"] = "Manual verification needed: address could not be extracted from Realtor.ca URL."
        return listing
    result = ocsb_school_lookup(address)
    if not result.get("school"):
        listing["school"] = "OCSB: Manual verification needed"
        listing["school_distance_km"] = None
        listing["school_distance_category"] = None
        listing["confidence"] = (
            f"Manual verification needed: {result.get('error', 'OCSB school not found')} "
            f"Tried: {', '.join(result.get('tried', [])[:6])}"
        )
        return listing
    listing["school"] = f"OCSB: {result['school']}"
    distance = None
    if result.get("school_address"):
        distance = driving_distance_km(result["locator_address"], result["school_address"])
    listing["school_distance_km"] = distance
    listing["school_distance_category"] = category(distance)
    listing["confidence"] = f"Verified via OCSB locator address: {result.get('locator_address')}."
    return listing
