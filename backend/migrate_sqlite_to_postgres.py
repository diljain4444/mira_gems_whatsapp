"""
migrate_sqlite_to_postgres.py — One-time migration from local mira_leads.db (SQLite)
to PostgreSQL configured via DATABASE_URL in backend/.env (or --target CLI arg).

Usage:
    cd mira-companion/backend
    python migrate_sqlite_to_postgres.py
    python migrate_sqlite_to_postgres.py --target postgresql://postgres:pass@localhost:5432/mira_leads
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).parent
DEFAULT_SQLITE_PATH = BACKEND_DIR / "mira_leads.db"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

from app.core.database import (
    Base,
    Customer,
    ChatSession,
    DiamondDemand,
    StoneQuote,
)


def _parse_dt(value):
    if value is None or isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _parse_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in {"1", "true", "yes"}:
        return True
    if s in {"0", "false", "no"}:
        return False
    return None


def _normalize_pg_url(url: str) -> str:
    url = url.strip().strip("\"'")
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def _fetch_sqlite_rows(sqlite_conn: sqlite3.Connection, table: str) -> list[dict]:
    cur = sqlite_conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    if cur.fetchone() is None:
        return []
    rows = sqlite_conn.execute(f"SELECT * FROM {table} ORDER BY id ASC").fetchall()
    return [dict(r) for r in rows]


def _migrate_table(pg_session, model, rows: list[dict], transform) -> tuple[int, int]:
    existing_ids = {r[0] for r in pg_session.query(model.id).all()}
    inserted = 0
    skipped = 0
    for row in rows:
        if row["id"] in existing_ids:
            skipped += 1
            continue
        pg_session.add(transform(row))
        inserted += 1
    pg_session.flush()
    return inserted, skipped


def migrate(source_path: Path, target_url: str) -> None:
    if not source_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {source_path}")

    target_url = _normalize_pg_url(target_url)
    if not target_url.startswith("postgresql"):
        raise ValueError(
            "Target DATABASE_URL must be a PostgreSQL URL (e.g. postgresql://user:pass@localhost:5432/mira_leads)."
        )

    pg_engine = create_engine(target_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=pg_engine)
    PgSession = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

    sqlite_conn = sqlite3.connect(str(source_path))
    sqlite_conn.row_factory = sqlite3.Row

    try:
        customers_rows = _fetch_sqlite_rows(sqlite_conn, "customers")
        sessions_rows = _fetch_sqlite_rows(sqlite_conn, "chat_sessions")
        demands_rows = _fetch_sqlite_rows(sqlite_conn, "diamond_demands")
        quotes_rows = _fetch_sqlite_rows(sqlite_conn, "stone_quotes")

        pg = PgSession()
        try:
            c_ins, c_skip = _migrate_table(
                pg, Customer, customers_rows,
                lambda r: Customer(
                    id=r["id"],
                    phone_number=r["phone_number"],
                    customer_name=r.get("customer_name"),
                    customer_type=r.get("customer_type"),
                    price_sensitivity=r.get("price_sensitivity"),
                    purchase_scale=r.get("purchase_scale"),
                    total_inquiries=r.get("total_inquiries") or 0,
                    total_deals_won=r.get("total_deals_won") or 0,
                    first_contact_date=_parse_dt(r.get("first_contact_date")),
                    last_active_date=_parse_dt(r.get("last_active_date")),
                ),
            )

            s_ins, s_skip = _migrate_table(
                pg, ChatSession, sessions_rows,
                lambda r: ChatSession(
                    id=r["id"],
                    customer_id=r["customer_id"],
                    created_at=_parse_dt(r.get("created_at")),
                    updated_at=_parse_dt(r.get("updated_at")),
                    deal_outcome=r.get("deal_outcome"),
                    lost_reason_category=r.get("lost_reason_category"),
                    lost_reason_detail=r.get("lost_reason_detail"),
                    competitor_mentioned=r.get("competitor_mentioned"),
                    market_benchmark_price=r.get("market_benchmark_price"),
                    payment_terms_requested=r.get("payment_terms_requested"),
                    media_requested=r.get("media_requested"),
                    urgency=r.get("urgency"),
                    sentiment=r.get("sentiment"),
                    customer_type=r.get("customer_type"),
                    price_sensitivity=r.get("price_sensitivity"),
                    purchase_scale=r.get("purchase_scale"),
                    ai_summary=r.get("ai_summary"),
                    next_action=r.get("next_action"),
                    follow_up_date=r.get("follow_up_date"),
                    manual_note=r.get("manual_note"),
                    raw_chat_transcript=r.get("raw_chat_transcript"),
                    chat_fingerprint=r.get("chat_fingerprint"),
                    seller_name=r.get("seller_name"),
                ),
            )

            d_ins, d_skip = _migrate_table(
                pg, DiamondDemand, demands_rows,
                lambda r: DiamondDemand(
                    id=r["id"],
                    session_id=r["session_id"],
                    shape=r.get("shape"),
                    carat_min=r.get("carat_min"),
                    carat_max=r.get("carat_max"),
                    color=r.get("color"),
                    clarity=r.get("clarity"),
                    cut_grade=r.get("cut_grade"),
                    lab=r.get("lab"),
                    growth_type=r.get("growth_type"),
                    special_criteria=r.get("special_criteria"),
                    target_price_per_carat=r.get("target_price_per_carat"),
                    in_stock_at_time=_parse_bool(r.get("in_stock_at_time")),
                ),
            )

            q_ins, q_skip = _migrate_table(
                pg, StoneQuote, quotes_rows,
                lambda r: StoneQuote(
                    id=r["id"],
                    session_id=r["session_id"],
                    stock_id=r.get("stock_id"),
                    quoted_price_per_carat=r.get("quoted_price_per_carat"),
                    customer_counter_offer=r.get("customer_counter_offer"),
                    stone_status=r.get("stone_status"),
                    rejection_note=r.get("rejection_note"),
                ),
            )

            pg.commit()

            # Reset PostgreSQL serial sequences so future inserts continue cleanly after MAX(id)
            with pg_engine.begin() as conn:
                for table_name in ("customers", "chat_sessions", "diamond_demands", "stone_quotes"):
                    conn.execute(
                        text(
                            f"SELECT setval("
                            f"pg_get_serial_sequence('{table_name}', 'id'), "
                            f"COALESCE((SELECT MAX(id) FROM {table_name}), 1), "
                            f"(SELECT MAX(id) IS NOT NULL FROM {table_name})"
                            f");"
                        )
                    )

            print("=== Migration Complete ===")
            print(f"customers       : inserted={c_ins}, skipped={c_skip}, total_src={len(customers_rows)}")
            print(f"chat_sessions   : inserted={s_ins}, skipped={s_skip}, total_src={len(sessions_rows)}")
            print(f"diamond_demands : inserted={d_ins}, skipped={d_skip}, total_src={len(demands_rows)}")
            print(f"stone_quotes    : inserted={q_ins}, skipped={q_skip}, total_src={len(quotes_rows)}")
        except Exception:
            pg.rollback()
            raise
        finally:
            pg.close()
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate mira_leads.db SQLite data to PostgreSQL.")
    parser.add_argument("--source", default=str(DEFAULT_SQLITE_PATH), help="Path to mira_leads.db")
    parser.add_argument("--target", default=os.getenv("DATABASE_URL", ""), help="PostgreSQL DATABASE_URL")
    args = parser.parse_args()

    if not args.target:
        print("ERROR: Set DATABASE_URL in backend/.env or pass --target postgresql://...")
        sys.exit(1)

    migrate(Path(args.source), args.target)
