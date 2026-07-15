"""FR-002 — the persisted crawl queue (operational state, DuckDB).

Priority tiers come from the universe (region×8 + cap rank: europe before us
before world, larger caps first within a region); revisit is
freshness-driven (quarterly for fundamentals). The queue lives in the same
DuckDB database as the operational state so a crawler restart resumes exactly
where the previous process stopped.
"""

from __future__ import annotations

import duckdb

QUARTER_SECONDS = 90 * 24 * 3600
PARK_AFTER_FAILURES = 8

SCHEMA = """
CREATE TABLE IF NOT EXISTS crawl_tasks (
    symbol               VARCHAR PRIMARY KEY,
    priority             TINYINT NOT NULL,
    next_due             DOUBLE NOT NULL DEFAULT 0,
    last_crawled_at      DOUBLE,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    status               VARCHAR NOT NULL DEFAULT 'pending'
)
"""


class CrawlQueue:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.con = con
        con.execute(SCHEMA)
        self.seed_from_universe()

    def seed_from_universe(self) -> int:
        """Insert queue entries for universe symbols not yet tracked, and sync
        priorities when the universe's scheme changed (e.g. cap-class tiers) —
        preserving the −1 the bootstrap sample gets from prioritize_sample."""
        has_companies = self.con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = 'companies'"
        ).fetchone()[0]
        if not has_companies:
            return 0
        before = self.con.execute("SELECT count(*) FROM crawl_tasks").fetchone()[0]
        self.con.execute(
            """
            INSERT INTO crawl_tasks (symbol, priority)
            SELECT c.symbol, c.crawl_priority
            FROM companies c
            LEFT JOIN crawl_tasks t ON t.symbol = c.symbol
            WHERE t.symbol IS NULL
            """
        )
        self.con.execute(
            """
            UPDATE crawl_tasks
            SET priority = c.crawl_priority
            FROM companies c
            WHERE crawl_tasks.symbol = c.symbol
              AND crawl_tasks.priority <> c.crawl_priority
              AND crawl_tasks.priority <> -1
            """
        )
        after = self.con.execute("SELECT count(*) FROM crawl_tasks").fetchone()[0]
        return after - before

    def next_batch(self, now: float, limit: int) -> list[str]:
        rows = self.con.execute(
            """
            SELECT symbol FROM crawl_tasks
            WHERE next_due <= ? AND status <> 'parked'
            ORDER BY priority ASC, next_due ASC, symbol ASC
            LIMIT ?
            """,
            [now, limit],
        ).fetchall()
        return [r[0] for r in rows]

    def mark_done(self, symbol: str, now: float, freshness_seconds: float = QUARTER_SECONDS) -> None:
        self.con.execute(
            """
            UPDATE crawl_tasks
            SET last_crawled_at = ?, next_due = ?, consecutive_failures = 0, status = 'pending'
            WHERE symbol = ?
            """,
            [now, now + freshness_seconds, symbol],
        )

    def mark_failed(self, symbol: str, now: float, retry_in_seconds: float = 3600.0) -> None:
        self.con.execute(
            """
            UPDATE crawl_tasks
            SET consecutive_failures = consecutive_failures + 1,
                next_due = ?,
                status = CASE WHEN consecutive_failures + 1 >= ? THEN 'parked' ELSE 'pending' END
            WHERE symbol = ?
            """,
            [now + retry_in_seconds, PARK_AFTER_FAILURES, symbol],
        )
