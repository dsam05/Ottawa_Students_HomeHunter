from __future__ import annotations

import html
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OCDSB_CACHE_PATH = ROOT / "app_data" / "ocdsb_cache.json"
OCDSB_LOCATOR_URL = "https://staffapps.ocdsb.ca/school_locator/default.aspx"
OCDSB_AUTOCOMPLETE_URL = "https://staffapps.ocdsb.ca/School_Locator/WebService.asmx/CompleteAddress"
OCDSB_YEAR = "20262027"
OCDSB_PROGRAM = "English Program with Core French"
OCDSB_GRADE = "01"
GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
ROUTE_URL = "https://router.project-osrm.org/route/v1/driving"
CACHE_VERSION = 2


def category(distance: Any) -> str | None:
    if distance in (None, ""):
        return None
    try:
        value = float(distance)
    except (TypeError, ValueError):
        return None
    if value <= 1.0:
        return "Preferred"
    if value <= 1.5:
        return "Considerable"
    return "Too Far"


def cache() -> dict[str, Any]:
    empty = {"version": CACHE_VERSION, "autocomplete": {}, "school": {}, "geocode": {}, "route": {}}
    if not OCDSB_CACHE_PATH.exists():
        return empty
    try:
        data = json.loads(OCDSB_CACHE_PATH.read_text())
        return data if data.get("version") == CACHE_VERSION else empty
    except json.JSONDecodeError:
        return empty


def save_cache(data: dict[str, Any]) -> None:
    OCDSB_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    OCDSB_CACHE_PATH.write_text(json.dumps(data, indent=2, sort_keys=True))


def request_text(url: str, data: dict[str, str] | None = None, json_body: dict[str, str] | None = None) -> str:
    headers = {
        "User-Agent": "homehunter-app/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml,application/json",
    }
    body: bytes | None = None
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
        headers["Accept"] = "application/json"
    elif data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    context = ssl._create_unverified_context() if "staffapps.ocdsb.ca" in url else None
    request_obj = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(request_obj, timeout=25, context=context) as response:
        return response.read().decode("utf-8", errors="replace")


def hidden_fields(page: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in re.finditer(r'<input[^>]+type="hidden"[^>]*>', page, flags=re.I):
        tag = match.group(0)
        name = re.search(r'name="([^"]+)"', tag)
        value = re.search(r'value="([^"]*)"', tag)
        if name:
            fields[html.unescape(name.group(1))] = html.unescape(value.group(1) if value else "")
    return fields


class LocatorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.current: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []
        self.select_args: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag.lower() in {"td", "th"}:
            self.in_cell = True
            self.current = []
        if tag.lower() == "a":
            href = attr.get("href") or ""
            match = re.search(r"__doPostBack\('gvAddresses','([^']+)'\)", href)
            if match:
                self.select_args.append(match.group(1))

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"td", "th"} and self.in_cell:
            text = " ".join("".join(self.current).split())
            self.row.append(text)
            self.in_cell = False
        if tag.lower() == "tr" and self.row:
            self.rows.append(self.row)
            self.row = []


