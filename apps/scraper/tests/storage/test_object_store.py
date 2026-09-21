"""
Tests for ObjectStoreClient.

Mocks the underlying aioboto3 client to verify correct key generation
and interaction without requiring a live S3 backend.
"""

import os
import sys
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from storage.object_store import S3ObjectStoreClient


@pytest.fixture
def s3_client():
    return S3ObjectStoreClient(
        bucket_name="test-bucket",
        endpoint_url="http://localhost:9000",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )


def test_generate_key(s3_client):
    """Spec §32: enforce path convention /raw/{source}/{date}/{run_id}/{filename}"""
    run_id = "123e4567-e89b-12d3-a456-426614174000"
    col_date = date(2026, 9, 21)
    
    key = s3_client._generate_key(
        source="indigo",
        collection_date=col_date,
        run_id=run_id,
        filename="response.json"
    )
    
    assert key == f"raw/indigo/2026-09-21/{run_id}/response.json"


@pytest.mark.asyncio
async def test_upload_raw_evidence(s3_client):
    """Test that upload formats the URI correctly and calls put_object."""
    
    # Mock aioboto3 session and client
    mock_s3_client = AsyncMock()
    mock_client_context = AsyncMock()
    mock_client_context.__aenter__.return_value = mock_s3_client
    
    with patch.object(s3_client.session, 'client', return_value=mock_client_context):
        run_id = "fake-uuid"
        col_date = date(2026, 9, 21)
        
        uri = await s3_client.upload_raw_evidence(
            source="indigo",
            collection_date=col_date,
            collection_run_id=run_id,
            filename="response.json",
            content=b'{"price": 5000}',
        )
        
        expected_key = f"raw/indigo/2026-09-21/{run_id}/response.json"
        assert uri == f"s3://test-bucket/{expected_key}"
        
        mock_s3_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key=expected_key,
            Body=b'{"price": 5000}',
            ContentType="application/json",
        )
