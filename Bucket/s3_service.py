import boto3
from botocore.config import Config

class S3Service:
    def __init__(self, access_key, secret_key, region):
        s3_config = Config(
            region_name=region,
            signature_version='s3v4',
            s3={'addressing_style': 'virtual'}
        )
        self.client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=s3_config
        )

    def get_actual_region(self, bucket_name):
        try:
            response = self.client.get_bucket_location(Bucket=bucket_name)
            loc = response.get('LocationConstraint')
            return loc if loc and loc != "US" else "us-east-1"
        except Exception:
            return None

    def get_versioning_status(self, bucket_name):
        try:
            response = self.client.get_bucket_versioning(Bucket=bucket_name)
            return response.get('Status', 'Disabled')
        except:
            return "Unknown"

    def set_versioning(self, bucket_name, status):
        self.client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': status}
        )

    def get_file_versions(self, bucket_name, filename):
        try:
            response = self.client.list_object_versions(Bucket=bucket_name, Prefix=filename)
            versions = []
            for v in response.get('Versions', []):
                if v['Key'] == filename:
                    versions.append({
                        'id': v['VersionId'],
                        'last_modified': v['LastModified'].strftime('%Y-%m-%d %H:%M:%S'),
                        'size': round(v['Size'] / 1024, 2),
                        'is_latest': v['IsLatest']
                    })
            return versions
        except Exception:
            return []

    def get_version_url(self, bucket_name, filename, version_id):
        return self.client.generate_presigned_url(
            'get_object', 
            Params={'Bucket': bucket_name, 'Key': filename, 'VersionId': version_id}, 
            ExpiresIn=3600
        )

    def list_files(self, bucket_name, prefix=''):
        try:
            response = self.client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if not obj['Key'].endswith('/'):
                        files.append(obj['Key'])
            return [], files
        except Exception:
            return [], []

    def upload(self, bucket_name, file_obj, filename, content_type):
        self.client.upload_fileobj(
            file_obj, bucket_name, filename, 
            ExtraArgs={"ContentType": content_type}
        )

    def get_url(self, bucket_name, filename):
        return self.client.generate_presigned_url(
            'get_object', Params={'Bucket': bucket_name, 'Key': filename}, ExpiresIn=3600
        )

    def delete(self, bucket_name, filename):
        self.client.delete_object(Bucket=bucket_name, Key=filename)