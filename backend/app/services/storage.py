import os
from app.core.supabase_client import supabase_admin_client
from app.core.logging import logger


class StorageService:
    @staticmethod
    def create_buckets_if_not_exist():
        """
        Idempotent helper to initialize critical storage buckets.
        Usually executed at application startup or via admin console.
        """
        required_buckets = ["movies", "extracted-clips", "soundtracks", "reels"]
        try:
            existing = supabase_admin_client.storage.list_buckets()
            existing_names = [b.name for b in existing]
            
            for bucket in required_buckets:
                if bucket not in existing_names:
                    logger.info(f"Creating missing Supabase Storage bucket: {bucket}")
                    supabase_admin_client.storage.create_bucket(bucket, options={"public": False})
        except Exception as e:
            logger.error(f"Failed to auto-create storage buckets: {str(e)}")

    @staticmethod
    def generate_presigned_upload_url(bucket_name: str, file_path: str, expires_in_seconds: int = 3600) -> str:
        """
        Generates a temporary presigned URL for direct secure file uploading from client browser.
        """
        try:
            # We fetch a presigned upload URL from Supabase
            response = supabase_admin_client.storage.from_(bucket_name).create_signed_upload_url(
                path=file_path
            )
            # Response contains signedURL and token
            return response.get("signedUrl")
        except Exception as e:
            logger.error(f"Error generating presigned upload URL for bucket '{bucket_name}', path '{file_path}': {str(e)}")
            raise

    @staticmethod
    def generate_presigned_download_url(bucket_name: str, file_path: str, expires_in_seconds: int = 3600) -> str:
        """
        Generates a temporary presigned URL for secure downloading/streaming of media assets.
        """
        try:
            response = supabase_admin_client.storage.from_(bucket_name).create_signed_url(
                path=file_path,
                expires_in=expires_in_seconds
            )
            return response.get("signedURL")
        except Exception as e:
            logger.error(f"Error generating presigned download URL for bucket '{bucket_name}', path '{file_path}': {str(e)}")
            raise

    @staticmethod
    def download_file(bucket_name: str, remote_path: str, local_destination_path: str):
        """
        Downloads a media file from a Supabase storage bucket onto local worker scratch disk.
        """
        try:
            logger.info(f"Downloading s3://{bucket_name}/{remote_path} to {local_destination_path}")
            # Ensure the directory exists
            os.makedirs(os.path.dirname(local_destination_path), exist_ok=True)
            
            with open(local_destination_path, "wb") as f:
                res = supabase_admin_client.storage.from_(bucket_name).download(remote_path)
                f.write(res)
            logger.info(f"Download complete for s3://{bucket_name}/{remote_path}")
        except Exception as e:
            logger.error(f"Error downloading file from bucket '{bucket_name}', path '{remote_path}': {str(e)}")
            raise

    @staticmethod
    def upload_file(bucket_name: str, remote_destination_path: str, local_file_path: str, content_type: str = "video/mp4"):
        """
        Uploads a completed media asset from a worker scratch disk up to Supabase storage.
        """
        try:
            logger.info(f"Uploading {local_file_path} to s3://{bucket_name}/{remote_destination_path}")
            if not os.path.exists(local_file_path):
                raise FileNotFoundError(f"Local file not found: {local_file_path}")
                
            with open(local_file_path, "rb") as f:
                supabase_admin_client.storage.from_(bucket_name).upload(
                    path=remote_destination_path,
                    file=f,
                    file_options={"cache-control": "3600", "content-type": content_type, "upsert": "true"}
                )
            logger.info(f"Upload complete for s3://{bucket_name}/{remote_destination_path}")
        except Exception as e:
            logger.error(f"Error uploading file to bucket '{bucket_name}', path '{remote_destination_path}': {str(e)}")
            raise
