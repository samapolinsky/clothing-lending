import os
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import uuid

def get_s3_client():
    """
    Create and return an S3 client with the configured credentials.
    """
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

def upload_file_to_s3(file_obj, bucket_name=None, object_name=None):
    """
    Upload a file to an S3 bucket and return the URL and key.
    
    :param file_obj: File-like object to upload
    :param bucket_name: S3 bucket name. If not specified, uses the default from settings.
    :param object_name: S3 object name. If not specified, a UUID is generated.
    :return: Dictionary containing the URL and key of the uploaded file, or None if upload fails
    """
    if bucket_name is None:
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
    # Generate a unique file name if not provided
    if object_name is None:
        # Extract file extension if present
        original_filename = file_obj.name
        ext = os.path.splitext(original_filename)[1] if '.' in original_filename else ''
        object_name = f"items/{uuid.uuid4()}{ext}"
    
    # Get S3 client
    s3_client = get_s3_client()
    
    try:
        # Upload the file with explicit ACL
        extra_args = {
            'ACL': 'public-read',
            'ContentType': file_obj.content_type if hasattr(file_obj, 'content_type') else 'application/octet-stream'
        }
        
        s3_client.upload_fileobj(file_obj, bucket_name, object_name, ExtraArgs=extra_args)
        
        # Generate temporary signed URL (valid for 1 week) since bucket might have public access blocked
        url = generate_presigned_url(object_name, bucket_name, expiration=604800)  # 7 days in seconds
        
        # Also return the standard URL in case bucket permissions get fixed later
        standard_url = f"https://{bucket_name}.s3.amazonaws.com/{object_name}"
        
        return {
            'url': url,
            'standard_url': standard_url,
            'key': object_name
        }
    except ClientError as e:
        print(f"Error uploading file to S3: {e}")
        return None

def generate_presigned_url(object_key, bucket_name=None, expiration=3600):
    """
    Generate a presigned URL to share an S3 object.
    
    :param object_key: Key of the object to share
    :param bucket_name: S3 bucket name. If not specified, uses the default from settings.
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """
    if bucket_name is None:
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    
    # Get S3 client
    s3_client = get_s3_client()
    
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': object_key},
                                                    ExpiresIn=expiration)
        return response
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        return None

def delete_file_from_s3(object_key, bucket_name=None):
    """
    Delete a file from an S3 bucket.
    
    :param object_key: Key of the object to delete
    :param bucket_name: S3 bucket name. If not specified, uses the default from settings.
    :return: True if successful, False otherwise
    """
    if bucket_name is None:
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    
    # Get S3 client
    s3_client = get_s3_client()
    
    try:
        # Delete the object
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as e:
        print(f"Error deleting file from S3: {e}")
        return False 