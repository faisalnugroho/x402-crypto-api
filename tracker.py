"""
x402 Request Tracker — SQLite-based logging for monitoring dashboard.
Records every request: endpoint, status, payment info, timing, IP.
"""
import sqlite3
import time
import threading
import os
import json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "tracker.db")
_lock = threading.Lock()


def _get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if not exist."""
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            endpoint TEXT NOT NULL,
            method TEXT DEFAULT 'GET',
            status_code INTEGER,
            paid INTEGER DEFAULT 0,
            payer_address TEXT,
            amount_usdc REAL DEFAULT 0,
            response_ms INTEGER DEFAULT 0,
            ip TEXT,
            user_agent TEXT,
            error TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_requests_ts ON requests(ts);
        CREATE INDEX IF NOT EXISTS idx_requests_endpoint ON requests(endpoint);
        CREATE INDEX IF NOT EXISTS idx_requests_paid ON requests(paid);

        CREATE TABLE IF NOT EXISTS revenue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            endpoint TEXT NOT NULL,
            payer_address TEXT,
            amount_usdc REAL NOT NULL,
            tx_hash TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_revenue_ts ON revenue(ts);
    """)
    conn.close()


def log_request(endpoint: str, status_code: int, paid: bool = False,
                payer_address: str = None, amount_usdc: float = 0,
                response_ms: int = 0, ip: str = None,
                user_agent: str = None, error: str = None):
    """Log a single API request."""
    with _lock:
        conn = _get_db()
        conn.execute("""
            INSERT INTO requests (ts, endpoint, status_code, paid, payer_address,
                                  amount_usdc, response_ms, ip, user_agent, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (time.time(), endpoint, status_code, int(paid),
              payer_address, amount_usdc, response_ms, ip, user_agent, error))
        conn.commit()
        conn.close()


def log_payment(endpoint: str, payer_address: str, amount_usdc: float,
                tx_hash: str = None):
    """Record a successful payment."""
    with _lock:
        conn = _get_db()
        conn.execute("""
            INSERT INTO revenue (ts, endpoint, payer_address, amount_usdc, tx_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (time.time(), endpoint, payer_address, amount_usdc, tx_hash))
        conn.commit()
        conn.close()


def get_stats(hours: int = 24):
    """Get aggregated stats for dashboard."""
    conn = _get_db()
    cutoff = time.time() - (hours * 3600)

    # Total requests in period
    row = conn.execute(
        "SELECT COUNT(*) as total, SUM(paid) as paid_count FROM requests WHERE ts > ?",
        (cutoff,)
    ).fetchone()
    total = row["total"]
    paid_count = row["paid_count"] or 0

    # Revenue in period
    rev = conn.execute(
        "SELECT COALESCE(SUM(amount_usdc), 0) as total_rev FROM revenue WHERE ts > ?",
        (cutoff,)
    ).fetchone()
    revenue = rev["total_rev"]

    # Endpoint breakdown
    endpoints = conn.execute("""
        SELECT endpoint, COUNT(*) as hits, SUM(paid) as paid_hits,
               COALESCE(SUM(amount_usdc), 0) as rev
        FROM requests WHERE ts > ?
        GROUP BY endpoint ORDER BY hits DESC
    """, (cutoff,)).fetchall()

    # Hourly distribution (last 24h)
    hourly = []
    if hours <= 24:
        now_hour = int(time.time()) // 3600
        for i in range(24):
            h = now_hour - 23 + i
            h_start = h * 3600
            h_end = (h + 1) * 3600
            r = conn.execute(
                "SELECT COUNT(*) as c, COALESCE(SUM(paid), 0) as p FROM requests WHERE ts >= ? AND ts < ?",
                (h_start, h_end)
            ).fetchone()
            hourly.append({
                "hour": f"{h % 24:02d}:00",
                "requests": r["c"],
                "paid": int(r["p"]),
            })

    # Daily distribution (last 7d)
    daily = []
    now_day = int(time.time()) // 86400
    for i in range(7):
        d = now_day - 6 + i
        d_start = d * 86400
        d_end = (d + 1) * 86400
        r = conn.execute(
            "SELECT COUNT(*) as c, COALESCE(SUM(paid), 0) as p FROM requests WHERE ts >= ? AND ts < ?",
            (d_start, d_end)
        ).fetchone()
        dt = datetime.utcfromtimestamp(d_start).strftime("%b %d")
        daily.append({
            "day": dt,
            "requests": r["c"],
            "paid": int(r["p"]),
        })

    # Recent requests (last 50)
    recent = conn.execute("""
        SELECT ts, endpoint, status_code, paid, payer_address,
               amount_usdc, response_ms, ip, user_agent, error
        FROM requests ORDER BY ts DESC LIMIT 50
    """).fetchall()

    # Unique IPs
    unique_ips = conn.execute(
        "SELECT COUNT(DISTINCT ip) as c FROM requests WHERE ts > ? AND ip IS NOT NULL",
        (cutoff,)
    ).fetchone()["c"]

    conn.close()

    return {
        "period_hours": hours,
        "total_requests": total,
        "paid_requests": paid_count,
        "free_requests": total - paid_count,
        "conversion_rate": round(paid_count / total * 100, 2) if total > 0 else 0,
        "revenue_usdc": round(revenue, 4),
        "unique_ips": unique_ips,
        "endpoints": [
            {
                "endpoint": e["endpoint"],
                "hits": e["hits"],
                "paid": e["paid_hits"],
                "revenue": round(e["rev"], 4),
            }
            for e in endpoints
        ],
        "hourly": hourly,
        "daily": daily,
        "recent": [
            {
                "time": datetime.utcfromtimestamp(r["ts"]).strftime("%Y-%m-%d %H:%M:%S"),
                "endpoint": r["endpoint"],
                "status": r["status_code"],
                "paid": bool(r["paid"]),
                "payer": r["payer_address"][:10] + "..." if r["payer_address"] else None,
                "amount": r["amount_usdc"],
                "ms": r["response_ms"],
                "ip": r["ip"],
                "ua": (r["user_agent"][:40] + "...") if r["user_agent"] and len(r["user_agent"]) > 40 else r["user_agent"],
                "error": r["error"],
            }
            for r in recent
        ],
    }


# Initialize on import
init_db()
