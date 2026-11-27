"""
lead_routes.py — FastAPI routes for the Lead Logger feature.

Endpoints:
  POST /api/leads/save           — Analyze chat + save to DB
  GET  /api/leads/list           — Paginated list of all sessions
  GET  /api/leads/customer/{phone} — Full history for one customer
  GET  /api/leads/stats          — Aggregate analytics
"""
from datetime import datetime
from typing import Optional
from collections import Counter
import hashlib
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db, Customer, ChatSession, DiamondDemand, StoneQuote
from app.core.chat_analyzer import analyze_chat
from app.schemas.lead import (
    SaveLeadRequest, SaveLeadResponse,
    LeadListResponse, LeadSummary,
    LeadStatsResponse, StatsItem,
    DiamondDemandOut, StoneQuoteOut,
)

router = APIRouter(prefix="/leads", tags=["Lead Logger"])


# ─────────────────────────────────────────────────────────────
# Helper: build raw transcript string from messages list
# ─────────────────────────────────────────────────────────────

def _build_transcript(messages) -> str:
    lines = []
    for m in messages:
        sender_label = "ME" if m.sender.lower() == "me" else "CUSTOMER"
        lines.append(f"[{m.date} {m.time}] {sender_label}: {m.text}")
    return "\n".join(lines)


def _compute_fingerprint(transcript: str) -> str:
    return hashlib.sha256(transcript.strip().encode("utf-8")).hexdigest()


def _display_phone(phone: Optional[str]) -> str:
    if not phone or phone.startswith("UNKNOWN_"):
        return ""
    return phone


def _normalize_db_str(value) -> Optional[str]:
    """Coerce list values (e.g. ['D', 'E']) to a comma-separated string for String DB columns."""
    if value is None:
        return None
    if isinstance(value, list):
        items = [str(v).strip() for v in value if v is not None and str(v).strip()]
        return ", ".join(items) if items else None
    return str(value)


_CERTI_LAB_VALUES = {"IGI", "WISE", "GIA", "CERTI", "CERTIFIED"}
_NON_CERTI_LAB_VALUES = {
    "NONE", "NON-CERTI", "NON CERTI", "NON-CERTIFIED", "NON CERTIFIED",
    "WITHOUT CERTIFICATE", "UNCERTIFIED", "NO CERTI", "NO CERTIFICATE",
}


def _normalize_lead_lab(value) -> Optional[str]:
    """Normalize Save Lead certification labels into CERTI, NON-CERTI, or None."""
    raw = _normalize_db_str(value)
    if not raw:
        return None
    upper = re.sub(r"\s+", " ", raw.strip().upper())
    if (
        upper in _NON_CERTI_LAB_VALUES
        or "NON-CERTI" in upper
        or "NON CERTI" in upper
        or "WITHOUT CERT" in upper
    ):
        return "NON-CERTI"
    tokens = [t.strip() for t in re.split(r"[,/&|]+", upper) if t.strip()]
    if tokens and all(t in _CERTI_LAB_VALUES for t in tokens):
        return "CERTI"
    return raw


OPEN_OUTCOMES = {"NEGOTIATING", "PENDING", "INQUIRY_ONLY"}


def _text_overlap_ratio(text_a: str, text_b: str) -> float:
    """
    Computes lexical overlap of significant words between two transcripts.
    Returns a score between 0.0 and 1.0 based on the smaller set,
    making it resilient to truncated/deleted messages or appended follow-ups.
    """
    if not text_a or not text_b:
        return 0.0
    words_a = set(re.findall(r'[a-zA-Z0-9]{3,}', text_a.lower()))
    words_b = set(re.findall(r'[a-zA-Z0-9]{3,}', text_b.lower()))
    if not words_a or not words_b:
        return 0.0
    common = words_a & words_b
    return len(common) / min(len(words_a), len(words_b))


# ─────────────────────────────────────────────────────────────
# POST /api/leads/save
# ─────────────────────────────────────────────────────────────

