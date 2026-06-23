"""
Vertical AI micro-SaaS endpoints.
LLM-backed services (Indonesian + global market) on top of x402 payment rail.
Uses Xiaomi MiMo (mimo-v2-flash) for inference. JSON-only outputs.
"""
import os
import json
import logging
import re
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx

log = logging.getLogger("x402-ai")

# Per-endpoint rate limit (token bucket) — prevents one endpoint from monopolizing MiMo quota
# Limits: 60/min for cheap endpoints, 30/min for tax, 20/min for invoice, 10/min for legal
from collections import defaultdict
import threading as _threading
_endpoint_buckets = defaultdict(lambda: {"tokens": 0.0, "last": 0.0})
_endpoint_buckets_lock = _threading.Lock()
ENDPOINT_LIMITS = {
    "/api/v1/ai/sentiment": (60, 60),      # 60 req/min
    "/api/v1/ai/invoice-ocr": (20, 60),    # 20 req/min
    "/api/v1/ai/tax-id": (30, 60),         # 30 req/min
    "/api/v1/ai/legal-review": (10, 60),   # 10 req/min
}

def _check_endpoint_rate(path: str) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds). Per-endpoint rate limit."""
    import time
    rate, period = ENDPOINT_LIMITS.get(path, (60, 60))
    now = time.time()
    with _endpoint_buckets_lock:
        b = _endpoint_buckets[path]
        if b["last"] == 0:
            b["tokens"] = rate
            b["last"] = now
        elapsed = now - b["last"]
        b["tokens"] = min(rate, b["tokens"] + elapsed * (rate / period))
        b["last"] = now
        if b["tokens"] < 1:
            retry = int(period / rate) + 1
            return False, retry
        b["tokens"] -= 1
        return True, 0

# Load MiMo key from .env (project-local), with fallback to hermes .env
def _load_mimo_key() -> str:
    candidates = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.expanduser("~/.hermes/.env"),
    ]
    for path in candidates:
        try:
            with open(path) as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    if s.startswith("XIAOMI_API_KEY="):
                        return s.split("=", 1)[1].strip()
        except FileNotFoundError:
            continue
    return os.environ.get("XIAOMI_API_KEY", "")

MIMO_KEY = _load_mimo_key()
MIMO_BASE = os.environ.get("XIAOMI_BASE_URL", "https://api.xiaomimimo.com/v1")
MIMO_MODEL = os.environ.get("MIMO_MODEL", "mimo-v2-flash")

_client = None
def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        if not MIMO_KEY:
            raise RuntimeError("XIAOMI_API_KEY not configured")
        _client = OpenAI(api_key=MIMO_KEY, base_url=MIMO_BASE)
    return _client


def _llm_json(system: str, user: str, max_tokens: int = 800, temperature: float = 0.2, timeout: float = 30.0, max_retries: int = 2) -> dict:
    """Call MiMo with JSON-only instruction; parse response as JSON. Retries on empty/timeout/parse failure."""
    import time
    client = _get_client()
    full_system = system + "\n\nIMPORTANT: Output ONLY valid JSON. No markdown, no prose, no code fences."
    last_err = None
    t0 = 0
    for attempt in range(max_retries + 1):
        try:
            t0 = time.time()
            r = client.chat.completions.create(
                model=MIMO_MODEL,
                messages=[
                    {"role": "system", "content": full_system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
            elapsed = time.time() - t0
            content = (r.choices[0].message.content or "").strip()
            log.info(f"[llm] attempt {attempt+1}/{max_retries+1} ok, elapsed={elapsed:.2f}s, chars={len(content)}")
            if not content:
                last_err = "empty_content"
                if attempt < max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise ValueError("LLM returned empty content after retries")
            # Strip code fences if present
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                m = re.search(r"\{.*\}", content, re.DOTALL)
                if m:
                    return json.loads(m.group(0))
                last_err = f"non_json: {content[:100]}"
                if attempt < max_retries:
                    time.sleep(0.3 * (attempt + 1))
                    continue
                raise ValueError(f"LLM returned non-JSON after retries: {content[:200]}")
        except Exception as e:
            elapsed = time.time() - t0 if 't0' in dir() else 0
            log.warning(f"[llm] attempt {attempt+1}/{max_retries+1} failed: {type(e).__name__}: {e}")
            last_err = str(e)[:200]
            if attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
    raise ValueError(f"LLM call failed after {max_retries+1} attempts: {last_err}")


router = APIRouter(prefix="/api/v1/ai", tags=["ai-micro-saas"])


# ============================================================
# 1. AI LEGAL DOCUMENT REVIEW
# ============================================================
class LegalReviewIn(BaseModel):
    text: str = Field(..., min_length=20, max_length=20000, description="Contract or agreement text to review")
    jurisdiction: Optional[str] = Field(default="general", description="Legal jurisdiction hint (e.g. 'indonesia', 'us', 'eu', 'general')")

class LegalReviewOut(BaseModel):
    risk_level: str
    risk_score: int
    summary: str
    key_terms: list
    red_flags: list
    recommendations: list
    model: str
    input_chars: int


@router.post("/legal-review", response_model=LegalReviewOut)
async def legal_review(payload: LegalReviewIn):
    """AI-powered legal document review. Returns risk analysis, key terms, red flags."""
    allowed, retry = _check_endpoint_rate("/api/v1/ai/legal-review")
    if not allowed:
        raise HTTPException(429, f"Per-endpoint rate limit exceeded. Retry after {retry}s.")
    if not MIMO_KEY:
        raise HTTPException(503, "LLM not configured")
    try:
        sys_p = (
            "You are a legal contract reviewer. Analyze the given contract/agreement and respond ONLY with JSON of this exact shape:\n"
            "{\n"
            '  "risk_level": "low|medium|high",\n'
            '  "risk_score": 0,\n'
            '  "summary": "1-2 sentence plain-language summary of what this contract does",\n'
            '  "key_terms": [{"term": "...", "explanation": "..."}],\n'
            '  "red_flags": [{"issue": "...", "severity": "low|medium|high", "why_it_matters": "..."}],\n'
            '  "recommendations": ["actionable advice 1", "actionable advice 2"]\n'
            "}\n"
            "risk_score is 0-100 (0=safe, 100=very risky). Be specific and practical. Jurisdiction hint: " + payload.jurisdiction
        )
        user_p = f"Review this contract/agreement:\n\n{payload.text}"
        data = _llm_json(sys_p, user_p, max_tokens=1200, temperature=0.2)
        return LegalReviewOut(
            risk_level=data.get("risk_level", "medium"),
            risk_score=int(data.get("risk_score", 50)),
            summary=data.get("summary", ""),
            key_terms=data.get("key_terms", []),
            red_flags=data.get("red_flags", []),
            recommendations=data.get("recommendations", []),
            model=MIMO_MODEL,
            input_chars=len(payload.text),
        )
    except Exception as e:
        log.exception("legal-review failed")
        raise HTTPException(502, f"AI service error: {str(e)[:200]}")


# ============================================================
# 2. AI TAX HELPER (INDONESIA)
# ============================================================
class TaxIDIn(BaseModel):
    annual_income_idr: float = Field(..., ge=0, description="Annual gross income in IDR")
    ptkp_status: str = Field(default="TK/0", description="PTKP status: TK/0, TK/1, TK/2, TK/3, K/0, K/1, K/2, K/3")
    deductions_idr: float = Field(default=0, ge=0, description="Total deductible expenses in IDR (e.g. zakat, profesi)")
    has_npwp: bool = Field(default=True, description="Whether taxpayer has NPWP (affects tariff)")
    income_type: str = Field(default="employee", description="'employee' (PPh 21) or 'freelance' (PPh 21 final-ish) or 'business' (PPh 25)")

class TaxIDOut(BaseModel):
    ptkp_status: str
    ptkp_amount_idr: float
    gross_income_idr: float
    deductions_idr: float
    taxable_income_idr: float
    pph_estimate_idr: float
    pph_estimate_monthly_idr: float
    effective_rate_pct: float
    marginal_rate_pct: float
    breakdown: list
    notes: list
    model: str


# PTKP 2024 (used as best-known reference)
PTKP_TABLE = {
    "TK/0": 54_000_000, "TK/1": 58_500_000, "TK/2": 63_000_000, "TK/3": 67_500_000,
    "K/0":  58_500_000, "K/1":  63_000_000, "K/2": 67_500_000, "K/3": 72_000_000,
}


@router.post("/tax-id", response_model=TaxIDOut)
async def tax_id(payload: TaxIDIn):
    """Indonesian PPh estimator. Computes estimated annual tax using UU HPP PPh 21 progressive brackets (2024 reference)."""
    allowed, retry = _check_endpoint_rate("/api/v1/ai/tax-id")
    if not allowed:
        raise HTTPException(429, f"Per-endpoint rate limit exceeded. Retry after {retry}s.")
    if not MIMO_KEY:
        raise HTTPException(503, "LLM not configured")
    try:
        ptkp = PTKP_TABLE.get(payload.ptkp_status)
        if ptkp is None:
            raise HTTPException(400, f"Invalid ptkp_status. Use one of: {list(PTKP_TABLE.keys())}")

        taxable = max(0, payload.annual_income_idr - ptkp - payload.deductions_idr)

        # PPh 21 progressive brackets per UU HPP (layer cake)
        brackets = [
            (60_000_000,  0.05),
            (190_000_000, 0.15),
            (250_000_000, 0.25),
            (4_500_000_000, 0.30),
            (float("inf"), 0.35),
        ]
        remaining = taxable
        prev_cap = 0
        breakdown = []
        marginal = 0.0
        for cap, rate in brackets:
            layer = max(0, min(remaining, cap - prev_cap))
            if layer <= 0:
                break
            tax = layer * rate
            breakdown.append({
                "bracket_idr": f"{prev_cap+1:,.0f} – {cap:,.0f}" if cap != float('inf') else f">{prev_cap:,.0f}",
                "rate_pct": rate * 100,
                "taxable_in_bracket_idr": round(layer, 0),
                "tax_idr": round(tax, 0),
            })
            marginal = rate
            remaining -= layer
            prev_cap = cap
            if remaining <= 0:
                break

        pph_annual = sum(b["tax_idr"] for b in breakdown)
        # NPWP penalty: +20% if no NPWP (UU HPP)
        if not payload.has_npwp:
            penalty = pph_annual * 0.20
            breakdown.append({
                "bracket_idr": "NPWP penalty (no NPWP, +20%)",
                "rate_pct": 20,
                "taxable_in_bracket_idr": 0,
                "tax_idr": round(penalty, 0),
            })
            pph_annual += penalty

        notes = []
        if payload.income_type == "freelance":
            notes.append("Untuk freelancer, perhitungan final tax bisa berbeda (PPh 21 final 5% atas bruto di Pasal 17C, max 50jt/thn). Ini estimasi progressive sebagai ilustrasi.")
        elif payload.income_type == "business":
            notes.append("Untuk usaha, gunakan PPh 25 (angsuran bulanan) dan laporkan di SPT Tahunan. Tarif efektif final biasanya 0.5% dari omzet (PP 23/2018 untuk omzet ≤ 4.8M).")
        else:
            notes.append("Perhitungan ini mengikuti tarif progresif PPh 21 UU HPP. Hasil estimasi, bukan saran pajak resmi.")
        notes.append("PTKP TK/0 = Rp 54.000.000 per tahun. Tambahan Rp 4.5jt per tanggungan (max 3).")
        notes.append("Deductions yang umum: zakat, biaya pensiun, biaya jabatan 5% (max 500rb/bln = 6jt/thn).")

        effective = (pph_annual / payload.annual_income_idr * 100) if payload.annual_income_idr > 0 else 0

        return TaxIDOut(
            ptkp_status=payload.ptkp_status,
            ptkp_amount_idr=float(ptkp),
            gross_income_idr=payload.annual_income_idr,
            deductions_idr=payload.deductions_idr,
            taxable_income_idr=taxable,
            pph_estimate_idr=round(pph_annual, 0),
            pph_estimate_monthly_idr=round(pph_annual / 12, 0),
            effective_rate_pct=round(effective, 2),
            marginal_rate_pct=marginal * 100,
            breakdown=breakdown,
            notes=notes,
            model="deterministic+UUHPP-2024",
        )
    except HTTPException:
        raise
    except Exception as e:
        log.exception("tax-id failed")
        raise HTTPException(500, f"Tax calc error: {str(e)[:200]}")


# ============================================================
# 3. AI INVOICE PARSER (text-based OCR companion)
# ============================================================
class InvoiceOCRIn(BaseModel):
    text: str = Field(..., min_length=10, max_length=20000, description="Raw invoice/receipt text (paste from phone OCR or email)")

class InvoiceItem(BaseModel):
    description: str
    quantity: Optional[float] = 1
    unit_price: Optional[float] = None
    total: Optional[float] = None

class InvoiceOCROut(BaseModel):
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: str = "IDR"
    items: list
    subtotal: Optional[float] = None
    tax_ppn: Optional[float] = None
    total: Optional[float] = None
    payment_method: Optional[str] = None
    notes: list
    model: str


@router.post("/invoice-ocr", response_model=InvoiceOCROut)
async def invoice_ocr(payload: InvoiceOCRIn):
    """Parse raw invoice/receipt text into structured JSON. Works with any OCR output."""
    allowed, retry = _check_endpoint_rate("/api/v1/ai/invoice-ocr")
    if not allowed:
        raise HTTPException(429, f"Per-endpoint rate limit exceeded. Retry after {retry}s.")
    if not MIMO_KEY:
        raise HTTPException(503, "LLM not configured")
    try:
        sys_p = (
            "You are an invoice/receipt parser. Extract structured data from the given text and respond ONLY with JSON of this exact shape:\n"
            "{\n"
            '  "vendor": "company name or null",\n'
            '  "invoice_number": "INV-XXX or null",\n'
            '  "invoice_date": "YYYY-MM-DD or null",\n'
            '  "due_date": "YYYY-MM-DD or null",\n'
            '  "currency": "IDR|USD|EUR|...",\n'
            '  "items": [{"description":"...","quantity":1,"unit_price":0,"total":0}],\n'
            '  "subtotal": 0,\n'
            '  "tax_ppn": 0,\n'
            '  "total": 0,\n'
            '  "payment_method": "cash|transfer|credit_card|e_wallet|null",\n'
            '  "notes": ["any important observations like missing info, suspicious patterns, conversion notes"]\n'
            "}\n"
            "All monetary values are numbers (not strings). If a field is missing, use null or empty array. Convert formats like 'Rp 1.500.000' to 1500000."
        )
        data = _llm_json(sys_p, payload.text, max_tokens=1000, temperature=0.1)
        return InvoiceOCROut(
            vendor=data.get("vendor"),
            invoice_number=data.get("invoice_number"),
            invoice_date=data.get("invoice_date"),
            due_date=data.get("due_date"),
            currency=data.get("currency", "IDR"),
            items=data.get("items", []),
            subtotal=data.get("subtotal"),
            tax_ppn=data.get("tax_ppn"),
            total=data.get("total"),
            payment_method=data.get("payment_method"),
            notes=data.get("notes", []),
            model=MIMO_MODEL,
        )
    except Exception as e:
        log.exception("invoice-ocr failed")
        raise HTTPException(502, f"AI service error: {str(e)[:200]}")


# ============================================================
# 4. AI TEXT SENTIMENT (multi-language, with intent + entities)
# ============================================================
class SentimentIn(BaseModel):
    text: str = Field(..., min_length=3, max_length=5000, description="Text to analyze")
    language: Optional[str] = Field(default="auto", description="Language hint: 'id', 'en', 'auto'")

class SentimentEntity(BaseModel):
    text: str
    type: str

class SentimentOut(BaseModel):
    score: float
    label: str
    confidence: float
    intent: str
    entities: list
    topics: list
    model: str


@router.post("/sentiment", response_model=SentimentOut)
async def sentiment_text(payload: SentimentIn):
    """Multi-language sentiment analysis. Returns score (-1 to 1), label, intent, entities, topics."""
    allowed, retry = _check_endpoint_rate("/api/v1/ai/sentiment")
    if not allowed:
        raise HTTPException(429, f"Per-endpoint rate limit exceeded. Retry after {retry}s.")
    if not MIMO_KEY:
        raise HTTPException(503, "LLM not configured")
    log.info(f"[sentiment] handler called, text_len={len(payload.text)}, language={payload.language}")
    try:
        sys_p = (
            "You are a sentiment and intent analyzer. Analyze the given text and respond ONLY with JSON of this exact shape:\n"
            "{\n"
            '  "score": 0.0,\n'
            '  "label": "positive|neutral|negative",\n'
            '  "confidence": 0.0,\n'
            '  "intent": "complaint|praise|inquiry|request|purchase_intent|churn_risk|support|spam|other",\n'
            '  "entities": [{"text":"...","type":"person|product|organization|location|brand|service"}],\n'
            '  "topics": ["topic1","topic2"]\n'
            "}\n"
            "score is -1.0 (very negative) to 1.0 (very positive). confidence is 0.0 to 1.0. Language hint: " + payload.language
        )
        data = _llm_json(sys_p, payload.text, max_tokens=500, temperature=0.2)
        score = float(data.get("score", 0))
        score = max(-1.0, min(1.0, score))
        return SentimentOut(
            score=round(score, 3),
            label=data.get("label", "neutral"),
            confidence=round(float(data.get("confidence", 0.5)), 2),
            intent=data.get("intent", "other"),
            entities=data.get("entities", []),
            topics=data.get("topics", []),
            model=MIMO_MODEL,
        )
    except Exception as e:
        log.exception("sentiment failed")
        raise HTTPException(502, f"AI service error: {str(e)[:200]}")
