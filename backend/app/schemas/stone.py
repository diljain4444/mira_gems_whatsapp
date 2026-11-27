"""
schemas/stone.py — Pydantic models for the Find Stone by ID feature.
"""
from typing import Optional
from pydantic import BaseModel


class StoneLookupRequest(BaseModel):
    stone_ids: str  # Raw free-text input — supports newline / comma / semicolon / space


class StoneDetail(BaseModel):
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
    StockDate: Optional[str] = ""
    Days: Optional[str] = ""


class StoneLookupResponse(BaseModel):
    total_requested: int
    unique_requested: int
    total_found: int
    total_not_found: int
    total_duplicates: int
    matched_stones: list[StoneDetail]
    not_found: list[str]
    duplicates: list[str]
