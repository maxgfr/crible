"""JP audited enrichment — EDINET (free-key opt-in)."""

from __future__ import annotations

import os
import time

from crible.ingest.enrich._base import _connect, config, log

def run_edinet(days, key: str | None = None, client=None, http=None, limit: int | None = None) -> dict:
    """EDINET (Japan) audited layer — free-key opt-in, OFF without a key. For
    each date, list annual securities reports, keep those whose securities code
    matches a JP listing in the universe, fetch the XBRL and write
    provider='edinet' raw. PDL1.0 → redistributable with attribution."""
    from crible.providers.audited import write_audited_frames
    from crible.providers.edinet import (
        ANNUAL_DOC_TYPES,
        KEY_ENV_VAR,
        EdinetClient,
        frames_from_document_zip,
        sec_code,
    )

    data = config.data_dir()
    outcome: dict = {"enriched": 0, "outage": None, "skipped": None}
    key = key or os.environ.get(KEY_ENV_VAR)
    if client is None and not key:
        outcome["skipped"] = f"EDINET disabled (set {KEY_ENV_VAR} to enable, free-key opt-in)"
        return outcome

    con = _connect()
    try:
        by_seccode: dict[str, str] = {}
        for (symbol,) in con.execute(
            "SELECT symbol FROM companies WHERE country = 'JP' AND NOT delisted"
        ).fetchall():
            code = sec_code(symbol)
            if code:
                by_seccode[code] = symbol
        if not by_seccode:
            outcome["skipped"] = "no JP listings in the universe"
            return outcome

        if client is None:
            client = EdinetClient(key, http=http)
        fetched_at = time.time()
        for day in days:
            try:
                documents = client.list_documents(day)
            except Exception as exc:  # noqa: BLE001 — outage: record, resume next run
                outcome["outage"] = f"{day}: {exc}"
                log.warning("edinet: %s — resuming next run", exc)
                continue
            for doc in documents:
                symbol = by_seccode.get(str(doc.get("secCode") or ""))
                if not symbol:
                    continue
                if str(doc.get("docTypeCode") or "") not in ANNUAL_DOC_TYPES:
                    continue  # only annual securities reports (120), not interim
                try:
                    frames = frames_from_document_zip(client.fetch_document(doc["docID"]))
                except Exception as exc:  # noqa: BLE001
                    outcome["outage"] = f"{doc.get('docID')}: {exc}"
                    log.warning("edinet: outage on %s: %s", doc.get("docID"), exc)
                    continue
                if not frames:
                    continue
                write_audited_frames(
                    data, symbol=symbol, provider_id="edinet", frames=frames, fetched_at=fetched_at,
                )
                outcome["enriched"] += 1
                if limit is not None and outcome["enriched"] >= limit:
                    break
            if limit is not None and outcome["enriched"] >= limit:
                break
        log.info("edinet: enriched %d JP listings", outcome["enriched"])
        return outcome
    finally:
        con.close()

