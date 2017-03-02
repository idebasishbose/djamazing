import datetime
import mimetypes

import boto3
from botocore.signers import CloudFrontSigner
from botocore.client import Config
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding

from django.conf import settings
from django.core.files.storage import Storage
from django.core.signing import Signer, BadSignature
from threadlocals.threadlocals import get_current_user 


SIGNER = Signer()

def get_signature(filename, username):
    signature = SIGNER.sign(':'.join([filename, username]))
    return signature.rsplit(':', 1)[1]

def check_signature(signature, filename, username):
    try:
        SIGNER.unsign(':'.join([filename, username, signature]))
    except BadSignature:
        return False
    return True



class DjamazingStorage(Storage):

    def __init__(self):
        self.cloud_front_key = serialization.load_pem_private_key(
            settings.DJAMAZING['CLOUDFRONT_KEY'],
            password=None,
            backend=default_backend(),
        )
        self.key_id = settings.DJAMAZING['CLOUDFRONT_KEY_ID']
        self.view_base_url = '/djamazing'
        self.cloud_front_base_url = settings.DJAMAZING['CLOUDFRONT_URL']
        self.bucket = boto3.resource(
            's3',
            aws_access_key_id = settings.DJAMAZING['S3_KEY_ID'],
            aws_secret_access_key = settings.DJAMAZING['S3_SECRET_KEY'],
            config=Config(signature_version='s3v4')
        ).Bucket(settings.DJAMAZING['S3_BUCKET'])
        self.signer = CloudFrontSigner(self.key_id, self.rsa_signer)

    def url(self, filename):
        user = get_current_user().get_username()
        signature = get_signature(filename, user)
        url = '{}/{}/?signature={}'.format(
            self.view_base_url,
            filename,
            signature,
        )
        return url

    def delete(self, filename):
        self.bucket.delete_objects(Delete={'Objects':[{'Key': filename}]})

    def exists(self, filename):
        try:
            self.bucket.Object(filename).get()
        except ClientError:
            return False
        return True

    def _open(self, filename, mode='rb'):
        if mode != 'rb':
            raise ValueError('Unsupported mode')
        object_ = self.bucket.Object(filename)
        return object_.get()['Body']

    def _save(self, filename, content):
        mime, _ = mimetypes.guess_type(filename)
        self.bucket.put_object(
            ACL='private',
            Body=content,
            Key=filename,
            ContentType=mime,
        )
        return filename


    def rsa_signer(self, data):
        signer = self.cloud_front_key.signer(padding.PKCS1v15(), hashes.SHA1())
        signer.update(data)
        return signer.finalize()

    def cloud_front_url(self, filename):
        expiration_time = (
            datetime.datetime.now() +
            datetime.timedelta(seconds=1)
        )
        url = self.cloud_front_base_url + filename
        return self.signer.generate_presigned_url(
            url,
            date_less_than=expiration_time,
        )