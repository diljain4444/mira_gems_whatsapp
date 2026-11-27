"""
api/report_routes.py

POST /api/reports/generate   — generate Excel, store in memory, return report_id
GET  /api/reports/{id}/download — stream the Excel file for download
GET  /api/reports            — list all in-memory reports (expire after 4 hours)

Reports are stored in a simple in-memory dict.
They are cleared on server restart — no database needed for Phase 1.
The excel_service is completely independent of Chrome so the same
generation logic can be reused by Tauri desktop or a web app.
"""
import io
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.report import GenerateReportRequest, ReportMetadata
from app.services.excel_service import generate_excel_report

router = APIRouter(tags=["Reports"])

# In-memory store: report_id → {excel_bytes, metadata}
_report_store: dict[str, dict] = {}

REPORT_TTL_HOURS = 4


@router.post("/reports/generate")
async def generate_report(request: GenerateReportRequest):
    """
    Generate a professional Excel report from matched diamonds.
    Returns a report_id for subsequent download.
    """
    try:
        excel_bytes = generate_excel_report(
            matched_diamonds=request.matched_diamonds,
            customer_message=request.customer_message,
            extracted_requirement=request.extracted_requirement,
            total_inventory=request.total_inventory,
            total_available=request.total_available,
            total_matched=request.total_matched,
            total_available_not_matched=request.total_available_not_matched,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Excel generation failed: {exc}"
        )

    report_id = str(uuid.uuid4())
    now = datetime.now()
    filename = f"mira_gems_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"

    _report_store[report_id] = {
        "excel_bytes": excel_bytes,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=REPORT_TTL_HOURS)).isoformat(),
        "customer_message": request.customer_message,
        "total_matched": request.total_matched,
        "filename": filename,
    }

    return {
        "report_id": report_id,
        "filename": filename,
        "created_at": now.isoformat(),
        "total_matched": request.total_matched,
    }


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str):
    """
    Stream the Excel file for a given report_id.
    Returns 404 if the report does not exist or has expired.
    """
    report = _report_store.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or expired.")

    # Expire check
    if datetime.now() > datetime.fromisoformat(report["expires_at"]):
        del _report_store[report_id]
        raise HTTPException(status_code=404, detail="Report has expired.")

    return StreamingResponse(
        io.BytesIO(report["excel_bytes"]),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{report["filename"]}"'
        },
    )


@router.get("/reports", response_model=list[ReportMetadata])
async def list_reports():
    """
    Return metadata for all non-expired in-memory reports, newest first.
    Expired reports are pruned from memory on each call.
    """
    now = datetime.now()
    expired = [
        rid for rid, data in _report_store.items()
        if now > datetime.fromisoformat(data["expires_at"])
    ]
    for rid in expired:
        del _report_store[rid]

    reports = [
        ReportMetadata(
            report_id=rid,
            created_at=data["created_at"],
            customer_message=data["customer_message"],
            total_matched=data["total_matched"],
            filename=data["filename"],
        )
        for rid, data in _report_store.items()
    ]
    return sorted(reports, key=lambda r: r.created_at, reverse=True)
