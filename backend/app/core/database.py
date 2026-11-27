"""
database.py — SQLAlchemy database setup and ORM models for Mira Companion Lead Logger.
Supports PostgreSQL via DATABASE_URL in .env, with automatic local SQLite fallback.
"""
import importlib.util
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, Text, ForeignKey, event, text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Backend root directory (mira-companion/backend/)
_DB_DIR = Path(__file__).parent.parent.parent
_DB_PATH = _DB_DIR / "mira_leads.db"

# Load .env before reading DATABASE_URL since this module initializes engine on import.
# override=True ensures backend/.env is used even if another project set DATABASE_URL in the shell.
try:
    from dotenv import load_dotenv
    load_dotenv(_DB_DIR / ".env", override=True)
except ImportError:
    _env_file = _DB_DIR / ".env"
    if _env_file.exists():
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            _s = _line.strip()
            if _s and not _s.startswith("#") and "=" in _s:
                _k, _v = _s.split("=", 1)
                os.environ[_k.strip()] = _v.strip().strip("\"'")


def _resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip().strip("\"'")
    if not url:
        return f"sqlite:///{_DB_PATH}"
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    elif (
        url.startswith("postgresql+psycopg://")
        and importlib.util.find_spec("psycopg") is None
    ):
        url = "postgresql+psycopg2://" + url[len("postgresql+psycopg://"):]
    # Safely percent-encode passwords containing '@' or special characters
    if url.startswith("postgresql") and "://" in url and "@" in url:
        from urllib.parse import quote_plus, unquote
        scheme, rest = url.split("://", 1)
        userinfo, host_db = rest.rsplit("@", 1)
        if ":" in userinfo:
            user, pw = userinfo.split(":", 1)
            url = f"{scheme}://{user}:{quote_plus(unquote(pw))}@{host_db}"
    return url


DATABASE_URL = _resolve_database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Enable WAL mode and foreign key enforcement for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─────────────────────────────────────────────────────────────
# ORM Models
# ─────────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    phone_number       = Column(String, unique=True, nullable=False, index=True)
    customer_name      = Column(String)
    customer_type      = Column(String)        # RETAIL_JEWELLER / BROKER / WHOLESALER / CONSUMER
    price_sensitivity  = Column(String)        # HIGH / MEDIUM / LOW
    purchase_scale     = Column(String)        # SINGLE_STONE / PAIRS_LAYOUT / BULK_WHOLESALE
    total_inquiries    = Column(Integer, default=0)
    total_deals_won    = Column(Integer, default=0)
    first_contact_date = Column(DateTime, default=datetime.now)
    last_active_date   = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    sessions = relationship("ChatSession", back_populates="customer", cascade="all, delete-orphan")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id                      = Column(Integer, primary_key=True, autoincrement=True)
    customer_id             = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    created_at              = Column(DateTime, default=datetime.now)
    updated_at              = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Deal intelligence
    deal_outcome            = Column(String)   # WON / LOST / NEGOTIATING / PENDING / INQUIRY_ONLY / GHOSTED
    lost_reason_category    = Column(String)   # PRICE_TOO_HIGH / OUT_OF_STOCK / QUALITY_MISMATCH / PAYMENT_TERMS / COMPETITOR / DELIVERY_DELAY / WINDOW_SHOPPER / NONE
    lost_reason_detail      = Column(Text)
    competitor_mentioned    = Column(String)
    market_benchmark_price  = Column(String)
    payment_terms_requested = Column(String)   # CASH / COD / 30_DAYS_CREDIT / MEMO / ANGADIA
    media_requested         = Column(String)   # What videos/photos were asked for
    urgency                 = Column(String)   # IMMEDIATE / THIS_WEEK / BROWSING

    # Customer behavioral profile
    sentiment               = Column(String)   # POSITIVE / NEUTRAL / DISAPPOINTED / DEMANDING
    customer_type           = Column(String)
    price_sensitivity       = Column(String)
    purchase_scale          = Column(String)

    # AI output
    ai_summary              = Column(Text)
    next_action             = Column(Text)
    follow_up_date          = Column(String)

    # Manual override note added by salesperson before saving
    manual_note             = Column(Text)

    # Raw chat
    raw_chat_transcript     = Column(Text)
    chat_fingerprint        = Column(String, index=True)
    seller_name             = Column(String, index=True)

    customer = relationship("Customer", back_populates="sessions")
    demands  = relationship("DiamondDemand", back_populates="session", cascade="all, delete-orphan")
    quotes   = relationship("StoneQuote", back_populates="session", cascade="all, delete-orphan")


class DiamondDemand(Base):
    __tablename__ = "diamond_demands"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    session_id            = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    shape                 = Column(String)
    carat_min             = Column(Float)
    carat_max             = Column(Float)
    color                 = Column(String)
    clarity               = Column(String)
    cut_grade             = Column(String)
    lab                   = Column(String)
    growth_type           = Column(String)   # CVD / HPHT
    special_criteria      = Column(Text)     # e.g. "Ratio 1.45+, No BGM, No Brown"
    target_price_per_carat= Column(Float)
    in_stock_at_time      = Column(Boolean)  # Did inventory have this when saved?

    session = relationship("ChatSession", back_populates="demands")


class StoneQuote(Base):
    __tablename__ = "stone_quotes"

    id                     = Column(Integer, primary_key=True, autoincrement=True)
    session_id             = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    stock_id               = Column(String, index=True)
    quoted_price_per_carat = Column(Float)
    customer_counter_offer = Column(Float)
    stone_status           = Column(String)   # PITCHED / REJECTED / PURCHASED / ON_MEMO
    rejection_note         = Column(Text)

    session = relationship("ChatSession", back_populates="quotes")


def init_db():
    """Create all tables if they don't exist. Safe to call multiple times."""
    Base.metadata.create_all(bind=engine)

    migration_columns = [
        ("chat_fingerprint", "VARCHAR"),
        ("seller_name", "VARCHAR"),
        ("updated_at", "TIMESTAMP" if not IS_SQLITE else "DATETIME"),
    ]

    if IS_SQLITE:
        with engine.connect() as conn:
            for col_name, col_type in migration_columns:
                try:
                    conn.execute(text(f"ALTER TABLE chat_sessions ADD COLUMN {col_name} {col_type};"))
                    conn.commit()
                except Exception:
                    pass  # Already exists
    else:
        with engine.begin() as conn:
            for col_name, col_type in migration_columns:
                conn.execute(
                    text(f"ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
                )


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