def address_variants(address: str) -> list[str]:
    base = re.sub(r"\s+", " ", address.replace(",", " ")).strip()
    base = re.sub(r"\bOttawa\b.*$", "", base, flags=re.I).strip()
    base = base.replace("St. ", "St-").replace("St ", "St-")
    base = re.sub(r"\bJeanne\s+d['’]?Arc\b", "Jeanne-d'Arc", base, flags=re.I)
    variants: list[str] = []

    def add(value: str) -> None:
        value = re.sub(r"\s+", " ", value.replace(".", "")).strip(" -")
        if value and value.lower() not in {item.lower() for item in variants}:
            variants.append(value)

    add(base)
    add(re.sub(r"\bPrivate\b", "Priv", base, flags=re.I))
    replacements = {
        "Avenue": "Ave", "Boulevard": "Blvd", "Crescent": "Cres", "Court": "Crt",
        "Drive": "Dr", "Lane": "Lane", "Place": "Pl", "Private": "Priv",
        "Road": "Rd", "Street": "St", "Terrace": "Terr", "Way": "Way",
    }
    short = base
    for long, abbr in replacements.items():
        short = re.sub(rf"\b{long}\b", abbr, short, flags=re.I)
    add(short)

    unit_match = re.match(r"^([A-Za-z0-9]+)\s*-\s*(\d+[A-Za-z]?)\s+(.+)$", base)
    if unit_match:
        unit, civic, rest = unit_match.groups()
        split_civic = re.sub(r"^(\d+)([A-Za-z])$", r"\1 \2", civic)
        rest_parts = rest.split()
        if len(rest_parts) > 1:
            street_type = rest_parts[-1]
            short_type = replacements.get(street_type, street_type)
            street_name = " ".join(rest_parts[:-1])
            add(f"{split_civic} {street_name} {unit} {street_type}")
            add(f"{split_civic} {street_name} {unit} {short_type}")
            add(f"{split_civic} {street_name} {unit.replace('PH', 'PH ', 1)} {street_type}")
            add(f"{split_civic} {street_name} {unit.replace('PH', 'PH ', 1)} {short_type}")
            unit_letter = re.search(r"([A-Za-z])$", unit)
            unit_number = re.sub(r"\D+$", "", unit)
            if unit_letter and unit_number:
                add(f"{split_civic} {unit_letter.group(1)} {street_name} {unit_number} {street_type}")
                add(f"{split_civic} {unit_letter.group(1)} {street_name} {unit_number} {short_type}")
            if re.search(r"\bSt-", street_name):
                unit_num = re.sub(r"\D+$", "", unit) or unit
                add(f"{split_civic} {street_name} {unit_num} {street_type}")
                add(f"{split_civic} {street_name} {unit_num} {short_type}")
        add(f"{civic} {unit} {rest}")
        add(f"{split_civic} {unit} {rest}")
        add(f"{civic} {rest}")
        add(f"{split_civic} {rest}")

    compact = re.match(r"^(\d+)([A-Za-z])\s+(.+)$", base)
    if compact:
        add(f"{compact.group(1)} {compact.group(2)} {compact.group(3)}")

    for variant in list(variants):
        add(re.sub(r"\s+(Ave|Avenue|Blvd|Boulevard|Cres|Crescent|Crt|Court|Dr|Drive|Lane|Pl|Place|Priv|Private|Rd|Road|St|Street|Terr|Terrace|Way)$", "", variant, flags=re.I))
        no_direction = re.sub(r"\s+(N|S|E|W)$", "", variant, flags=re.I)
        add(no_direction)
        shortened = variant
        for long, abbr in replacements.items():
            shortened = re.sub(rf"\b{long}\b", abbr, shortened, flags=re.I)
        add(shortened)
    return variants[:30]


def ocdsb_autocomplete(address: str) -> str | None:
    data = cache()
    key = address.lower()
    if key in data["autocomplete"]:
        return data["autocomplete"][key]
    try:
        raw = request_text(OCDSB_AUTOCOMPLETE_URL, json_body={"prefixText": address, "contextKey": OCDSB_YEAR})
        values = json.loads(raw).get("d", [])
        result = values[0] if values else None
    except Exception:
        return None
    data["autocomplete"][key] = result
    save_cache(data)
    time.sleep(0.2)
    return result


def find_locator_address(address: str) -> tuple[str | None, list[str]]:
    tried: list[str] = []
    for variant in address_variants(address):
        tried.append(variant)
        match = ocdsb_autocomplete(variant)
        if match:
            return match, tried
    return None, tried


def parse_school_result(page: str) -> tuple[str | None, str | None, str | None]:
    parser = LocatorParser()
    parser.feed(page)
    for index, row in enumerate(parser.rows):
        joined = " | ".join(row)
        if OCDSB_PROGRAM in joined and f"| {OCDSB_GRADE} |" in f"| {joined} |":
            school = row[1] if len(row) > 1 else None
            argument = parser.select_args[min(index - 1, len(parser.select_args) - 1)] if parser.select_args else None
            return school, argument, joined
    return None, None, None


def parse_school_address(page: str) -> str | None:
    match = re.search(r'id="dvSchool_dvSchoollbAddress"[^>]*>\s*([^<]+)', page)
    if match:
        return " ".join(html.unescape(match.group(1)).split())
    return None


def ocdsb_school_lookup(address: str) -> dict[str, Any]:
    data = cache()
    cache_key = address.lower()
    cached = data["school"].get(cache_key)
    if (
        cached
        and "Address not found in OCDSB autocomplete" not in str(cached.get("error", ""))
        and cached.get("school") != cached.get("locator_address")
    ):
        return data["school"][cache_key]
    locator_address, tried = find_locator_address(address)
    result: dict[str, Any] = {"locator_address": locator_address, "tried": tried}
    if not locator_address:
        result["error"] = "Address not found in OCDSB autocomplete."
        data["school"][cache_key] = result
        save_cache(data)
        return result
    try:
        initial = request_text(OCDSB_LOCATOR_URL)
        fields = hidden_fields(initial)
        fields.update({
            "ddlSchoolYear": OCDSB_YEAR,
            "tbStreet": locator_address,
            "ckprogram$3": OCDSB_PROGRAM,
            "ckgrade$2": OCDSB_GRADE,
            "btFind": "Search schools.",
        })
        page = request_text(OCDSB_LOCATOR_URL, data=fields)
        school, event_argument, raw_row = parse_school_result(page)
        result.update({"school": school, "raw_row": raw_row})
        if event_argument:
            detail_fields = hidden_fields(page)
            detail_fields.update({
                "__EVENTTARGET": "gvAddresses",
                "__EVENTARGUMENT": event_argument,
                "ddlSchoolYear": OCDSB_YEAR,
                "tbStreet": locator_address,
                "ckprogram$3": OCDSB_PROGRAM,
                "ckgrade$2": OCDSB_GRADE,
            })
            detail_page = request_text(OCDSB_LOCATOR_URL, data=detail_fields)
            result["school_address"] = parse_school_address(detail_page)
        if not school:
            result["error"] = "OCDSB returned no Grade 01 English/Core French school."
    except Exception as exc:
        result["error"] = f"OCDSB lookup failed: {exc}"
    data["school"][cache_key] = result
    save_cache(data)
    return result


