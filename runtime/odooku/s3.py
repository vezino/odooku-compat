import os
import logging
import boto3
import botocore.session
from botocore.client import Config
from botocore.exceptions import ClientError
from werkzeug.local import Local


_logger = logging.getLogger(__name__)


class S3Error(Exception):
    pass


class S3NoSuchKey(S3Error):
    pass


class S3Pool(object):

    def __init__(self, bucket, aws_access_key_id=None,
            aws_secret_access_key=None, dev_url=None):
        self._local = Local()
        self._bucket = bucket
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._dev_url = dev_url

    def check(self):
        if not self._dev_url:
            try:
                _logger.info("S3 (%s) head", self.bucket)
                self.client.head_bucket(Bucket=self.bucket)
            except ClientError as e:
                _logger.warning("S3 (%s) head", self.bucket, exc_info=True)
                return False

        return True

    @property
    def bucket(self):
        return self._bucket

    @property
    def client(self):
        if not hasattr(self._local, 'client'):
            _logger.info("Creating new S3 Client")
            if self._dev_url:
                _logger.warning("S3 dev mode enabled")
                session = botocore.session.get_session()
                self._local.client = session.create_client(
                    's3',
                    aws_access_key_id='-',
                    aws_secret_access_key='-',
                    endpoint_url=self._dev_url,
                    config=Config(
                        s3={'addressing_style': 'path'},
                        signature_version='s3'
                    )
                )
            else:
                self._local.client = boto3.client(
                    's3',
                    aws_access_key_id=self._aws_access_key_id,
                    aws_secret_access_key=self._aws_secret_access_key
                )

        return self._local.client


pool = None

def configure(bucket=None, **options):

    global pool
    if bucket:
        _pool = S3Pool(
            bucket,
            **options
        )

        if _pool.check():
            pool = _pool

    if pool:
        _logger.info("S3 enabled")
    else:
        _logger.warning("S3 disabled")
