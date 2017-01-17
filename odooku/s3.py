import urlparse
import posixpath

import logging
import boto3
import botocore.session
from botocore.client import Config
from botocore.exceptions import ClientError
from werkzeug.local import Local


_logger = logging.getLogger(__name__)


S3_CACHE_TIME = 3600*24*30


class S3Error(Exception):
    pass


class S3NoSuchKey(S3Error):
    pass


class S3Pool(object):

    def __init__(self, bucket, aws_access_key_id=None,
            aws_secret_access_key=None, endpoint_url=None,
            addressing_style=None, signature_version=None,
            custom_domain=None):
        self._local = Local()
        self._bucket = bucket
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._endpoint_url = endpoint_url
        self._addressing_style = addressing_style
        self._signature_version = signature_version
        self._custom_domain = custom_domain

    def check(self):
        # Wont work for fake-s3
        '''
        try:
            _logger.info("S3 (%s) head", self.bucket)
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            _logger.warning("S3 (%s) head", self.bucket, exc_info=True)
            return False
        '''
        return True

    def get_url(self, *parts):
        if self._custom_domain:
            return urlparse.urljoin(self._custom_domain, posixpath.join(*parts))
        return urlparse.urljoin(self.client.meta.endpoint_url, posixpath.join(self.bucket, *parts))

    @property
    def bucket(self):
        return self._bucket

    @property
    def client(self):
        if not hasattr(self._local, 'client'):
            _logger.info("Creating new S3 Client")
            self._local.client = boto3.client(
                's3',
                aws_access_key_id=self._aws_access_key_id,
                aws_secret_access_key=self._aws_secret_access_key,
                endpoint_url=self._endpoint_url,
                config=Config(
                    s3={'addressing_style': self._addressing_style},
                    signature_version=self._signature_version
                )
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
