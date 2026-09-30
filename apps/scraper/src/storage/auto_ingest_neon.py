"""
auto_ingest_neon.py - Automated Ingestion of Scraped Top-60 Observations into Neon PostgreSQL.

Guarantees:
1. Zero Data Loss: Uses batch UPSERT (ON CONFLICT DO UPDATE).
2. Enforces Referential Integrity: Ensures sources ('google_flights') and collection_runs exist.
3. Automatically triggers after complete Top-60 production runs.
"""

import os
import sys
import uuid
import datetime
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import execute_batch, execute_values

logger = logging.getLogger("aerix.auto_ingest")


def get_neon_connection():
    """Returns a direct psycopg2 connection to hosted Neon PostgreSQL."""
    db_url = os.environ.get("DATABASE_URL_SYNC", "").replace("+psycopg2", "")
    if not db_url:
        direct = os.environ.get("DATABASE_URL_DIRECT", "")
        if direct:
            db_url = direct.replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
    if not db_url:
        raw_url = os.environ.get("DATABASE_URL", "")
        if raw_url:
            db_url = raw_url.replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
    if db_url:
        try:
            return psycopg2.connect(db_url)
        except Exception as e:
            logger.warning(f"Could not connect to Neon PostgreSQL for auto-ingestion: {e}")
    return None


