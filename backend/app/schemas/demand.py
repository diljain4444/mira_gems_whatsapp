"""
schemas/demand.py — Pydantic models for the Find Stone by Demand feature.
"""
from typing import Optional, Union
from pydantic import BaseModel


class DemandSearchRequest(BaseModel):
    customer_message: str


class ExtractedRequirement(BaseModel):
    shape: Optional[str] = ""
    color: Optional[Union[str, list[str]]] = ""
    clarity: Optional[Union[str, list[str]]] = ""
    business_category: Optional[str] = ""
    cut: Optional[str] = ""
    polish: Optional[str] = ""
    symm: Optional[str] = ""
    certification: Optional[str] = ""
    fluorescence: Optional[str] = ""
    carat_min: Optional[float] = None
    carat_max: Optional[float] = None


class DiamondMatch(BaseModel):
    StockId: Optional[str] = ""
    Availability: Optional[str] = ""
    Shape: Optional[str] = ""
    Weight: Optional[float] = None
    Color: Optional[str] = ""
    Clarity: Optional[str] = ""
    Cut: Optional[str] = ""
    Polish: Optional[str] = ""
    Symm: Optional[str] = ""
    business_category: Optional[str] = ""
    Lab: Optional[str] = ""
    Fls: Optional[str] = ""
    FinalPrice: Optional[float] = None
    Location: Optional[str] = ""
    Measurements: Optional[str] = ""


class SimilarDiamondMatch(BaseModel):
    """
    A diamond returned as a 'closest alternative' when no exact match is found.
    Identical fields to DiamondMatch plus two similarity-specific extras:
      - similarity_score : lower = more similar to the demand
      - diff_tags        : human-readable badges explaining what differs
                           e.g. ["Color: E (better)", "Carat: 10.50ct (+5%)"]
    """
    StockId: Optional[str] = ""
    Availability: Optional[str] = ""
    Shape: Optional[str] = ""
    Weight: Optional[float] = None
    Color: Optional[str] = ""
    Clarity: Optional[str] = ""
    Cut: Optional[str] = ""
    Polish: Optional[str] = ""
    Symm: Optional[str] = ""
    business_category: Optional[str] = ""
    Lab: Optional[str] = ""
    Fls: Optional[str] = ""
    FinalPrice: Optional[float] = None
    Location: Optional[str] = ""
    Measurements: Optional[str] = ""
    similarity_score: Optional[float] = None
    diff_tags: list[str] = []


class DemandSearchResponse(BaseModel):
    customer_message: str
    extracted_requirement: ExtractedRequirement
    total_inventory: int
    total_available: int
    total_matched: int
    total_available_not_matched: int
    matched_diamonds: list[DiamondMatch]
    similar_diamonds: list[SimilarDiamondMatch] = []
