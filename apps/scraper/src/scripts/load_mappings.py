"""
Bootstrap script to load normalization_mappings.yaml into the PostgreSQL database.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

import yaml
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

# Ensure apps/scraper/src is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from storage.models import EntityMapping
from storage.postgres import DatabaseClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:15432/airfare_index"
)
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'config', 'normalization_mappings.yaml'))


async def main():
    if not os.path.exists(CONFIG_PATH):
        logger.error(f"Config file not found at {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH, 'r') as f:
        data = yaml.safe_load(f)

    mappings = data.get('mappings', [])
    if not mappings:
        logger.info("No mappings found in config.")
        return

    client = DatabaseClient(DATABASE_URL)
    
    try:
        async with client.session() as session:
            for m in mappings:
                # Check if exists
                stmt_check = select(EntityMapping).where(
                    EntityMapping.entity_type == m['entity_type'],
                    EntityMapping.source == m['source'],
                    EntityMapping.raw_value == m['raw_value']
                )
                result = await session.execute(stmt_check)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.canonical_value = m['canonical_value']
                    existing.approval_status = "APPROVED"
                    existing.approved_at = datetime.now(timezone.utc)
                else:
                    new_mapping = EntityMapping(
                        entity_type=m['entity_type'],
                        source=m['source'],
                        raw_value=m['raw_value'],
                        canonical_value=m['canonical_value'],
                        confidence=1.0,
                        approval_status="APPROVED",
                        created_at=datetime.now(timezone.utc),
                        approved_at=datetime.now(timezone.utc),
                        version=1
                    )
                    session.add(new_mapping)
                
            await session.commit()
            logger.info(f"Loaded {len(mappings)} mappings into database.")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
