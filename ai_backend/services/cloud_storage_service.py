import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException, UploadFile
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

class CloudStorageService:
    """Cloud storage service supporting multiple providers"""
    
    def __init__(self):
        self.provider = os.getenv("CLOUD_STORAGE_PROVIDER", "aws").lower()
        self.bucket_name = os.getenv("CLOUD_STORAGE_BUCKET", "classmate-recordings")
        self.region = os.getenv("CLOUD_STORAGE_REGION", "us-east-1")
        
        if self.provider == "aws":
            self._init_aws_s3()
        elif self.provider == "gcp":
            self._init_gcp_storage()
        elif self.provider == "azure":
            self._init_azure_blob()
    
    def _init_aws_s3(self):
        """Initialize AWS S3 client"""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=self.region
            )
            logger.info("AWS S3 client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AWS S3: {e}")
            self.s3_client = None
    
    def _init_gcp_storage(self):
        """Initialize Google Cloud Storage client"""
        try:
            from google.cloud import storage
            self.gcs_client = storage.Client(
                project=os.getenv("GCP_PROJECT_ID"),
                credentials=os.getenv("GCP_CREDENTIALS_PATH")
            )
            self.gcs_bucket = self.gcs_client.bucket(self.bucket_name)
            logger.info("Google Cloud Storage client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GCS: {e}")
            self.gcs_client = None
    
    def _init_azure_blob(self):
        """Initialize Azure Blob Storage client"""
        try:
            from azure.storage.blob import BlobServiceClient
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            self.azure_client = BlobServiceClient.from_connection_string(connection_string)
            self.azure_container = self.azure_client.get_container_client(self.bucket_name)
            logger.info("Azure Blob Storage client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob: {e}")
            self.azure_client = None
    
    async def upload_audio_file(self, file_path: str, session_id: str, user_id: str) -> Dict[str, Any]:
        """Upload audio file to cloud storage"""
        try:
            file_name = f"audio/{user_id}/{session_id}/{Path(file_path).name}"
            
            if self.provider == "aws" and self.s3_client:
                return await self._upload_to_s3(file_path, file_name)
            elif self.provider == "gcp" and self.gcs_client:
                return await self._upload_to_gcs(file_path, file_name)
            elif self.provider == "azure" and self.azure_client:
                return await self._upload_to_azure(file_path, file_name)
            else:
                raise HTTPException(status_code=500, detail="Cloud storage not available")
                
        except Exception as e:
            logger.error(f"Failed to upload audio file: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    async def _upload_to_s3(self, file_path: str, file_name: str) -> Dict[str, Any]:
        """Upload file to AWS S3"""
        try:
            # Generate presigned URL for upload
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_name,
                    'ContentType': 'audio/wav'
                },
                ExpiresIn=3600
            )
            
            # Upload file
            with open(file_path, 'rb') as file:
                self.s3_client.upload_fileobj(file, self.bucket_name, file_name)
            
            # Generate download URL
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_name
                },
                ExpiresIn=3600 * 24 * 7  # 7 days
            )
            
            return {
                "provider": "aws_s3",
                "file_name": file_name,
                "upload_url": presigned_url,
                "download_url": download_url,
                "size": os.path.getsize(file_path),
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")
    
    async def _upload_to_gcs(self, file_path: str, file_name: str) -> Dict[str, Any]:
        """Upload file to Google Cloud Storage"""
        try:
            blob = self.gcs_bucket.blob(file_name)
            blob.upload_from_filename(file_path)
            
            # Generate signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.utcnow() + timedelta(hours=24 * 7),  # 7 days
                method="GET"
            )
            
            return {
                "provider": "gcp_storage",
                "file_name": file_name,
                "download_url": url,
                "size": os.path.getsize(file_path),
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"GCS upload error: {e}")
            raise HTTPException(status_code=500, detail=f"GCS upload failed: {str(e)}")
    
    async def _upload_to_azure(self, file_path: str, file_name: str) -> Dict[str, Any]:
        """Upload file to Azure Blob Storage"""
        try:
            blob_client = self.azure_container.get_blob_client(file_name)
            
            with open(file_path, 'rb') as file:
                blob_client.upload_blob(file, overwrite=True)
            
            # Generate SAS URL for download
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            sas_token = generate_blob_sas(
                account_name=self.azure_client.account_name,
                container_name=self.bucket_name,
                blob_name=file_name,
                account_key=self.azure_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=24 * 7)  # 7 days
            )
            
            download_url = f"{blob_client.url}?{sas_token}"
            
            return {
                "provider": "azure_blob",
                "file_name": file_name,
                "download_url": download_url,
                "size": os.path.getsize(file_path),
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Azure upload error: {e}")
            raise HTTPException(status_code=500, detail=f"Azure upload failed: {str(e)}")
    
    async def upload_transcript(self, transcript_data: Dict[str, Any], session_id: str, user_id: str) -> Dict[str, Any]:
        """Upload transcript data to cloud storage"""
        try:
            file_name = f"transcripts/{user_id}/{session_id}/transcript.json"
            
            # Convert to JSON
            transcript_json = json.dumps(transcript_data, indent=2, default=str)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                temp_file.write(transcript_json)
                temp_file_path = temp_file.name
            
            try:
                if self.provider == "aws" and self.s3_client:
                    result = await self._upload_to_s3(temp_file_path, file_name)
                elif self.provider == "gcp" and self.gcs_client:
                    result = await self._upload_to_gcs(temp_file_path, file_name)
                elif self.provider == "azure" and self.azure_client:
                    result = await self._upload_to_azure(temp_file_path, file_name)
                else:
                    raise HTTPException(status_code=500, detail="Cloud storage not available")
                
                result["type"] = "transcript"
                return result
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"Failed to upload transcript: {e}")
            raise HTTPException(status_code=500, detail=f"Transcript upload failed: {str(e)}")
    
    async def list_user_files(self, user_id: str, file_type: str = "all") -> List[Dict[str, Any]]:
        """List all files for a user"""
        try:
            prefix = f"{file_type}/{user_id}/" if file_type != "all" else f"{user_id}/"
            
            if self.provider == "aws" and self.s3_client:
                return await self._list_s3_files(prefix)
            elif self.provider == "gcp" and self.gcs_client:
                return await self._list_gcs_files(prefix)
            elif self.provider == "azure" and self.azure_client:
                return await self._list_azure_files(prefix)
            else:
                raise HTTPException(status_code=500, detail="Cloud storage not available")
                
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            raise HTTPException(status_code=500, detail=f"File listing failed: {str(e)}")
    
    async def _list_s3_files(self, prefix: str) -> List[Dict[str, Any]]:
        """List files from AWS S3"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "name": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "url": self.s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': self.bucket_name, 'Key': obj['Key']},
                        ExpiresIn=3600
                    )
                })
            
            return files
            
        except ClientError as e:
            logger.error(f"S3 listing error: {e}")
            raise HTTPException(status_code=500, detail=f"S3 listing failed: {str(e)}")
    
    async def _list_gcs_files(self, prefix: str) -> List[Dict[str, Any]]:
        """List files from Google Cloud Storage"""
        try:
            blobs = self.gcs_client.list_blobs(self.bucket_name, prefix=prefix)
            
            files = []
            for blob in blobs:
                files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.updated.isoformat(),
                    "url": blob.generate_signed_url(
                        version="v4",
                        expiration=datetime.utcnow() + timedelta(hours=1),
                        method="GET"
                    )
                })
            
            return files
            
        except Exception as e:
            logger.error(f"GCS listing error: {e}")
            raise HTTPException(status_code=500, detail=f"GCS listing failed: {str(e)}")
    
    async def _list_azure_files(self, prefix: str) -> List[Dict[str, Any]]:
        """List files from Azure Blob Storage"""
        try:
            blobs = self.azure_container.list_blobs(name_starts_with=prefix)
            
            files = []
            for blob in blobs:
                blob_client = self.azure_container.get_blob_client(blob.name)
                
                # Generate SAS URL
                from azure.storage.blob import generate_blob_sas, BlobSasPermissions
                sas_token = generate_blob_sas(
                    account_name=self.azure_client.account_name,
                    container_name=self.bucket_name,
                    blob_name=blob.name,
                    account_key=self.azure_client.credential.account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(hours=1)
                )
                
                files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified.isoformat(),
                    "url": f"{blob_client.url}?{sas_token}"
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Azure listing error: {e}")
            raise HTTPException(status_code=500, detail=f"Azure listing failed: {str(e)}")
    
    async def delete_file(self, file_name: str) -> bool:
        """Delete a file from cloud storage"""
        try:
            if self.provider == "aws" and self.s3_client:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_name)
            elif self.provider == "gcp" and self.gcs_client:
                blob = self.gcs_bucket.blob(file_name)
                blob.delete()
            elif self.provider == "azure" and self.azure_client:
                blob_client = self.azure_container.get_blob_client(file_name)
                blob_client.delete_blob()
            else:
                raise HTTPException(status_code=500, detail="Cloud storage not available")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    async def get_storage_usage(self, user_id: str) -> Dict[str, Any]:
        """Get storage usage statistics for a user"""
        try:
            files = await self.list_user_files(user_id)
            
            total_size = sum(file['size'] for file in files)
            file_count = len(files)
            
            # Categorize by type
            audio_files = [f for f in files if f['name'].startswith('audio/')]
            transcript_files = [f for f in files if f['name'].startswith('transcripts/')]
            
            return {
                "total_size": total_size,
                "total_files": file_count,
                "audio_files": len(audio_files),
                "transcript_files": len(transcript_files),
                "audio_size": sum(f['size'] for f in audio_files),
                "transcript_size": sum(f['size'] for f in transcript_files)
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            raise HTTPException(status_code=500, detail=f"Storage usage failed: {str(e)}")

# Global cloud storage service instance
cloud_storage_service = CloudStorageService()
