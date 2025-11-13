import os

from botocore.config import Config
import boto3
from dotenv import load_dotenv


def get_spaces_resource():
    load_dotenv('.env.dev')
    region = os.getenv('DO_SPACES_REGION', 'fra1')
    endpoint = f"https://{region}.digitaloceanspaces.com"
    access_key = os.getenv('DO_SPACES_KEY') or os.getenv('DO_SPACES_ACCESS_KEY_ID')
    secret_key = os.getenv('DO_SPACES_SECRET')

    if not all([access_key, secret_key, os.getenv('DO_SPACES_BUCKET')]):
        raise RuntimeError(
            "Brak konfiguracji DigitalOcean Spaces. Uzupełnij DO_SPACES_* w .env.dev."
        )

    return boto3.resource(
        's3',
        region_name=region,
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4'),
    )


def get_minio_resource():
    endpoint = os.getenv('MINIO_ENDPOINT')
    access_key = os.getenv('MINIO_ACCESS_KEY')
    secret_key = os.getenv('MINIO_SECRET_KEY')
    region = os.getenv('MINIO_REGION', 'us-east-1')

    if not all([endpoint, access_key, secret_key, os.getenv('MINIO_BUCKET_NAME')]):
        raise RuntimeError(
            "Brak konfiguracji MinIO. Uzupełnij MINIO_* w .env.dev."
        )

    return boto3.resource(
        's3',
        region_name=region,
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4'),
    )


def migrate_spaces_to_minio():
    spaces_resource = get_spaces_resource()
    minio_resource = get_minio_resource()

    spaces_bucket_name = os.getenv('DO_SPACES_BUCKET')
    minio_bucket_name = os.getenv('MINIO_BUCKET_NAME', 'nc-media')

    spaces_bucket = spaces_resource.Bucket(spaces_bucket_name)
    minio_bucket = minio_resource.Bucket(minio_bucket_name)

    total = 0
    failed = 0
    for obj in spaces_bucket.objects.all():
        # DigitalOcean Spaces zwraca pseudo-foldery jako klucze zakończone "/"
        if obj.key.endswith('/'):
            print(f"Pominięto katalog {obj.key}")
            continue
        try:
            source_object = spaces_resource.Object(spaces_bucket_name, obj.key)
            response = source_object.get()
            body = response['Body']
            extra_args = {}
            if 'ContentType' in response:
                extra_args['ContentType'] = response['ContentType']
            if 'Metadata' in response and response['Metadata']:
                extra_args['Metadata'] = response['Metadata']
            target_object = minio_bucket.Object(obj.key)
            upload_kwargs = {'ExtraArgs': extra_args} if extra_args else {}
            target_object.upload_fileobj(body, **upload_kwargs)
            print(f"Przeniesiono {obj.key}")
            total += 1
        except Exception as exc:
            print(f"Błąd podczas kopiowania {obj.key}: {exc}")
            failed += 1

    print(
        f"Gotowe. Skopiowano {total} obiektów, błędów: {failed}. "
        f"Źródło: {spaces_bucket_name}, cel: {minio_bucket_name}."
    )


if __name__ == "__main__":
    migrate_spaces_to_minio()

