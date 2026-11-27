"""
api/stone_routes.py — POST /api/stones/lookup

Find one or multiple diamonds by Stock ID.
Wraps particular_info.get_multiple_stone_details() via inventory_service.
"""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

from app.schemas.stone import StoneLookupRequest, StoneLookupResponse, StoneDetail
from app.services.inventory_service import lookup_stones_by_ids

router = APIRouter(tags=["Stones"])


def _to_float(value) -> float | None:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        s = str(value).strip()
        return float(s) if s else None
    except (ValueError, TypeError):
        return None


@router.post("/stones/lookup", response_model=StoneLookupResponse)
async def lookup_stones(request: StoneLookupRequest):
    """
    Look up one or multiple diamonds by Stock ID.

    Accepts free-text input — newline, comma, semicolon, or space separated.
    Returns full stone details for found IDs, and lists not-found / duplicate IDs.
    If the inventory API fails, returns HTTP 502 (do not claim the stone is unavailable).
    """
    if not request.stone_ids or not request.stone_ids.strip():
        raise HTTPException(status_code=400, detail="stone_ids must not be empty.")

    try:
        result = lookup_stones_by_ids(request.stone_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Inventory API error: {exc}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during stone lookup: {exc}"
        )

    matched_stones: list[StoneDetail] = []
    for stone in result.get("matched_stones", []):
        try:
            matched_stones.append(StoneDetail(
                StockId=str(stone.get("StockId") or ""),
                Availability=str(stone.get("Availability") or ""),
                Shape=str(stone.get("Shape") or ""),
                Weight=_to_float(stone.get("Weight")),
                Color=str(stone.get("Color") or ""),
                Clarity=str(stone.get("Clarity") or ""),
                Cut=str(stone.get("Cut") or ""),
                Polish=str(stone.get("Polish") or ""),
                Symm=str(stone.get("Symm") or ""),
                business_category=str(stone.get("business_category") or ""),
                Lab=str(stone.get("Lab") or ""),
                Fls=str(stone.get("Fls") or ""),
                FinalPrice=_to_float(stone.get("FinalPrice")),
                Location=str(stone.get("Location") or ""),
                Measurements=str(stone.get("Measurements") or ""),
                StockDate=str(stone.get("StockDate") or ""),
                Days=str(stone.get("Days") or ""),
            ))
        except Exception:
            # Skip malformed stone records — don't crash the whole response
            continue

    return StoneLookupResponse(
        total_requested=result.get("total_requested", 0),
        unique_requested=result.get("unique_requested", 0),
        total_found=result.get("total_found", 0),
        total_not_found=result.get("total_not_found", 0),
        total_duplicates=result.get("total_duplicates", 0),
        matched_stones=matched_stones,
        not_found=result.get("not_found", []),
        duplicates=result.get("duplicates", []),
    )
