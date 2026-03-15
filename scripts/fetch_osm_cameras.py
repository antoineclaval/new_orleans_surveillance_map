#!/usr/bin/env python3
"""
Fetch OSM surveillance camera nodes within New Orleans (Orleans Parish) via Overpass API.

Uses the official city limits polygon (OSM relation 1836428) as the query boundary.
Area ID = 3601836428 (relation 1836428 + 3600000000, Overpass convention).

Usage:
    uv pip install overpy
    uv run python3 scripts/fetch_osm_cameras.py [--output PATH]

Output CSV matches the CameraResource import format for django-import-export,
including the osm_id column for deduplication.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    import overpy
except ImportError:
    print("Missing dependency: uv pip install overpy", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).parent.parent
DEFAULT_OUTPUT = ROOT / "osm_cameras.csv"

# Orleans Parish city limits — OSM relation 1836428
# Area ID = relation ID + 3600000000 (Overpass convention for relation-derived areas)
OVERPASS_QUERY = """
[out:json][timeout:90];
area(3601836428)->.searchArea;
node["man_made"="surveillance"](area.searchArea);
out body;
"""

OUTPUT_FIELDS = [
    "id",
    "osm_id",
    "cross_road",
    "street_address",
    "latitude",
    "longitude",
    "facial_recognition",
    "associated_shop",
    "camera_type",
    "manufacturer",
    "direction",
    "status",
    "reported_by",
    "reported_at",
    "vetted_at",
    "vetted_by",
    "notes",
]


def node_to_row(node) -> dict:
    tags = node.tags

    housenumber = tags.get("addr:housenumber", "")
    street = tags.get("addr:street", "")
    if housenumber and street:
        street_address = f"{housenumber} {street}"
    elif street:
        street_address = street
    else:
        street_address = ""

    surveillance_type = tags.get("surveillance:type", "")
    facial_recognition = "True" if surveillance_type.lower() == "fr" else "False"
    camera_type = "alpr" if surveillance_type == "ALPR" else "unknown"

    manufacturer = tags.get("manufacturer", "")
    direction = tags.get("direction", "")

    # Store all OSM tags in notes for full traceability (exclude promoted fields)
    notes_tags = {k: v for k, v in tags.items() if k not in ("manufacturer", "direction")}
    notes_data = {"osm_node_id": node.id, "tags": notes_tags}

    return {
        "id": "",
        "osm_id": node.id,
        "cross_road": "",
        "street_address": street_address,
        "latitude": float(node.lat),
        "longitude": float(node.lon),
        "facial_recognition": facial_recognition,
        "associated_shop": tags.get("name", ""),
        "camera_type": camera_type,
        "manufacturer": manufacturer,
        "direction": direction,
        "status": "pending",
        "reported_by": "",
        "reported_at": "",
        "vetted_at": "",
        "vetted_by": "",
        "notes": json.dumps(notes_data, ensure_ascii=False),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT.name})",
    )
    args = parser.parse_args()

    print("Querying Overpass API for surveillance nodes in Orleans Parish...")
    print("  Boundary: OSM relation 1836428 (Orleans Parish)")

    api = overpy.Overpass()
    try:
        result = api.query(OVERPASS_QUERY)
    except overpy.exception.OverPyException as e:
        print(f"Overpass query failed: {e}", file=sys.stderr)
        sys.exit(1)

    nodes = result.nodes
    print(f"  Found {len(nodes)} surveillance node(s)")

    if not nodes:
        print("No nodes found — nothing to write.")
        return

    rows = [node_to_row(n) for n in nodes]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Written to: {args.output}")
    print()
    print("Breakdown by surveillance:type:")
    from collections import Counter
    types = Counter(
        json.loads(r["notes"])["tags"].get("surveillance:type", "(none)")
        for r in rows
    )
    for t, count in types.most_common():
        print(f"  {t}: {count}")


if __name__ == "__main__":
    main()
