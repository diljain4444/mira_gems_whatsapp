"""
lead.py — Pydantic schemas for the Lead Logger API.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, Field


# ─── Incoming request from the Chrome extension ───────────────────────────────

class ChatMessage(BaseModel):
    sender: str          # "me" or "customer"
    time:   str          # e.g. "14:32"
    date:   str          # e.g. "24/11/2026"
    text:   str


class SaveLeadRequest(BaseModel):
    customer_phone:  str
    customer_name:   Optional[str] = None
    messages:        List[ChatMessage]
    manual_note:     Optional[str] = None   # Optional extra note from salesperson
    force_update:    Optional[bool] = False # True to force re-analysis & update existing session
    seller_name:     Optional[str] = None   # Name of the salesperson who logged this lead


# ─── Individual sub-objects in the response ───────────────────────────────────

class DiamondDemandOut(BaseModel):
    shape:                  Optional[str]
    carat_min:              Optional[float]
    carat_max:              Optional[float]
    color:                  Optional[Union[str, List[str]]] = None
    clarity:                Optional[Union[str, List[str]]] = None
    cut_grade:              Optional[str]
    lab:                    Optional[str]
    growth_type:            Optional[str]
    special_criteria:       Optional[str]
    target_price_per_carat: Optional[float]
    in_stock_at_time:       Optional[bool]


class StoneQuoteOut(BaseModel):
    stock_id:               str
    quoted_price_per_carat: Optional[float]
    customer_counter_offer: Optional[float]
    stone_status:           str
    rejection_note:         Optional[str]


# ─── Full save response (what the extension shows as the preview) ─────────────

class SaveLeadResponse(BaseModel):
    session_id:             int
    customer_id:            int
    customer_name:          Optional[str]
    customer_phone:         str
    deal_outcome:           Optional[str]
    lost_reason_category:   Optional[str]
    lost_reason_detail:     Optional[str]
    ai_summary:             Optional[str]
    next_action:            Optional[str]
    follow_up_date:         Optional[str]
    urgency:                Optional[str]
    sentiment:              Optional[str]
    price_sensitivity:      Optional[str]
    diamond_demands:        List[DiamondDemandOut]
    stone_quotes:           List[StoneQuoteOut]
    created_at:             str
    is_duplicate:           bool = False
    duplicate_message:      Optional[str] = None
    seller_name:            Optional[str] = None


# ─── List endpoint response ───────────────────────────────────────────────────

class LeadSummary(BaseModel):
    session_id:          int
    customer_name:       Optional[str]
    customer_phone:      str
    seller_name:         Optional[str] = None
    deal_outcome:        Optional[str]
    lost_reason_category:Optional[str]
    ai_summary:          Optional[str]
    created_at:          str
    total_demands:       int
    total_quotes:        int


class LeadListResponse(BaseModel):
    total:   int
    leads:   List[LeadSummary]


# ─── Stats endpoint response ──────────────────────────────────────────────────

class StatsItem(BaseModel):
    label: str
    count: int


class LeadStatsResponse(BaseModel):
    total_sessions:         int
    total_customers:        int
    won:                    int
    lost:                   int
    pending:                int
    conversion_rate_pct:    float
    top_lost_reasons:       List[StatsItem]
    top_demanded_shapes:    List[StatsItem]
    top_price_sensitivities:List[StatsItem]
