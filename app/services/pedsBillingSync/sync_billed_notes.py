import os
import sys
import logging
from typing import Dict, List, Any
from datetime import datetime

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()


PAYROLL_DB = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

PEDS_DB = {
    "host": os.getenv("PEDS_DB_HOST"),
    "port": int(os.getenv("PEDS_DB_PORT", "5432")),
    "dbname": os.getenv("PEDS_DB_NAME", "peds_billing"),
    "user": os.getenv("PEDS_DB_USER"),
    "password": os.getenv("PEDS_DB_PASSWORD"),
}

SYNC_TEST_DATE = os.getenv("SYNC_TEST_DATE")  # YYYY-MM-DD or ALL


def parse_sync_test_date(value):
    if not value:
        return None

    value = value.strip().upper()

    if value == "ALL":
        return "ALL"

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise RuntimeError(f"SYNC_TEST_DATE must be YYYY-MM-DD or ALL. Got: {value}")


def get_conn(cfg: Dict[str, Any]):
    missing = [k for k, v in cfg.items() if v in (None, "", 0)]
    if missing:
        raise RuntimeError(f"Missing DB config values: {missing}")

    return psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
    )


def fetch_candidate_visits(payroll_conn, test_date):
    with payroll_conn.cursor(cursor_factory=RealDictCursor) as cur:
        if test_date == "ALL":
            cur.execute(
                """
                SELECT id, note_id, note_date
                FROM visits
                WHERE billed = false
                  AND primary_insurance ILIKE '%%CHHA'
                  AND note_id IS NOT NULL
                ORDER BY id
                """
            )
        elif test_date:
            cur.execute(
                """
                SELECT id, note_id, note_date
                FROM visits
                WHERE billed = false
                  AND note_id IS NOT NULL
                  AND primary_insurance ILIKE '%%CHHA'
                  AND note_date = %s
                ORDER BY id
                """,
                (test_date,),
            )
        else:
            cur.execute(
                """
                SELECT id, note_id, note_date
                FROM visits
                WHERE billed = false
                  AND primary_insurance ILIKE '%%CHHA'
                  AND note_id IS NOT NULL
                ORDER BY id
                """
            )

        return list(cur.fetchall())


def fetch_peds_matches_for_note_ids(peds_conn, note_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not note_ids:
        return {}

    with peds_conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                v.note_id,
                v.invoice_id,
                v.charge,
                i.invoice_name,
                i.created_at AS billed_date
            FROM visits v
            JOIN invoices i
              ON i.id = v.invoice_id
            WHERE v.note_id = ANY(%s)
              AND v.invoice_id IS NOT NULL
            ORDER BY v.note_id, i.created_at
            """,
            (note_ids,),
        )
        rows = list(cur.fetchall())

    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["note_id"], []).append(row)
    return grouped


def billing_status_exists_for_note(payroll_conn, note_id: int) -> bool:
    with payroll_conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM billing_status
            WHERE billed_note_id = %s
            LIMIT 1
            """,
            (note_id,),
        )
        return cur.fetchone() is not None


