#!/usr/bin/env python3
"""
Geocode camera_record_to_import.csv → clean_camera_import.csv

Usage:
    pip install requests          # required
    pip install duckduckgo-search # optional, enables web search fallback
    python scripts/import_loose_records.py

Geocoding strategies (tried in order for each row):
  1. Nominatim: "<address>, New Orleans, Louisiana"
  2. Nominatim: "<business name>, New Orleans, Louisiana"
  3. DuckDuckGo search for "<business name> New Orleans" → extract address → Nominatim
  4. Mark as UNRESOLVED in notes if all strategies fail

Output columns match the CameraResource import format (django-import-export):
  cross_road, street_address, latitude, longitude,
  facial_recognition, associated_shop, status, notes
"""

import csv
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing dependency: uv pip install requests", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).parent.parent
INPUT_CSV = ROOT / "camera_record_to_import.csv"
OUTPUT_CSV = ROOT / "clean_camera_import.csv"
FAILURES_CSV = ROOT / "camera_import_failures.csv"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "nola-camera-import/1.0 (github.com/antoineclaval/new_orleans_surveillance_map)"}

# Matches "123 Main St", "456 N. Robertson St", etc.
ADDR_RE = re.compile(
    r"\b\d{1,5}\s+(?:[NSEW]\.?\s+)?[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*"
    r"\s+(?:St(?:reet)?|Ave(?:nue)?|Blvd|Rd|Dr|Ct|Ln|Pl|Way|Hwy|Pkwy|Bienville|Bourbon|Decatur|Frenchmen|Chartres|Royal|Toulouse|Burgundy|Iberville|Canal|Tchoupitoulas|Tchoup)\b",
    re.IGNORECASE,
)

OUTPUT_FIELDS = [
    "id",
    "cross_road",
    "street_address",
    "latitude",
    "longitude",
    "facial_recognition",
    "associated_shop",
    "status",
    "reported_by",
    "reported_at",
    "vetted_at",
    "vetted_by",
    "notes",
]


def nominatim_geocode(query: str) -> tuple[float, float, str] | None:
    """Return (lat, lon, display_name) or None. Respects 1 req/sec rate limit."""
    time.sleep(1.1)
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "us",
        "addressdetails": "1",
    }
    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        results = resp.json()
        if results:
            r = results[0]
            return float(r["lat"]), float(r["lon"]), r.get("display_name", "")
    except Exception as e:
        print(f"    Nominatim error: {e}", file=sys.stderr)
    return None


def ddg_find_address(business_name: str) -> str | None:
    """
    Search DuckDuckGo for the business in New Orleans and try to extract
    a street address from the result snippets.
    Returns a raw address string to feed into Nominatim, or None.
    """
    try:
        try:
            from ddgs import DDGS  # new package name
        except ImportError:
            from duckduckgo_search import DDGS  # legacy name
    except ImportError:
        print(
            "    ddgs not installed — skipping web fallback.\n"
            "    Install with: uv pip install ddgs",
            file=sys.stderr,
        )
        return None

    query = f"{business_name} New Orleans address"
    try:
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=5):
                text = result.get("body", "") + " " + result.get("title", "")
                match = ADDR_RE.search(text)
                if match:
                    found = match.group(0).strip()
                    print(f"    DDG snippet address: {found!r}")
                    return found
    except Exception as e:
        print(f"    DDG error: {e}", file=sys.stderr)
    return None


# Common NOLA street abbreviation expansions
_NOLA_EXPANSIONS = [
    (re.compile(r"\bTchoup\b", re.IGNORECASE), "Tchoupitoulas"),
    (re.compile(r"\bSt\.?\s+Phillip\b", re.IGNORECASE), "St Philip"),
    (re.compile(r"\bRoberston\b", re.IGNORECASE), "Robertson"),
    (re.compile(r"\bS\.\s+Peters\b", re.IGNORECASE), "South Peters"),
    (re.compile(r"\bN\.\s+Robertson\b", re.IGNORECASE), "North Robertson"),
]


