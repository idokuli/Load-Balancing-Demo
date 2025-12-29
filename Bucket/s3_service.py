import boto3

class S3Service:
    def __init__(self, access_key, secret_key, region):
        self.client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

    def list_files(self, bucket_name):
        response = self.client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            return [obj['Key'] for obj in response['Contents']]
        return []

    def upload(self, bucket_name, file_obj, filename, content_type):
        self.client.upload_fileobj(
            file_obj, 
            bucket_name, 
            filename, 
            ExtraArgs={"ContentType": content_type}
        )

    def get_url(self, bucket_name, filename):
        return self.client.generate_presigned_url(
            'get_object', 
            Params={'Bucket': bucket_name, 'Key': filename}, 
            ExpiresIn=3600
        )

    def delete(self, bucket_name, filename):
        self.client.delete_object(Bucket=bucket_name, Key=filename)