@router.post("/save", response_model=SaveLeadResponse)
def save_lead(payload: SaveLeadRequest, db: Session = Depends(get_db)):
    """
    Main endpoint: receives chat payload from Chrome extension,
    checks for duplicates, analyzes with LLM, and persists to SQLite.
    """
    if not payload.messages:
        raise HTTPException(status_code=400, detail="No messages provided.")

    # 1. Build transcript & unique fingerprint
    transcript = _build_transcript(payload.messages)
    fingerprint = _compute_fingerprint(transcript)
    now = datetime.now()

    # Normalize phone: if blank, use a name-based key so different contacts
    # with no phone number are NOT collapsed into the same customer row.
    raw_phone = (payload.customer_phone or "").strip()
    if raw_phone:
        phone = raw_phone
        customer = db.query(Customer).filter(Customer.phone_number == phone).first()
    else:
        # Fallback key: "UNKNOWN_<sanitized_name>" — unique per contact name
        fallback_name = (payload.customer_name or "NONAME").strip().upper().replace(" ", "_")
        phone = f"UNKNOWN_{fallback_name}"
        customer = db.query(Customer).filter(
            (Customer.phone_number == phone) |
            (Customer.customer_name == payload.customer_name)
        ).first()

    # 2. Check for Existing Exact Duplicate Session
    existing_session = None
    if customer:
        existing_session = (
            db.query(ChatSession)
            .filter(
                ChatSession.customer_id == customer.id,
                (ChatSession.chat_fingerprint == fingerprint) | (ChatSession.raw_chat_transcript == transcript)
            )
            .order_by(ChatSession.created_at.desc())
            .first()
        )

    # 3. If exact duplicate exists and force_update is False -> RETURN EXISTING RECORD (NO LLM, NO DUPLICATE)
    if existing_session and not payload.force_update:
        formatted_date = existing_session.created_at.strftime("%d-%b-%Y at %H:%M") if existing_session.created_at else "earlier"
        return SaveLeadResponse(
            session_id           = existing_session.id,
            customer_id          = customer.id,
            customer_name        = customer.customer_name,
            customer_phone       = _display_phone(customer.phone_number),
            deal_outcome         = existing_session.deal_outcome,
            lost_reason_category = existing_session.lost_reason_category,
            lost_reason_detail   = existing_session.lost_reason_detail,
            ai_summary           = existing_session.ai_summary,
            next_action          = existing_session.next_action,
            follow_up_date       = existing_session.follow_up_date,
            urgency              = existing_session.urgency,
            sentiment            = existing_session.sentiment,
            price_sensitivity    = existing_session.price_sensitivity,
            diamond_demands      = [
                DiamondDemandOut(
                    shape=d.shape, carat_min=d.carat_min, carat_max=d.carat_max,
                    color=d.color, clarity=d.clarity, cut_grade=d.cut_grade,
                    lab=d.lab, growth_type=d.growth_type,
                    special_criteria=d.special_criteria,
                    target_price_per_carat=d.target_price_per_carat,
                    in_stock_at_time=d.in_stock_at_time,
                ) for d in existing_session.demands
            ],
            stone_quotes         = [
                StoneQuoteOut(
                    stock_id=q.stock_id,
                    quoted_price_per_carat=q.quoted_price_per_carat,
                    customer_counter_offer=q.customer_counter_offer,
                    stone_status=q.stone_status,
                    rejection_note=q.rejection_note,
                ) for q in existing_session.quotes
            ],
            created_at           = existing_session.created_at.isoformat() if existing_session.created_at else now.isoformat(),
            is_duplicate         = True,
            duplicate_message    = f"Already saved on {formatted_date} (Session #{existing_session.id}). Loaded existing record without duplicates.",
            seller_name          = existing_session.seller_name,
        )

    # 4. LLM Analysis (runs when new chat, lifecycle update, or force_update requested)
    try:
        analysis = analyze_chat(transcript, manual_note=payload.manual_note)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM analysis failed: {str(e)}")

    # 5. Smart Lifecycle & Overlap Matching
    seller = payload.seller_name.strip() if payload.seller_name and payload.seller_name.strip() else None
    new_outcome = analysis.get("deal_outcome")
    new_demands = analysis.get("diamond_demands") or []
    new_shapes = set(d.get("shape").upper() for d in new_demands if d.get("shape"))

    target_session = None
    is_fuzzy_duplicate = False
    is_lifecycle_update = False
    lifecycle_msg = None

    if existing_session and payload.force_update:
        target_session = existing_session
    elif customer:
        recent_sessions = (
            db.query(ChatSession)
            .filter(ChatSession.customer_id == customer.id)
            .order_by(ChatSession.created_at.desc())
            .limit(5)
            .all()
        )

        for s in recent_sessions:
            overlap = _text_overlap_ratio(transcript, s.raw_chat_transcript or "")
            s_shapes = set(d.shape.upper() for d in s.demands if d.shape)
            shapes_match = bool(new_shapes and s_shapes and (new_shapes & s_shapes))

            # Case A: Fuzzy duplicate (virtually identical conversation, no outcome or demand change)
            # e.g., user deleted 1 word, edited a typo, or scrolled slightly
            if overlap >= 0.85 and (new_outcome == s.deal_outcome) and (shapes_match or (not new_shapes and not s_shapes)):
                target_session = s
                is_fuzzy_duplicate = True
                break

            # Case B: Smart Lifecycle Update on an OPEN session (e.g. NEGOTIATING or PENDING -> WON / LOST)
            # The previous session was still open, and this chat is discussing the same diamond requirement
            # or has high conversation continuity (overlap >= 0.65)
            if s.deal_outcome in OPEN_OUTCOMES:
                if shapes_match or (overlap >= 0.65):
                    target_session = s
                    is_lifecycle_update = True
                    prev_status = s.deal_outcome
                    lifecycle_msg = f"Updated active deal (Session #{s.id}) from {prev_status} to {new_outcome}."
                    break

    # If fuzzy duplicate detected without force_update, return existing record safely
    if is_fuzzy_duplicate and not payload.force_update:
        formatted_date = target_session.created_at.strftime("%d-%b-%Y at %H:%M") if target_session.created_at else "earlier"
        # Refresh fingerprint to latest so future calls match instantly
        target_session.chat_fingerprint = fingerprint
        target_session.raw_chat_transcript = transcript
        db.commit()
        return SaveLeadResponse(
            session_id           = target_session.id,
            customer_id          = customer.id,
            customer_name        = customer.customer_name,
            customer_phone       = _display_phone(customer.phone_number),
            deal_outcome         = target_session.deal_outcome,
            lost_reason_category = target_session.lost_reason_category,
            lost_reason_detail   = target_session.lost_reason_detail,
            ai_summary           = target_session.ai_summary,
            next_action          = target_session.next_action,
            follow_up_date       = target_session.follow_up_date,
            urgency              = target_session.urgency,
            sentiment            = target_session.sentiment,
            price_sensitivity    = target_session.price_sensitivity,
            diamond_demands      = [
                DiamondDemandOut(
                    shape=d.shape, carat_min=d.carat_min, carat_max=d.carat_max,
                    color=d.color, clarity=d.clarity, cut_grade=d.cut_grade,
                    lab=d.lab, growth_type=d.growth_type,
                    special_criteria=d.special_criteria,
                    target_price_per_carat=d.target_price_per_carat,
                    in_stock_at_time=d.in_stock_at_time,
                ) for d in target_session.demands
            ],
            stone_quotes         = [
                StoneQuoteOut(
                    stock_id=q.stock_id,
                    quoted_price_per_carat=q.quoted_price_per_carat,
                    customer_counter_offer=q.customer_counter_offer,
                    stone_status=q.stone_status,
                    rejection_note=q.rejection_note,
                ) for q in target_session.quotes
            ],
            created_at           = target_session.created_at.isoformat() if target_session.created_at else now.isoformat(),
            is_duplicate         = True,
            duplicate_message    = f"Already saved on {formatted_date} (Session #{target_session.id}). Recognized identical chat without creating duplicates.",
            seller_name          = target_session.seller_name,
        )

    # 6. Apply Update or Create New Session
    if target_session:
        session = target_session
        prev_outcome = session.deal_outcome

        # Remove old child records to replace with fresh ones
        db.query(DiamondDemand).filter(DiamondDemand.session_id == session.id).delete()
        db.query(StoneQuote).filter(StoneQuote.session_id == session.id).delete()

        # Update session fields
        session.deal_outcome            = new_outcome
        session.lost_reason_category    = analysis.get("lost_reason_category")
        session.lost_reason_detail      = analysis.get("lost_reason_detail")
        session.competitor_mentioned    = analysis.get("competitor_mentioned")
        session.market_benchmark_price  = analysis.get("market_benchmark_price")
        session.payment_terms_requested = analysis.get("payment_terms_requested")
        session.media_requested         = analysis.get("media_requested")
        session.urgency                 = analysis.get("urgency")
        session.sentiment               = analysis.get("sentiment")
        session.customer_type           = analysis.get("customer_type")
        session.price_sensitivity       = analysis.get("price_sensitivity")
        session.purchase_scale          = analysis.get("purchase_scale")
        session.ai_summary              = analysis.get("ai_summary")
        session.next_action             = analysis.get("next_action")
        session.follow_up_date          = analysis.get("follow_up_date")
        session.manual_note             = payload.manual_note
        session.raw_chat_transcript     = transcript
        session.chat_fingerprint        = fingerprint
        session.updated_at              = now
        if seller:
            session.seller_name         = seller

        # Customer stats update (do NOT increment total_inquiries since it's the same deal)
        customer.last_active_date = now
        if new_outcome == "WON" and prev_outcome != "WON":
            customer.total_deals_won = (customer.total_deals_won or 0) + 1
        elif prev_outcome == "WON" and new_outcome != "WON":
            customer.total_deals_won = max(0, (customer.total_deals_won or 1) - 1)

        if analysis.get("customer_name") and not customer.customer_name:
            customer.customer_name = analysis.get("customer_name")
        if payload.customer_name:
            customer.customer_name = payload.customer_name
    else:
        # Upsert Customer for a NEW session
        if customer is None:
            customer = Customer(
                phone_number       = phone,
                customer_name      = payload.customer_name or analysis.get("customer_name"),
                customer_type      = analysis.get("customer_type"),
                price_sensitivity  = analysis.get("price_sensitivity"),
                purchase_scale     = analysis.get("purchase_scale"),
                total_inquiries    = 1,
                total_deals_won    = 1 if new_outcome == "WON" else 0,
                first_contact_date = now,
                last_active_date   = now,
            )
            db.add(customer)
            db.flush()  # get customer.id
        else:
            customer.last_active_date = now
            customer.total_inquiries  = (customer.total_inquiries or 0) + 1
            if new_outcome == "WON":
                customer.total_deals_won = (customer.total_deals_won or 0) + 1
            if analysis.get("customer_name") and not customer.customer_name:
                customer.customer_name = analysis.get("customer_name")
            if payload.customer_name:
                customer.customer_name = payload.customer_name
            if analysis.get("customer_type"):
                customer.customer_type = analysis.get("customer_type")
            if analysis.get("price_sensitivity"):
                customer.price_sensitivity = analysis.get("price_sensitivity")
            if analysis.get("purchase_scale"):
                customer.purchase_scale = analysis.get("purchase_scale")

        # Create new ChatSession
        session = ChatSession(
            customer_id             = customer.id,
            created_at              = now,
            updated_at              = now,
            deal_outcome            = new_outcome,
            lost_reason_category    = analysis.get("lost_reason_category"),
            lost_reason_detail      = analysis.get("lost_reason_detail"),
            competitor_mentioned    = analysis.get("competitor_mentioned"),
            market_benchmark_price  = analysis.get("market_benchmark_price"),
            payment_terms_requested = analysis.get("payment_terms_requested"),
            media_requested         = analysis.get("media_requested"),
            urgency                 = analysis.get("urgency"),
            sentiment               = analysis.get("sentiment"),
            customer_type           = analysis.get("customer_type"),
            price_sensitivity       = analysis.get("price_sensitivity"),
            purchase_scale          = analysis.get("purchase_scale"),
            ai_summary              = analysis.get("ai_summary"),
            next_action             = analysis.get("next_action"),
            follow_up_date          = analysis.get("follow_up_date"),
            manual_note             = payload.manual_note,
            raw_chat_transcript     = transcript,
            chat_fingerprint        = fingerprint,
            seller_name             = seller,
        )
        db.add(session)
        db.flush()  # get session.id

    # 6. Save DiamondDemands
    demand_objs = []
    for d in (analysis.get("diamond_demands") or []):
        if not isinstance(d, dict):
            continue
        obj = DiamondDemand(
            session_id             = session.id,
            shape                  = _normalize_db_str(d.get("shape")),
            carat_min              = d.get("carat_min"),
            carat_max              = d.get("carat_max"),
            color                  = _normalize_db_str(d.get("color")),
            clarity                = _normalize_db_str(d.get("clarity")),
            cut_grade              = _normalize_db_str(d.get("cut_grade")),
            lab                    = _normalize_lead_lab(d.get("lab")),
            growth_type            = _normalize_db_str(d.get("growth_type")),
            special_criteria       = _normalize_db_str(d.get("special_criteria")),
            target_price_per_carat = d.get("target_price_per_carat"),
            in_stock_at_time       = d.get("in_stock_at_time"),
        )
        db.add(obj)
        demand_objs.append(obj)

    # 7. Save StoneQuotes
    quote_objs = []
    for q in (analysis.get("stone_quotes") or []):
        obj = StoneQuote(
            session_id              = session.id,
            stock_id                = q.get("stock_id", ""),
            quoted_price_per_carat  = q.get("quoted_price_per_carat"),
            customer_counter_offer  = q.get("customer_counter_offer"),
            stone_status            = q.get("stone_status", "PITCHED"),
            rejection_note          = q.get("rejection_note"),
        )
        db.add(obj)
        quote_objs.append(obj)

    db.commit()

    # 8. Build response
    dup_msg = None
    if existing_session and payload.force_update:
        dup_msg = "Updated existing record with fresh analysis."
    elif is_lifecycle_update:
        dup_msg = lifecycle_msg
    return SaveLeadResponse(
        session_id           = session.id,
        customer_id          = customer.id,
        customer_name        = customer.customer_name,
        customer_phone       = _display_phone(customer.phone_number),
        deal_outcome         = session.deal_outcome,
        lost_reason_category = session.lost_reason_category,
        lost_reason_detail   = session.lost_reason_detail,
        ai_summary           = session.ai_summary,
        next_action          = session.next_action,
        follow_up_date       = session.follow_up_date,
        urgency              = session.urgency,
        sentiment            = session.sentiment,
        price_sensitivity    = session.price_sensitivity,
        diamond_demands      = [
            DiamondDemandOut(
                shape=d.shape, carat_min=d.carat_min, carat_max=d.carat_max,
                color=d.color, clarity=d.clarity, cut_grade=d.cut_grade,
                lab=d.lab, growth_type=d.growth_type,
                special_criteria=d.special_criteria,
                target_price_per_carat=d.target_price_per_carat,
                in_stock_at_time=d.in_stock_at_time,
            ) for d in demand_objs
        ],
        stone_quotes         = [
            StoneQuoteOut(
                stock_id=q.stock_id,
                quoted_price_per_carat=q.quoted_price_per_carat,
                customer_counter_offer=q.customer_counter_offer,
                stone_status=q.stone_status,
                rejection_note=q.rejection_note,
            ) for q in quote_objs
        ],
        created_at           = session.created_at.isoformat() if session.created_at else now.isoformat(),
        is_duplicate         = False,
        duplicate_message    = dup_msg,
        seller_name          = session.seller_name,
    )


