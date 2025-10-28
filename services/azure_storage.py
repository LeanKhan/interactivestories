"""
Azure Blob Storage Service

Handles all file operations with Azure Blob Storage
"""

import os
from azure.storage.blob import BlobClient, ContainerClient, ContentSettings, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename


class AzureBlobStorage:
    """Service class for Azure Blob Storage operations"""

    def __init__(self, connection_string, container_name):
        """
        Initialize Azure Blob Storage client

        Args:
            connection_string: Azure Storage connection string
            container_name: Name of the blob container
        """
        self.connection_string = connection_string
        self.container_name = container_name
        self.container_client = ContainerClient.from_connection_string(
            conn_str=connection_string, container_name=container_name)

        print('Container => ', self.container_client)

        # Create container if it doesn't exist
        try:
            self.container_client.create_container()
        except Exception as e:
            # Container already exists
            print("Container already exists! : ", e)
            pass

    def upload_file(self, file_data, folder='', filename=None):
        """
        Upload a file to Azure Blob Storage

        Args:
            file_data: File object to upload
            folder: Optional folder/prefix for the blob
            filename: Optional custom filename (if None, uses file_data.filename)

        Returns:
            dict: Contains 'filename', 'blob_name', and 'url'
        """
        if filename is None:
            filename = secure_filename(file_data.filename)
        else:
            filename = secure_filename(filename)

        # Create blob name with folder prefix if provided
        blob_name = f"{folder}/{filename}" if folder else filename

        # Determine content type
        content_type = self._get_content_type(filename)

        blob = BlobClient.from_connection_string(
            conn_str=self.connection_string, container_name=self.container_name, blob_name=blob_name)

        print('blob_client ', blob)

        # Upload file
        file_data.seek(0)  # Reset file pointer to beginning
        blob.upload_blob(
            file_data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
        )

        # Get the blob URL
        blob_url = blob.url

        return {
            'filename': filename,
            'blob_name': blob_name,
            'url': blob_url
        }

    def get_blob_url(self, blob_name):
        """
        Get the public URL for a blob

        Args:
            blob_name: Name of the blob

        Returns:
            str: Public URL of the blob
        """

        blob = BlobClient.from_connection_string(
            conn_str=self.connection_string, container_name=self.container_name, blob_name=blob_name)

        return blob.url

    # def get_blob_sas_url(self, blob_name, expiry_hours=1):
    #     """
    #     Generate a SAS URL for a blob with read permissions

    #     Args:
    #         blob_name: Name of the blob
    #         expiry_hours: Number of hours until the SAS token expires

    #     Returns:
    #         str: SAS URL with read permissions
    #     """
    #     blob = BlobClient.from_connection_string(conn_str=self.connection_string, container_name=self.container_name, blob_name=blob_name)

    #     # Generate SAS token
    #     sas_token = generate_blob_sas(
    #         account_name=blob.account_name,
    #         container_name=self.container_name,
    #         blob_name=blob_name,
    #         account_key=self._get_account_key(),
    #         permission=BlobSasPermissions(read=True),
    #         expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
    #     )

    #     return f"{blob_client.url}?{sas_token}"

    def delete_blob(self, blob_name):
        """
        Delete a blob from storage

        Args:
            blob_name: Name of the blob to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            blob = BlobClient.from_connection_string(
                conn_str=self.connection_string, container_name=self.container_name, blob_name=blob_name)

            blob.delete_blob()
            return True
        except Exception as e:
            print(f"Error deleting blob {blob_name}: {str(e)}")
            return False

    def blob_exists(self, blob_name):
        """
        Check if a blob exists

        Args:
            blob_name: Name of the blob

        Returns:
            bool: True if blob exists, False otherwise
        """
        try:

            blob = BlobClient.from_connection_string(
                conn_str=self.connection_string, container_name=self.container_name, blob_name=blob_name)
            return blob.exists()
        except Exception:
            return False

    def _get_content_type(self, filename):
        """
        Determine content type based on file extension

        Args:
            filename: Name of the file

        Returns:
            str: MIME type
        """
        extension = filename.rsplit(
            '.', 1)[-1].lower() if '.' in filename else ''

        content_types = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'ppt': 'application/vnd.ms-powerpoint',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        }

        return content_types.get(extension, 'application/octet-stream')

    def _get_account_key(self):
        """
        Extract account key from connection string

        Returns:
            str: Azure Storage account key
        """
        conn_dict = dict(item.split('=', 1)
                         for item in self.connection_string.split(';') if '=' in item)
        return conn_dict.get('AccountKey', '')
