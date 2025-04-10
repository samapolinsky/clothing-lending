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

def check_aws_credentials():
    """
    Check if AWS credentials are properly configured.
    """
    try:
        # Print AWS settings for debugging
        print(f"AWS_ACCESS_KEY_ID: {'*' * len(settings.AWS_ACCESS_KEY_ID)}")
        print(f"AWS_SECRET_ACCESS_KEY: {'*' * len(settings.AWS_SECRET_ACCESS_KEY)}")
        print(f"AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
        print(f"AWS_S3_REGION_NAME: {settings.AWS_S3_REGION_NAME}")
        
        # Try to create an S3 client
        s3_client = get_s3_client()
        
        # Try to list buckets to verify credentials
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        
        # Check if our bucket exists
        bucket_exists = settings.AWS_STORAGE_BUCKET_NAME in buckets
        
        return {
            'success': True,
            'buckets': buckets,
            'bucket_exists': bucket_exists
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

def upload_file_to_s3(file_obj, bucket_name=None, object_name=None):
    """
    Upload a file to an S3 bucket and return the URL and key.
    """
    # Check AWS credentials first
    creds_check = check_aws_credentials()
    if not creds_check['success']:
        print(f"AWS credentials check failed: {creds_check['error']}")
        return None
        
    if bucket_name is None:
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
    # Generate a unique file name if not provided
    if object_name is None:
        # Extract file extension if present
        original_filename = file_obj.name
        ext = os.path.splitext(original_filename)[1] if '.' in original_filename else ''
        object_name = f"items/{uuid.uuid4()}{ext}"
    
    try:
        # Get S3 client
        s3_client = get_s3_client()
        
        print(f"Uploading to S3: bucket={bucket_name}, key={object_name}")
        
        # Upload the file
        s3_client.upload_fileobj(
            file_obj,
            bucket_name,
            object_name,
            ExtraArgs={
                'ContentType': getattr(file_obj, 'content_type', 'application/octet-stream')
            }
        )
        
        # Generate URL
        url = f"https://{bucket_name}.s3.amazonaws.com/{object_name}"
        
        print(f"Upload successful. URL: {url}")
        
        return {
            'url': url,
            'key': object_name
        }
        
    except Exception as e:
        print(f"Error in upload_file_to_s3: {str(e)}")
        import traceback
        traceback.print_exc()
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
