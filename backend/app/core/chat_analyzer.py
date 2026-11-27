"""
chat_analyzer.py — LLM-powered WhatsApp chat analysis for Mira Companion Lead Logger.

Takes a raw WhatsApp transcript and returns a fully structured LeadAnalysis JSON
that maps directly to the database schema.
"""
import os
import json
import re
from datetime import datetime
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage


# ─────────────────────────────────────────────────────────────
# LLM Setup (reuses the same Groq client pattern as demand_extract.py)
# ─────────────────────────────────────────────────────────────

def _get_llm():
    return ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0,
        max_tokens=2048,
        api_key=os.getenv("GROQ_API_KEY", ""),
    )


# ─────────────────────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert diamond trade analyst for Mira Gems, a lab-grown diamond company based in Surat, India.

Your job is to analyze a WhatsApp conversation between a Mira Gems salesperson ("ME") and a customer, and extract structured business intelligence.

IMPORTANT RULES:
1. Focus ONLY on the most recent conversation session in the transcript.
2. The diamond trade uses shorthand: ct/carat, RND=Round, OV=Oval, MQ=Marquise, PR=Pear, EM=Emerald, RAD=Radiant, CU=Cushion, PS=Princess, HT=Heart, AS=Asscher. Colors: D>E>F>G>H>I>J. Clarities: IF>VVS1>VVS2>VS1>VS2>SI1>SI2>I1. 3EX=Triple Excellent, 2EX=Double Excellent.
3. The conversation may be in English, Hindi, or Hinglish. Understand all variants.
4. Extract ALL diamond demands from the chat (a customer may ask for multiple stones).
5. For deal_outcome: use WON if the customer confirmed purchase/memo, LOST if they said no/rejected, PENDING if they said "will confirm later" or "asking client", NEGOTIATING if actively bargaining, INQUIRY_ONLY if just asking rates with no real intent, GHOSTED if no reply.
6. For lost_reason_category — pick the BEST match: PRICE_TOO_HIGH, OUT_OF_STOCK, QUALITY_MISMATCH, PAYMENT_TERMS, COMPETITOR, DELIVERY_DELAY, WINDOW_SHOPPER, NONE.
7. For stone_quotes — extract every Stock ID mentioned (format: letter + digits, e.g. B000346). Determine if each was PITCHED (shown), REJECTED (customer didn't like), PURCHASED (confirmed), or ON_MEMO (taken on approval).
8. customer_type: RETAIL_JEWELLER, BROKER, WHOLESALER, or CONSUMER.
9. price_sensitivity: HIGH (aggressive bargainer), MEDIUM (fair negotiator), LOW (quality-first, rarely bargains).
10. purchase_scale: SINGLE_STONE, PAIRS_LAYOUT (2-5 stones), or BULK_WHOLESALE (5+ stones or regular buyer).
11. If a field cannot be determined from the chat, use null for that field.
12. growth_type: CVD or HPHT — only if mentioned.
13. in_stock_at_time: set true if the salesperson offered a matching stone, false if they said "nahi hai" / "not available" / "not in stock".
14. lab (certification): IGI, WISE, GIA, certi, and certified are ALL treated as the same category -> output "CERTI". For "non certi", "non-certi", "non certified", or "without certificate" -> ALWAYS output "NON-CERTI". Do NOT confuse standalone "non" (fluorescence = non-fluorescence; note it in special_criteria if needed) with "non certi": e.g. "non certi" -> lab="NON-CERTI"; "non certi non" -> lab="NON-CERTI" and non-fluorescence in special_criteria; "non IGI" -> lab="CERTI" and non-fluorescence in special_criteria. Use null only if certification is not mentioned.

Respond ONLY with valid JSON in this exact structure (no extra text, no markdown):
{
  "customer_name": "string or null",
  "deal_outcome": "WON|LOST|NEGOTIATING|PENDING|INQUIRY_ONLY|GHOSTED",
  "lost_reason_category": "PRICE_TOO_HIGH|OUT_OF_STOCK|QUALITY_MISMATCH|PAYMENT_TERMS|COMPETITOR|DELIVERY_DELAY|WINDOW_SHOPPER|NONE",
  "lost_reason_detail": "string or null",
  "competitor_mentioned": "string or null",
  "market_benchmark_price": "string or null",
  "payment_terms_requested": "CASH|COD|30_DAYS_CREDIT|60_DAYS_CREDIT|MEMO|ANGADIA|null",
  "media_requested": "string or null",
  "urgency": "IMMEDIATE|THIS_WEEK|BROWSING",
  "sentiment": "POSITIVE|NEUTRAL|DISAPPOINTED|DEMANDING",
  "customer_type": "RETAIL_JEWELLER|BROKER|WHOLESALER|CONSUMER|null",
  "price_sensitivity": "HIGH|MEDIUM|LOW",
  "purchase_scale": "SINGLE_STONE|PAIRS_LAYOUT|BULK_WHOLESALE",
  "ai_summary": "2-3 sentence plain English summary of the entire conversation",
  "next_action": "string — specific next step for the salesperson, or null",
  "follow_up_date": "YYYY-MM-DD or null",
  "diamond_demands": [
    {
      "shape": "ROUND|OVAL|MARQUISE|PEAR|EMERALD|RADIANT|CUSHION|PRINCESS|HEART|ASSCHER|null",
      "carat_min": number_or_null,
      "carat_max": number_or_null,
      "color": "D|E|F|G|H|I|J or range like E-F or null",
      "clarity": "IF|VVS1|VVS2|VS1|VS2|SI1|SI2 or range or null",
      "cut_grade": "3EX|2EX|EX|VG|null",
      "lab": "CERTI|NON-CERTI|null",
      "growth_type": "CVD|HPHT|null",
      "special_criteria": "string or null",
      "target_price_per_carat": number_or_null,
      "in_stock_at_time": true_or_false_or_null
    }
  ],
  "stone_quotes": [
    {
      "stock_id": "string",
      "quoted_price_per_carat": number_or_null,
      "customer_counter_offer": number_or_null,
      "stone_status": "PITCHED|REJECTED|PURCHASED|ON_MEMO",
      "rejection_note": "string or null"
    }
  ]
}"""


# ─────────────────────────────────────────────────────────────
# Main Analyzer Function
# ─────────────────────────────────────────────────────────────

def analyze_chat(transcript: str, manual_note: Optional[str] = None) -> dict:
    """
    Sends the chat transcript to the LLM and returns structured analysis as a dict.
    Raises ValueError if the LLM returns non-parseable output.
    """
    llm = _get_llm()

    user_content = f"WhatsApp Chat Transcript:\n\n{transcript}"
    if manual_note and manual_note.strip():
        user_content += f"\n\nSalesperson Note (treat as additional context):\n{manual_note.strip()}"

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    response = llm.invoke(messages)
    raw = response.content.strip()

    # Strip markdown code fences if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw: {raw[:300]}")

    return result