def normalize_address(address: str) -> str:
    """Expand common NOLA abbreviations/typos before geocoding."""
    for pattern, replacement in _NOLA_EXPANSIONS:
        address = pattern.sub(replacement, address)
    return address


def ensure_nola(address: str) -> str:
    """Normalize abbreviations and append New Orleans context if not already present."""
    address = normalize_address(address)
    low = address.lower()
    if "new orleans" in low or "louisiana" in low:
        return address
    return f"{address}, New Orleans, Louisiana"


def geocode_row(business_name: str, apparent_address: str) -> dict:
    """
    Try all geocoding strategies for one row.
    Returns a dict with latitude, longitude, street_address, notes.
    """
    # Strategy 1: provided address via Nominatim
    if apparent_address:
        query = ensure_nola(apparent_address)
        print(f"  [1] Nominatim address: {query!r}")
        result = nominatim_geocode(query)
        if result:
            lat, lon, display = result
            return {"latitude": lat, "longitude": lon, "street_address": apparent_address, "notes": f"geocoded:nominatim_address | {display[:80]}"}

    # Strategy 2: business name via Nominatim
    if business_name:
        query = f"{business_name}, New Orleans, Louisiana"
        print(f"  [2] Nominatim name: {query!r}")
        result = nominatim_geocode(query)
        if result:
            lat, lon, display = result
            return {"latitude": lat, "longitude": lon, "street_address": apparent_address, "notes": f"geocoded:nominatim_name | {display[:80]}"}

    # Strategy 3: DuckDuckGo web search → extract address → Nominatim
    if business_name:
        print(f"  [3] DuckDuckGo search for: {business_name!r}")
        addr_from_web = ddg_find_address(business_name)
        if addr_from_web:
            query = ensure_nola(addr_from_web)
            print(f"      Re-geocoding: {query!r}")
            result = nominatim_geocode(query)
            if result:
                lat, lon, display = result
                return {"latitude": lat, "longitude": lon, "street_address": addr_from_web, "notes": f"geocoded:ddg_fallback | {display[:80]}"}

    print(f"  !! UNRESOLVED")
    return {"latitude": "", "longitude": "", "street_address": apparent_address, "notes": "UNRESOLVED: manual geocoding needed"}


def main():
    if not INPUT_CSV.exists():
        print(f"Input file not found: {INPUT_CSV}", file=sys.stderr)
        sys.exit(1)

    rows = []
    with INPUT_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for line in reader:
            # Pad to at least 2 columns and strip empties
            while len(line) < 2:
                line.append("")
            business_name = line[0].strip()
            apparent_address = line[1].strip().rstrip(",").strip()
            # Skip completely empty rows
            if not business_name and not apparent_address:
                continue
            rows.append((business_name, apparent_address))

    print(f"Processing {len(rows)} records from {INPUT_CSV.name}...")
    print(f"Output: {OUTPUT_CSV.name}\n")

    results = []
    for i, (business_name, apparent_address) in enumerate(rows, 1):
        label = business_name or apparent_address
        print(f"[{i}/{len(rows)}] {label!r}")

        geo = geocode_row(business_name, apparent_address)

        results.append({
            "id": "",
            "cross_road": "",
            "street_address": geo["street_address"],
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
            "facial_recognition": "False",
            "associated_shop": business_name,
            "status": "pending",
            "reported_by": "",
            "reported_at": "",
            "vetted_at": "",
            "vetted_by": "",
            "notes": geo["notes"],
        })

    resolved = [r for r in results if r["latitude"] != ""]
    unresolved = [r for r in results if r["latitude"] == ""]

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(resolved)

    FAILURE_FIELDS = ["associated_shop", "street_address", "notes"]
    with FAILURES_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FAILURE_FIELDS)
        writer.writeheader()
        for r in unresolved:
            writer.writerow({k: r[k] for k in FAILURE_FIELDS})

    print(f"\nDone. {len(resolved)} resolved → {OUTPUT_CSV}")
    if unresolved:
        print(f"      {len(unresolved)} unresolved → {FAILURES_CSV}")
        for r in unresolved:
            print(f"  - {r['associated_shop']!r} / {r['street_address']!r}")


if __name__ == "__main__":
    main()
