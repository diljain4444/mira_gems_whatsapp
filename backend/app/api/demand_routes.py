"""
api/demand_routes.py — POST /api/demand/search

Extract diamond requirements from a customer message and find matching inventory.
Uses demand_extract.extract_diamond_requirement() + inventory_service.search_by_demand().
"""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

from app.schemas.demand import (
    DemandSearchRequest, DemandSearchResponse,
    ExtractedRequirement, DiamondMatch, SimilarDiamondMatch,
)
from app.services.inventory_service import search_by_demand

# Ensure core/ is on the path so demand_extract can be imported
_core_path = str(Path(__file__).parent.parent / "core")
if _core_path not in sys.path:
    sys.path.insert(0, _core_path)

import demand_extract  # existing file — extract_diamond_requirement()

router = APIRouter(tags=["Demand"])


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        s = str(value).strip()
        return float(s) if s else None
    except (ValueError, TypeError):
        return None


@router.post("/demand/search", response_model=DemandSearchResponse)
async def search_by_demand_endpoint(request: DemandSearchRequest):
    """
    Two-step process:
      1. Extract structured diamond requirements from the customer message
         using the existing demand_extract.extract_diamond_requirement().
      2. Match the extracted requirements against live inventory
         using the existing inventory_fetching logic via inventory_service.

    All Mira Gems business rules (fluorescence/certification correction,
    color/clarity ranges, business category) are preserved from the
    existing Python files — nothing is rewritten here.
    """
    if not request.customer_message or not request.customer_message.strip():
        raise HTTPException(status_code=400, detail="customer_message must not be empty.")

    # ── Step 1: AI extraction ────────────────────────────────────────────────
    try:
        extracted = demand_extract.extract_diamond_requirement(request.customer_message)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI extraction error: {exc}"
        )

    if extracted is None:
        raise HTTPException(
            status_code=502,
            detail="AI extraction returned no result. The Groq API may be unavailable."
        )

    # ── Step 2: Inventory matching ────────────────────────────────────────────
    try:
        match_result = search_by_demand(extracted)
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
            detail=f"Unexpected matching error: {exc}"
        )

    # ── Build response ────────────────────────────────────────────────────────
    matched_diamonds: list[DiamondMatch] = []
    for stone in match_result.get("matched_diamonds", []):
        try:
            matched_diamonds.append(DiamondMatch(
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
            ))
        except Exception:
            continue

    similar_diamonds: list[SimilarDiamondMatch] = []
    for stone in match_result.get("similar_diamonds", []):
        try:
            similar_diamonds.append(SimilarDiamondMatch(
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
                similarity_score=_to_float(stone.get("similarity_score")),
                diff_tags=stone.get("diff_tags") or [],
            ))
        except Exception:
            continue

    req_model = ExtractedRequirement(
        shape=extracted.get("shape") or "",
        color=extracted.get("color") or "",
        clarity=extracted.get("clarity") or "",
        business_category=extracted.get("business_category") or "",
        cut=extracted.get("cut") or "",
        polish=extracted.get("polish") or "",
        symm=extracted.get("symm") or "",
        certification=extracted.get("certification") or "",
        fluorescence=extracted.get("fluorescence") or "",
        carat_min=extracted.get("carat_min"),
        carat_max=extracted.get("carat_max"),
    )

    return DemandSearchResponse(
        customer_message=request.customer_message,
        extracted_requirement=req_model,
        total_inventory=match_result["total_inventory"],
        total_available=match_result["total_available"],
        total_matched=match_result["total_matched"],
        total_available_not_matched=match_result["total_available_not_matched"],
        matched_diamonds=matched_diamonds,
        similar_diamonds=similar_diamonds,
    )