def insert_billing_status(
    payroll_conn,
    note_id: int,
    invoice_id: str,
    billed_date,
    amount_paid,
) -> int:
    with payroll_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO billing_status (
                status,
                billed_date,
                paid_date,
                paid_amount,
                hold,
                hold_reason,
                current_note_id,
                billed_note_id,
                invoice_id,
                review_needed,
                review_reason,
                created_at,
                updated_at,
                check_number
            )
            VALUES (
                'billed',
                %s,
                NULL,
                %s,
                false,
                NULL,
                %s,
                %s,
                %s,
                false,
                NULL,
                %s,
                %s,
                NULL
            )
            RETURNING id
            """,
            (
                billed_date,
                amount_paid,
                note_id,
                note_id,
                invoice_id,
                billed_date,
                billed_date,
            ),
        )
        return cur.fetchone()[0]


def link_visit_to_billing_status(payroll_conn, visit_id: int, billing_status_id: int) -> int:
    with payroll_conn.cursor() as cur:
        cur.execute(
            """
            UPDATE visits
            SET billed = true,
                billing_id = %s
            WHERE id = %s
              AND billed = false
            """,
            (billing_status_id, visit_id),
        )
        return cur.rowcount


def run_sync():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    test_date = parse_sync_test_date(SYNC_TEST_DATE)

    stats = {
        "checked": 0,
        "matched": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
    }

    payroll_conn = None
    peds_conn = None

    try:
        payroll_conn = get_conn(PAYROLL_DB)
        peds_conn = get_conn(PEDS_DB)

        payroll_conn.autocommit = False
        peds_conn.autocommit = True

        candidates = fetch_candidate_visits(payroll_conn, test_date=test_date)
        stats["checked"] = len(candidates)

        logging.info("SYNC_TEST_DATE=%s", test_date)
        logging.info("Found %s candidate payroll visits.", len(candidates))

        if not candidates:
            payroll_conn.commit()
            logging.info("Nothing to sync.")
            logging.info("Summary: %s", stats)
            return stats

        note_ids = [row["note_id"] for row in candidates]
        peds_matches = fetch_peds_matches_for_note_ids(peds_conn, note_ids)

        for visit in candidates:
            visit_id = visit["id"]
            note_id = visit["note_id"]
            note_date = visit["note_date"]

            try:
                matches = peds_matches.get(note_id, [])

                if not matches:
                    stats["skipped"] += 1
                    logging.info(
                        "SKIP note_id=%s visit_id=%s note_date=%s | no billed match found in peds_billing",
                        note_id,
                        visit_id,
                        note_date,
                    )
                    continue

                if len(matches) > 1:
                    stats["failed"] += 1
                    logging.warning(
                        "FAIL note_id=%s visit_id=%s note_date=%s | multiple billed matches found in peds_billing",
                        note_id,
                        visit_id,
                        note_date,
                    )
                    continue

                match = matches[0]
                stats["matched"] += 1

                if billing_status_exists_for_note(payroll_conn, note_id):
                    stats["skipped"] += 1
                    logging.info(
                        "SKIP note_id=%s visit_id=%s note_date=%s | billing_status already exists",
                        note_id,
                        visit_id,
                        note_date,
                    )
                    continue

                billing_status_id = insert_billing_status(
                    payroll_conn,
                    note_id=note_id,
                    invoice_id=match["invoice_name"],
                    billed_date=match["billed_date"],
                    amount_paid=match["charge"],
                )

                updated_rows = link_visit_to_billing_status(
                    payroll_conn,
                    visit_id=visit_id,
                    billing_status_id=billing_status_id,
                )

                if updated_rows != 1:
                    stats["failed"] += 1
                    logging.warning(
                        "FAIL note_id=%s visit_id=%s note_date=%s | inserted billing_status_id=%s but expected 1 visit row updated, got %s",
                        note_id,
                        visit_id,
                        note_date,
                        billing_status_id,
                        updated_rows,
                    )
                    raise RuntimeError(
                        f"Inserted billing_status_id={billing_status_id} but could not update visit_id={visit_id}"
                    )

                stats["updated"] += 1
                logging.info(
                    "UPDATED note_id=%s visit_id=%s note_date=%s | billing_status_id=%s source_invoice_id=%s billed_date=%s charge=%s invoice_name=%s",
                    note_id,
                    visit_id,
                    note_date,
                    billing_status_id,
                    match["invoice_id"],
                    match["billed_date"],
                    match["charge"],
                    match["invoice_name"],
                )

            except Exception as row_error:
                stats["failed"] += 1
                logging.exception(
                    "FAIL note_id=%s visit_id=%s note_date=%s | row error: %s",
                    note_id,
                    visit_id,
                    note_date,
                    row_error,
                )
                payroll_conn.rollback()
                payroll_conn.autocommit = False

        payroll_conn.commit()
        logging.info("Sync committed successfully.")
        logging.info("Summary: %s", stats)
        return stats

    except Exception as e:
        if payroll_conn:
            payroll_conn.rollback()
        logging.exception("Sync failed and was rolled back: %s", e)
        raise

    finally:
        if payroll_conn:
            payroll_conn.close()
        if peds_conn:
            peds_conn.close()


if __name__ == "__main__":
    try:
        run_sync()
    except Exception:
        sys.exit(1)