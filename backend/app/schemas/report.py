"""
schemas/report.py — Pydantic models for Excel report management.
"""
from pydantic import BaseModel


class ReportMetadata(BaseModel):
    report_id: str
    created_at: str
    customer_message: str
    total_matched: int
    filename: str


class GenerateReportRequest(BaseModel):
    customer_message: str
    extracted_requirement: dict
    matched_diamonds: list[dict]
    total_inventory: int
    total_available: int
    total_matched: int
    total_available_not_matched: int
