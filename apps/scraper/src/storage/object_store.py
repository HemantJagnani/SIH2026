"""
Object Storage interface and implementations.

Provides an abstract interface for object storage to ensure the pipeline
is not tightly coupled to aioboto3 or S3, per user design constraints.
"""

import abc
import logging
import mimetypes
from datetime import date
from typing import Any

import aioboto3

logger = logging.getLogger(__name__)


class ObjectStoreClient(abc.ABC):
    """
    Abstract interface for object storage operations.
    """

    @abc.abstractmethod
    async def upload_raw_evidence(
        self,
        source: str,
        collection_date: date,
        collection_run_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str:
        """
        Upload raw evidence and return the reference URI.
        
        Args:
            source: Source name (e.g., 'indigo')
            collection_date: Date of the collection run
            collection_run_id: UUID string of the run
            filename: Name of the file (e.g., 'search_response.json')
            content: Raw bytes to upload
            content_type: MIME type (e.g., 'application/json')
            
        Returns:
            str: The URI reference (e.g., 's3://bucket/raw/indigo/2026-09-21/uuid/filename')
        """
        pass

    @abc.abstractmethod
    async def download_file(self, uri: str) -> bytes:
        """
        Download a file by its reference URI.
        """
        pass

    @abc.abstractmethod
    async def check_health(self) -> bool:
        """
        Verify connectivity to the object store.
        """
        pass


class S3ObjectStoreClient(ObjectStoreClient):
    """
    S3-compatible implementation using aioboto3.
    """

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region_name: str | None = None,
    ):
        self.bucket_name = bucket_name
        self.session = aioboto3.Session()
        
        # Boto3 client configuration
        self.client_kwargs: dict[str, Any] = {
            "service_name": "s3",
        }
        if endpoint_url:
            self.client_kwargs["endpoint_url"] = endpoint_url
        if aws_access_key_id and aws_secret_access_key:
            self.client_kwargs["aws_access_key_id"] = aws_access_key_id
            self.client_kwargs["aws_secret_access_key"] = aws_secret_access_key
        if region_name:
            self.client_kwargs["region_name"] = region_name

    def _generate_key(self, source: str, collection_date: date, run_id: str, filename: str) -> str:
        """Enforce path convention: /raw/{source}/{date}/{collection_run_id}/{filename}"""
        date_str = collection_date.isoformat()
        return f"raw/{source}/{date_str}/{run_id}/{filename}"

    async def upload_raw_evidence(
        self,
        source: str,
        collection_date: date,
        collection_run_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str:
        key = self._generate_key(source, collection_date, collection_run_id, filename)
        uri = f"s3://{self.bucket_name}/{key}"
        
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or "application/octet-stream"
            
        extra_args = {"ContentType": content_type}
        
        async with self.session.client(**self.client_kwargs) as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                **extra_args,
            )
            logger.debug(f"Uploaded {len(content)} bytes to {uri}")
            
        return uri

    async def download_file(self, uri: str) -> bytes:
        if not uri.startswith(f"s3://{self.bucket_name}/"):
            raise ValueError(f"Invalid URI format or bucket mismatch: {uri}")
            
        key = uri[len(f"s3://{self.bucket_name}/"):]
        
        async with self.session.client(**self.client_kwargs) as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=key)
            body = await response["Body"].read()
            return body

    async def check_health(self) -> bool:
        try:
            async with self.session.client(**self.client_kwargs) as s3:
                await s3.head_bucket(Bucket=self.bucket_name)
                return True
        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            return False
