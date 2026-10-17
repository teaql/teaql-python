"""Optional S3 adapter. Install teaql[object-storage-s3]; boto3 owns SigV4."""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
import tempfile
from teaql.core.object_storage import (
    ObjectMetadata, ObjectContent, ObjectReadUrl, StorageError, StorageErrorCode, WriteMode,
)


def _translate(error):
    from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError, ParamValidationError
    if isinstance(error, (ConnectTimeoutError, ReadTimeoutError, TimeoutError)):
        return StorageError(StorageErrorCode.TIMEOUT)
    if isinstance(error, ParamValidationError):
        return StorageError(StorageErrorCode.INVALID_INPUT)
    if isinstance(error, ClientError):
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if error.response.get("Error", {}).get("Code") == "NoSuchBucket":
            return StorageError(StorageErrorCode.UNAVAILABLE)
        return StorageError({401: StorageErrorCode.ACCESS_DENIED, 403: StorageErrorCode.ACCESS_DENIED,
            404: StorageErrorCode.NOT_FOUND, 409: StorageErrorCode.CONFLICT, 412: StorageErrorCode.CONFLICT,
            408: StorageErrorCode.TIMEOUT, 504: StorageErrorCode.TIMEOUT, 413: StorageErrorCode.TOO_LARGE,
            501: StorageErrorCode.UNSUPPORTED, 400: StorageErrorCode.INVALID_INPUT,
            422: StorageErrorCode.INVALID_INPUT}.get(status, StorageErrorCode.UNAVAILABLE))
    return StorageError(StorageErrorCode.UNAVAILABLE)


def _sdk_call(work):
    translated = None
    try:
        return work()
    except Exception as error:
        translated = _translate(error)
    # Outside the except block: neither __context__ nor __cause__ retains provider text.
    raise translated


def _metadata(key, response):
    size, etag = response.get("ContentLength"), response.get("ETag")
    if type(size) is not int or size < 0 or not isinstance(etag, str) or not etag.strip():
        raise StorageError(StorageErrorCode.UNAVAILABLE)
    return ObjectMetadata(key, size, response.get("ContentType"), etag,
                          response.get("LastModified"), response.get("Metadata", {}))


class S3ObjectStorage:
    """Shared client installed at trusted startup; never creates buckets."""
    def __init__(self, client, bucket: str):
        if not isinstance(bucket, str) or not bucket.strip():
            raise StorageError(StorageErrorCode.INVALID_INPUT)
        self._client, self._bucket = client, bucket

    @classmethod
    def connect(cls, bucket, *, session=None, endpoint_url=None, region_name="us-east-1", **client_options):
        import boto3
        from botocore.config import Config
        session = session or boto3.Session()
        client_options.setdefault("config", Config(signature_version="s3v4", connect_timeout=10, read_timeout=30,
            s3={"addressing_style": "path"}, retries={"max_attempts": 2, "mode": "standard"}))
        return cls(session.client("s3", endpoint_url=endpoint_url, region_name=region_name, **client_options), bucket)

    def put(self, invocation, key, content, options):
        with tempfile.TemporaryFile(mode="w+b") as staging:
            total, error = 0, None
            try:
                while True:
                    block = content.read(65536)
                    if not isinstance(block, bytes):
                        raise StorageError(StorageErrorCode.INVALID_INPUT)
                    if not block:
                        break
                    total += len(block)
                    if total > options.size:
                        raise StorageError(StorageErrorCode.INVALID_INPUT)
                    staging.write(block)
            except StorageError:
                raise
            except Exception:
                error = StorageError(StorageErrorCode.IO)
            if error:
                raise error
            if total != options.size:
                raise StorageError(StorageErrorCode.INVALID_INPUT)
            staging.seek(0)
            args = dict(Bucket=self._bucket, Key=key.value, Body=staging, ContentLength=total,
                        ContentType=options.content_type, Metadata=dict(options.metadata))
            if options.mode == WriteMode.CREATE_ONLY:
                args["IfNoneMatch"] = "*"
            result = _sdk_call(lambda: self._client.put_object(**args))
            if not isinstance(result.get("ETag"), str) or not result["ETag"].strip():
                raise StorageError(StorageErrorCode.UNAVAILABLE)
            return ObjectMetadata(key, total, options.content_type, result["ETag"], custom_metadata=options.metadata)

    def get(self, invocation, key):
        response = _sdk_call(lambda: self._client.get_object(Bucket=self._bucket, Key=key.value))
        try:
            return ObjectContent(_metadata(key, response), response["Body"])
        except Exception:
            response.get("Body") and response["Body"].close()
            raise

    def head(self, invocation, key):
        missing = False
        try:
            response = _sdk_call(lambda: self._client.head_object(Bucket=self._bucket, Key=key.value))
            return _metadata(key, response)
        except StorageError as error:
            if error.code != StorageErrorCode.NOT_FOUND:
                raise
            missing = True
        if missing:
            bucket_error = None
            try:
                _sdk_call(lambda: self._client.head_bucket(Bucket=self._bucket))
            except StorageError as error:
                bucket_error = StorageError(StorageErrorCode.UNAVAILABLE) if error.code == StorageErrorCode.NOT_FOUND else error
            if bucket_error:
                raise bucket_error
        return None

    def delete(self, invocation, key):
        _sdk_call(lambda: self._client.delete_object(Bucket=self._bucket, Key=key.value))

    def get_read_url(self, invocation, key, options):
        params = dict(Bucket=self._bucket, Key=key.value)
        disposition = options.content_disposition()
        if disposition:
            params["ResponseContentDisposition"] = disposition
        url = _sdk_call(lambda: self._client.generate_presigned_url("get_object", Params=params,
                        ExpiresIn=int(options.lifetime.total_seconds()), HttpMethod="GET"))
        invalid = False
        try:
            query = parse_qs(urlsplit(url).query)
            seconds = int(query["X-Amz-Expires"][0])
            started = datetime.strptime(query["X-Amz-Date"][0], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            invalid = not 0 < seconds <= int(options.lifetime.total_seconds())
        except (KeyError, ValueError, TypeError, IndexError):
            invalid = True
        if invalid:
            raise StorageError(StorageErrorCode.UNAVAILABLE)
        if query.get("X-Amz-SignedHeaders") != ["host"]:
            raise StorageError(StorageErrorCode.UNSUPPORTED)
        return ObjectReadUrl(url, started + timedelta(seconds=seconds))

    def close(self):
        self._client.close()

    def __repr__(self):
        return "S3ObjectStorage[configuration=masked]"
