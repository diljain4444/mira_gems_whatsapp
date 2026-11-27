"""
services/inventory_service.py

Thin adapter layer connecting existing core modules to the FastAPI routes.

IMPORTANT: This file does NOT rewrite any business logic.
It only:
  1. Parses raw input strings into clean ID lists.
  2. Calls the existing functions in particular_info.py and inventory_fetching.py.
  3. Adds the inventory statistics that find_matching_diamonds() alone doesn't return.
"""
import re
import sys
from pathlib import Path

# Ensure core/ is importable regardless of where uvicorn is launched from
_core_path = str(Path(__file__).parent.parent / "core")
if _core_path not in sys.path:
    sys.path.insert(0, _core_path)

import particular_info        # existing file — get_multiple_stone_details()
import inventory_fetching     # existing file — find_matching_diamonds(), fetch_inventory()


def parse_stone_ids(raw_input: str) -> list[str]:
    """
    Convert a free-text string of Stock IDs into a deduplicated list.

    Supports separators: newline, carriage return, comma, semicolon,
    and space. Duplicate IDs are removed while preserving first-seen order.
    Case-insensitive deduplication (preserves original casing).
    """
    # Split on any combination of newline / comma / semicolon first
    parts = re.split(r"[\n\r,;]+", raw_input)
    ids: list[str] = []
    seen: set[str] = set()
    for part in parts:
        # Further split on whitespace to handle space-separated IDs on one line
        for token in part.split():
            cleaned = token.strip()
            if cleaned and cleaned.upper() not in seen:
                seen.add(cleaned.upper())
                ids.append(cleaned)
    return ids


def lookup_stones_by_ids(raw_input: str) -> dict:
    """
    Parse raw input and call particular_info.get_multiple_stone_details().

    Returns the existing result dict, enriched with unique_requested count.
    """
    stone_ids = parse_stone_ids(raw_input)

    if not stone_ids:
        raise ValueError("No valid Stock IDs found in input.")

    result = particular_info.get_multiple_stone_details(stone_ids)
    result["unique_requested"] = len(stone_ids)
    return result


def search_by_demand(requirement: dict) -> dict:
    """
    Fetch inventory once and compute:
      - total inventory
      - total available stones
      - matched stones (all filters applied)
      - available-but-not-matched count
      - similar_diamonds (top similar alternatives when no exact match found)

    Uses the existing inventory_fetching functions directly.
    The matches_stone() and calculate_business_category() functions are
    called exactly as inventory_fetching.find_matching_diamonds() would call them,
    so the results are identical — we just expose the inventory statistics too.
    """
    # Single inventory fetch for this request
    inventory = inventory_fetching.fetch_inventory()

    total_inventory = len(inventory)

    # Count available stones (Availability == "A" or "AVAILABLE")
    available_stones = [
        s for s in inventory
        if isinstance(s, dict) and inventory_fetching.matches_availability(s)
    ]
    total_available = len(available_stones)

    # Apply all filters (availability + all customer requirements)
    matched: list[dict] = []
    for stone in inventory:
        if not isinstance(stone, dict):
            continue
        if inventory_fetching.matches_stone(stone, requirement):
            stone_result = stone.copy()
            stone_result["business_category"] = inventory_fetching.calculate_business_category(stone)
            # Normalize availability for display
            stone_result["Availability"] = inventory_fetching.clean_text(stone.get("Availability", ""))
            matched.append(stone_result)

    total_matched = len(matched)
    total_available_not_matched = max(0, total_available - total_matched)

    # ── Fallback: find nearest similar diamonds when no exact match ──────────
    similar: list[dict] = []
    if total_matched == 0:
        # Reuse the already-fetched inventory to avoid a duplicate network call
        similar = inventory_fetching.find_similar_diamonds(requirement, inventory=inventory)

    return {
        "total_inventory": total_inventory,
        "total_available": total_available,
        "total_matched": total_matched,
        "total_available_not_matched": total_available_not_matched,
        "matched_diamonds": matched,
        "similar_diamonds": similar,
    }