def geocode(query: str) -> tuple[float, float] | None:
    data = cache()
    key = query.lower()
    if key in data["geocode"]:
        value = data["geocode"][key]
        return tuple(value) if value else None
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": "1", "countrycodes": "ca"})
    try:
        raw = request_text(f"{GEOCODE_URL}?{params}")
        values = json.loads(raw)
        result = (float(values[0]["lat"]), float(values[0]["lon"])) if values else None
    except Exception:
        result = None
    data["geocode"][key] = list(result) if result else None
    save_cache(data)
    time.sleep(1.0)
    return result


def geocode_candidates(address: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", address.replace(",", " ")).strip()
    cleaned = re.sub(r"\s+ON\s+Canada$", "", cleaned, flags=re.I)
    candidates = [cleaned]
    expanded = cleaned
    for abbr, long in {
        "Ave": "Avenue", "Blvd": "Boulevard", "Cres": "Crescent", "Crt": "Court",
        "Dr": "Drive", "Pl": "Place", "Priv": "Private", "Rd": "Road",
        "St": "Street", "Terr": "Terrace",
    }.items():
        expanded = re.sub(rf"\b{abbr}\b", long, expanded, flags=re.I)
    candidates.append(expanded)
    if not re.search(r"\bOttawa\b", expanded, flags=re.I):
        candidates.append(f"{expanded} Ottawa")
    return list(dict.fromkeys(candidates))


def geocode_first(address: str) -> tuple[float, float] | None:
    for candidate in geocode_candidates(address):
        result = geocode(candidate)
        if result:
            return result
    return None


def driving_distance_km(origin: str, destination: str) -> float | None:
    data = cache()
    key = f"{origin.lower()} -> {destination.lower()}"
    if key in data["route"] and data["route"][key] is not None:
        return data["route"][key]
    start = geocode_first(origin)
    end = geocode_first(destination)
    if not start or not end:
        data["route"][key] = None
        save_cache(data)
        return None
    url = f"{ROUTE_URL}/{start[1]},{start[0]};{end[1]},{end[0]}?overview=false"
    try:
        raw = request_text(url)
        routes = json.loads(raw).get("routes", [])
        result = round(routes[0]["distance"] / 1000, 2) if routes else None
    except Exception:
        result = None
    data["route"][key] = result
    save_cache(data)
    return result


def needs_school_enrichment(listing: dict[str, Any]) -> bool:
    school = str(listing.get("school") or "").lower()
    confidence = str(listing.get("confidence") or "").lower()
    return not school or "manual" in school or "manual" in confidence or listing.get("school_distance_km") in (None, "")


def enrich_listing_with_ocdsb(listing: dict[str, Any]) -> dict[str, Any]:
    address = str(listing.get("address") or "").strip()
    if not address:
        listing["confidence"] = "Manual verification needed: address could not be extracted from Realtor.ca URL."
        return listing
    result = ocdsb_school_lookup(address)
    listing["source_urls"] = "; ".join(filter(None, [str(listing.get("source_urls") or listing.get("url") or ""), OCDSB_LOCATOR_URL]))
    if not result.get("school"):
        listing["school"] = "Manual verification needed"
        listing["school_distance_km"] = None
        listing["school_distance_category"] = None
        listing["confidence"] = f"Manual verification needed: {result.get('error', 'OCDSB school not found')} Tried: {', '.join(result.get('tried', [])[:6])}"
        return listing
    listing["school"] = result["school"]
    distance = None
    if result.get("school_address"):
        distance = driving_distance_km(result["locator_address"], result["school_address"])
    listing["school_distance_km"] = distance
    listing["school_distance_category"] = category(distance)
    if distance is None:
        listing["confidence"] = "Manual verification needed: OCDSB school found, but route distance could not be calculated."
    else:
        listing["confidence"] = f"Verified via OCDSB locator address: {result['locator_address']}."
    return listing
