#!/usr/bin/env python3
"""
Reverse-geocode NOPD camera coordinates → admin-ready CSV.

Input:  new-orleans-surveillance-cameras-2026-2-27.csv  (Latitude, Longitude, Random ID)
Output: nopd_camera_import.csv  (CameraResource import format)

Usage (from project root, inside toolbox):
    uv run python3 scripts/import_nopd_cameras.py

Then: Django admin → Cameras → Import → upload nopd_camera_import.csv
"""

import csv
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing dependency: uv pip install requests", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).parent.parent
INPUT_CSV = ROOT / "new-orleans-surveillance-cameras-2026-2-27.csv"
OUTPUT_CSV = ROOT / "nopd_camera_import.csv"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
HEADERS = {"User-Agent": "nola-camera-import/1.0 (github.com/antoineclaval/new_orleans_surveillance_map)"}

# Column order must match CameraResource.Meta.fields exactly.
# Note: vetted_by_username field uses column_name="vetted_by" → header is "vetted_by".
OUTPUT_FIELDS = [
    "id",
    "cross_road",
    "street_address",
    "latitude",
    "longitude",
    "facial_recognition",
    "associated_shop",
    "camera_type",
    "status",
    "reported_by",
    "reported_at",
    "vetted_at",
    "vetted_by",
    "notes",
]


def reverse_geocode(lat: float, lon: float) -> tuple[str, str] | None:
    """
    Reverse-geocode (lat, lon) via Nominatim.
    Returns (street_address, display_name) or None on error/no result.
    Respects Nominatim's 1 req/sec policy.
    """
    time.sleep(1.1)
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": "1",
    }
    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data or "error" in data:
            return None
        address = data.get("address", {})
        display_name = data.get("display_name", "")
        house_number = address.get("house_number", "")
        road = address.get("road", "")
        if road:
            street_address = f"{house_number} {road}".strip() if house_number else road
        else:
            street_address = ""
        return street_address, display_name
    except Exception as e:
        print(f"    Nominatim error: {e}", file=sys.stderr)
    return None


def main():
    if not INPUT_CSV.exists():
        print(f"Input file not found: {INPUT_CSV}", file=sys.stderr)
        sys.exit(1)

    rows = []
    with INPUT_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = row.get("Latitude", "").strip()
            lon = row.get("Longitude", "").strip()
            if not lat or not lon:
                continue
            try:
                rows.append((float(lat), float(lon)))
            except ValueError:
                print(f"  Skipping invalid coordinates: lat={lat!r} lon={lon!r}", file=sys.stderr)

    print(f"Processing {len(rows)} records from {INPUT_CSV.name}...")
    print(f"Output: {OUTPUT_CSV.name}\n")

    results = []
    unresolved = []

    for i, (lat, lon) in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] ({lat}, {lon})")
        result = reverse_geocode(lat, lon)

        if result:
            street_address, display_name = result
            notes = f"reverse_geocoded:nominatim | {display_name[:80]}"
            record = {
                "id": "",
                "cross_road": "",
                "street_address": street_address,
                "latitude": lat,
                "longitude": lon,
                "facial_recognition": "False",
                "associated_shop": "",
                "camera_type": "nopd",
                "status": "vetted",
                "reported_by": "nopd_import_2026-02-27",
                "reported_at": "",
                "vetted_at": "",
                "vetted_by": "",
                "notes": notes,
            }
        else:
            print(f"  !! UNRESOLVED ({lat}, {lon})", file=sys.stderr)
            record = {
                "id": "",
                "cross_road": "",
                "street_address": "",
                "latitude": lat,
                "longitude": lon,
                "facial_recognition": "False",
                "associated_shop": "NOPD Camera",
                "camera_type": "nopd",
                "status": "vetted",
                "reported_by": "nopd_import_2026-02-27",
                "reported_at": "",
                "vetted_at": "",
                "vetted_by": "",
                "notes": "UNRESOLVED: reverse geocoding failed",
            }
            unresolved.append((lat, lon))

        results.append(record)

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{len(results)} records → {OUTPUT_CSV.name} ({len(unresolved)} unresolved)")
    if unresolved:
        print("Unresolved coordinates:", file=sys.stderr)
        for lat, lon in unresolved:
            print(f"  ({lat}, {lon})", file=sys.stderr)


if __name__ == "__main__":
    main()