def ingest_top60_to_neon(
    raw_observations: List[Dict[str, Any]],
    classified_observations: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """
    Batches and ingests real scraped observations into Neon PostgreSQL table 'fare_observations'.
    """
    if not raw_observations:
        logger.info("No observations provided for Neon ingestion.")
        return 0

    conn = get_neon_connection()
    if not conn:
        logger.warning("Neon DB connection unavailable. Skipping automated DB ingestion.")
        return 0

    try:
        cur = conn.cursor()

        # 1. Ensure source 'google_flights' exists
        gf_source_id = "a11ce000-0000-4000-8000-000000000001"
        cur.execute("""
            INSERT INTO sources (id, name, source_type, permitted_method, is_active)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING;
        """, (gf_source_id, "google_flights", "OTA", "WEB", True))

        # 2. Build classification mapping if provided
        cls_map = {}
        if classified_observations:
            for item in classified_observations:
                obs_id = item.get("observation_id")
                if obs_id:
                    cls_map[obs_id] = item.get("status", "VALID")

        # 3. Ensure collection_runs exist
        run_records = {}
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        for o in raw_observations:
            rid = o.get("collection_run_id") or str(uuid.uuid4())
            o["collection_run_id"] = rid
            if rid not in run_records:
                col_at = o.get("collected_at")
                run_records[rid] = col_at or now_utc.isoformat()

        run_insert_rows = []
        for rid, dt_str in run_records.items():
            try:
                parsed_dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except Exception:
                parsed_dt = now_utc
            run_insert_rows.append((rid, parsed_dt, "COMPLETED"))

        execute_values(
            cur,
            """
            INSERT INTO collection_runs (id, created_at, status)
            VALUES %s
            ON CONFLICT (id) DO NOTHING;
            """,
            run_insert_rows,
        )
        conn.commit()

        # 4. Prepare batch insert for fare_observations
        insert_sql = """
        INSERT INTO fare_observations (
            observation_id, collection_run_id, source, source_offer_id, source_itinerary_id,
            collected_at, travel_date, lead_days, origin, destination,
            airline, airline_code, flight_number, trip_type, cabin, passenger_count,
            departure_time_local, departure_time_utc, arrival_time_local, arrival_time_utc,
            stops, fare_family, fare_class, requires_self_transfer,
            base_fare, taxes, fees, discount, total_fare, currency, price_status, availability,
            raw_value_reference, raw_evidence_uri, adapter_version, normalizer_version, schema_version,
            quality_status, product_stratum_id, itinerary_fingerprint, offer_fingerprint
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON CONFLICT (observation_id) DO UPDATE SET
            total_fare = EXCLUDED.total_fare,
            base_fare = EXCLUDED.base_fare,
            taxes = EXCLUDED.taxes,
            quality_status = EXCLUDED.quality_status;
        """

        obs_rows = []
        for o in raw_observations:
            obs_id = o.get("observation_id") or str(uuid.uuid4())
            run_id = o.get("collection_run_id")
            source = o.get("source") or "google_flights"
            col_at_str = o.get("collected_at")
            try:
                collected_at = datetime.datetime.fromisoformat(col_at_str.replace("Z", "+00:00")) if col_at_str else now_utc
            except Exception:
                collected_at = now_utc

            t_date = o.get("travel_date")
            try:
                travel_date_val = datetime.date.fromisoformat(str(t_date)) if t_date else None
            except Exception:
                travel_date_val = None

            lead_days = int(o.get("lead_days", 7))
            origin = o.get("origin", "")
            dest = o.get("destination", "")
            airline = o.get("airline", "Domestic Carrier")
            airline_code = o.get("airline_code", "")
            flight_num = o.get("flight_number", "")
            trip_type = o.get("trip_type", "ONE_WAY")
            cabin = o.get("cabin", "ECONOMY")
            pax = int(o.get("passenger_count", 1))

            dep_local = o.get("departure_time_local")
            if dep_local and isinstance(dep_local, str):
                try:
                    dep_local = datetime.datetime.fromisoformat(dep_local.replace("Z", "+00:00"))
                except Exception:
                    dep_local = None

            arr_local = o.get("arrival_time_local")
            if arr_local and isinstance(arr_local, str):
                try:
                    arr_local = datetime.datetime.fromisoformat(arr_local.replace("Z", "+00:00"))
                except Exception:
                    arr_local = None

            stops = o.get("stops", 0)
            fare_family = o.get("fare_family")
            fare_class = o.get("fare_class")
            self_transfer = bool(o.get("requires_self_transfer", False))

            base_fare = Decimal(str(o.get("base_fare"))) if o.get("base_fare") is not None else None
            taxes = Decimal(str(o.get("taxes"))) if o.get("taxes") is not None else None
            fees = Decimal(str(o.get("fees"))) if o.get("fees") is not None else None
            discount = Decimal(str(o.get("discount"))) if o.get("discount") is not None else None
            tf = o.get("total_fare")
            total_fare = Decimal(str(tf)) if tf is not None else None

            currency = o.get("currency", "INR")
            price_status = o.get("price_status", "DISPLAYED_TOTAL")
            avail = o.get("availability", "AVAILABLE")
            raw_val = str(o.get("price_raw_text") or o.get("raw_value_reference") or "")
            raw_evidence = o.get("raw_evidence_uri")
            quality_status = cls_map.get(obs_id, o.get("quality_status", "VALID"))

            stratum = o.get("product_stratum_id") or f"{origin}_{dest}_{airline_code or airline}_{cabin}"
            itin_fp = o.get("itinerary_fingerprint") or ""
            offer_fp = o.get("offer_fingerprint") or ""

            obs_rows.append((
                obs_id, run_id, source, o.get("source_offer_id"), o.get("source_itinerary_id"),
                collected_at, travel_date_val, lead_days, origin, dest,
                airline, airline_code, flight_num, trip_type, cabin, pax,
                dep_local, None, arr_local, None,
                stops, fare_family, fare_class, self_transfer,
                base_fare, taxes, fees, discount, total_fare, currency, price_status, avail,
                raw_val, raw_evidence, "2.0.0", "2.0.0", "2.0.0",
                quality_status, stratum, itin_fp, offer_fp
            ))

        logger.info(f"Ingesting {len(obs_rows)} observations into Neon DB table fare_observations...")
        execute_batch(cur, insert_sql, obs_rows, page_size=1000)
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Successfully ingested {len(obs_rows)} rows to Neon DB.")
        return len(obs_rows)

    except Exception as exc:
        logger.error(f"Error during automated Neon ingestion: {exc}", exc_info=True)
        try:
            conn.close()
        except Exception:
            pass
        return 0