# ─────────────────────────────────────────────────────────────
# GET /api/leads/list
# ─────────────────────────────────────────────────────────────

@router.get("/list", response_model=LeadListResponse)
def list_leads(
    skip:  int = Query(0,  ge=0),
    limit: int = Query(50, ge=1, le=200),
    db:    Session = Depends(get_db),
):
    total = db.query(ChatSession).count()
    sessions = (
        db.query(ChatSession)
        .order_by(ChatSession.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    leads = []
    for s in sessions:
        leads.append(LeadSummary(
            session_id           = s.id,
            customer_name        = s.customer.customer_name if s.customer else None,
            customer_phone       = _display_phone(s.customer.phone_number) if s.customer else "",
            seller_name          = s.seller_name,
            deal_outcome         = s.deal_outcome,
            lost_reason_category = s.lost_reason_category,
            ai_summary           = s.ai_summary,
            created_at           = s.created_at.isoformat() if s.created_at else "",
            total_demands        = len(s.demands),
            total_quotes         = len(s.quotes),
        ))
    return LeadListResponse(total=total, leads=leads)


# ─────────────────────────────────────────────────────────────
# GET /api/leads/customer/{phone}
# ─────────────────────────────────────────────────────────────

@router.get("/customer/{phone}")
def customer_history(phone: str, db: Session = Depends(get_db)):
    clean_phone = phone.strip()
    sanitized = f"UNKNOWN_{clean_phone.upper().replace(' ', '_')}"
    customer = db.query(Customer).filter(
        (Customer.phone_number == clean_phone) |
        (Customer.phone_number == sanitized) |
        (Customer.customer_name == clean_phone)
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    sessions_out = []
    for s in sorted(customer.sessions, key=lambda x: x.created_at or datetime.min, reverse=True):
        sessions_out.append({
            "session_id":           s.id,
            "seller_name":          s.seller_name,
            "created_at":           s.created_at.isoformat() if s.created_at else None,
            "deal_outcome":         s.deal_outcome,
            "lost_reason_category": s.lost_reason_category,
            "lost_reason_detail":   s.lost_reason_detail,
            "ai_summary":           s.ai_summary,
            "next_action":          s.next_action,
            "follow_up_date":       s.follow_up_date,
            "sentiment":            s.sentiment,
            "urgency":              s.urgency,
            "diamond_demands":      [
                {
                    "shape": d.shape, "carat_min": d.carat_min, "carat_max": d.carat_max,
                    "color": d.color, "clarity": d.clarity, "cut_grade": d.cut_grade,
                    "lab": d.lab, "in_stock_at_time": d.in_stock_at_time,
                    "target_price_per_carat": d.target_price_per_carat,
                    "special_criteria": d.special_criteria,
                } for d in s.demands
            ],
            "stone_quotes": [
                {
                    "stock_id": q.stock_id, "stone_status": q.stone_status,
                    "quoted_price_per_carat": q.quoted_price_per_carat,
                    "customer_counter_offer": q.customer_counter_offer,
                    "rejection_note": q.rejection_note,
                } for q in s.quotes
            ],
        })

    return {
        "customer": {
            "id":                 customer.id,
            "phone_number":       _display_phone(customer.phone_number),
            "customer_name":      customer.customer_name,
            "customer_type":      customer.customer_type,
            "price_sensitivity":  customer.price_sensitivity,
            "purchase_scale":     customer.purchase_scale,
            "total_inquiries":    customer.total_inquiries,
            "total_deals_won":    customer.total_deals_won,
            "first_contact_date": customer.first_contact_date.isoformat() if customer.first_contact_date else None,
            "last_active_date":   customer.last_active_date.isoformat()   if customer.last_active_date   else None,
        },
        "sessions": sessions_out,
    }


# ─────────────────────────────────────────────────────────────
# GET /api/leads/stats
# ─────────────────────────────────────────────────────────────

@router.get("/stats", response_model=LeadStatsResponse)
def lead_stats(db: Session = Depends(get_db)):
    sessions  = db.query(ChatSession).all()
    customers = db.query(Customer).all()
    demands   = db.query(DiamondDemand).all()

    total_sessions  = len(sessions)
    total_customers = len(customers)
    won     = sum(1 for s in sessions if s.deal_outcome == "WON")
    lost    = sum(1 for s in sessions if s.deal_outcome == "LOST")
    pending = sum(1 for s in sessions if s.deal_outcome in ("PENDING", "NEGOTIATING"))

    conversion_rate = round((won / total_sessions * 100), 1) if total_sessions > 0 else 0.0

    # Top lost reasons
    lost_reasons = Counter(
        s.lost_reason_category for s in sessions
        if s.lost_reason_category and s.lost_reason_category != "NONE"
    )
    top_lost = [StatsItem(label=k, count=v) for k, v in lost_reasons.most_common(5)]

    # Top demanded shapes
    shapes = Counter(d.shape for d in demands if d.shape)
    top_shapes = [StatsItem(label=k, count=v) for k, v in shapes.most_common(5)]

    # Price sensitivity distribution
    sensitivities = Counter(s.price_sensitivity for s in sessions if s.price_sensitivity)
    top_sens = [StatsItem(label=k, count=v) for k, v in sensitivities.most_common(3)]

    return LeadStatsResponse(
        total_sessions         = total_sessions,
        total_customers        = total_customers,
        won                    = won,
        lost                   = lost,
        pending                = pending,
        conversion_rate_pct    = conversion_rate,
        top_lost_reasons       = top_lost,
        top_demanded_shapes    = top_shapes,
        top_price_sensitivities= top_sens,
    )
