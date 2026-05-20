from __future__ import annotations

import re
from typing import Any


SAFETY_BY_COMMUNITY = {
    "arbeatha park": "Moderate",
    "arbeatha park / bells corners east": "Moderate",
    "arlington woods": "Very Safe",
    "barrhaven - half moon bay": "Very Safe",
    "barrhaven - heritage park": "Very Safe",
    "barrhaven - pheasant run": "Very Safe",
    "beacon hill south": "Moderate",
    "beaconwood": "Very Safe",
    "bells corners": "Moderate",
    "blackburn hamlet south": "Very Safe",
    "blossom park / kemp park / findlay creek": "Moderate",
    "blossom park / leitrim": "Moderate",
    "borden farm / carleton heights / parkwood hills": "Moderate",
    "britannia": "Moderate",
    "carleton square": "Moderate",
    "carlington": "Moderate",
    "carlsbad springs": "Very Safe",
    "carson grove": "Moderate",
    "castle heights / rideau high": "Moderate",
    "castle heights / vanier south": "Risky",
    "chatelaine village": "Very Safe",
    "convent glen north": "Very Safe",
    "convent glen south": "Very Safe",
    "cyrville": "Moderate",
    "emerald woods / sawmill creek": "Moderate",
    "fallingbrook / pineridge": "Very Safe",
    "guildwood estates / urbandale acres": "Moderate",
    "heron gate / industrial park": "Risky",
    "hiawatha park / convent glen": "Very Safe",
    "hunt club": "Moderate",
    "hunt club park / greenboro": "Moderate",
    "kanata - beaverbrook": "Very Safe",
    "kanata - emerald meadows / trailwest": "Very Safe",
    "kanata - katimavik": "Very Safe",
    "leslie park": "Moderate",
    "meadowlands / crestview": "Moderate",
    "mooney's bay / riverside park": "Moderate",
    "orleans / sunridge": "Very Safe",
    "overbrook": "Risky",
    "pineview": "Moderate",
    "queensway terrace north": "Moderate",
    "queenswood heights south": "Very Safe",
    "redwood park": "Moderate",
    "riverview park / elmvale": "Moderate",
    "sandy hill": "Moderate",
    "sawmill creek / timbermill": "Moderate",
    "sheffield glen / industrial park": "Moderate",
    "stittsville south": "Very Safe",
    "tanglewood": "Moderate",
    "vanier": "Risky",
    "viscount alexander park": "Moderate",
    "westcliffe estates": "Moderate",
    "windsor park village": "Moderate",
}


def canonical_community(community: Any) -> str:
    value = str(community or "").strip()
    value = re.sub(r"^\d+\s+", "", value)
    value = re.sub(r"^kanata-", "", value, flags=re.I)
    value = value.replace("And", "and")
    value = value.replace("Parkkemp", "Park / Kemp")
    value = value.replace("Parkfindlay", "Park / Findlay")
    value = value.replace("Bayriverside", "Bay / Riverside")
    value = value.replace("Farmcarleton", "Farm / Carleton")
    value = value.replace("Heightsparkwood", "Heights / Parkwood")
    value = value.replace("Hiawatha Parkconvent", "Hiawatha Park / Convent")
    value = value.replace("Heights South", "Heights South")
    value = re.sub(r"\s*/\s*", " / ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


def needs_safety_enrichment(listing: dict[str, Any]) -> bool:
    value = str(listing.get("safety_category") or "").strip().lower()
    return not value or "manual" in value or value == "safety pending"


def enrich_listing_with_safety(listing: dict[str, Any]) -> dict[str, Any]:
    key = canonical_community(listing.get("community"))
    safety = SAFETY_BY_COMMUNITY.get(key)
    if safety:
        listing["safety_category"] = safety
        listing["safety_notes"] = "Workbook-derived community safety classification; verify manually against current crime data before final decision."
    else:
        listing["safety_category"] = "Manual verification needed"
        listing["safety_notes"] = f"Manual verification needed: no saved safety rule for community '{listing.get('community') or 'unknown'}'."
    return listing
