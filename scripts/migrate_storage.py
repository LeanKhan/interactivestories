"""
Copy Azure Blob Storage containers from one storage account to another

Copies every blob (with its content type and metadata) and the container's
public access level. Safe to re-run: blobs already in the destination with
the same size are skipped.

Usage:
    SOURCE_AZURE_STORAGE_CONNECTION_STRING="..." \\
    DEST_AZURE_STORAGE_CONNECTION_STRING="..." \\
    python scripts/migrate_storage.py [container ...]

Containers default to AZURE_CONTAINER_NAME and AZURE_BACKUP_CONTAINER_NAME from .env.
"""

import os
import sys

from azure.core.exceptions import HttpResponseError, ResourceExistsError
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv


def copy_container(source_service, dest_service, name):
    source = source_service.get_container_client(name)
    dest = dest_service.get_container_client(name)

    # The PDF container is usually public (the site links to blobs directly); backups must stay private
    public_access = source.get_container_properties().public_access

    try:
        dest.create_container(public_access=public_access)
    except ResourceExistsError:
        dest.set_container_access_policy(signed_identifiers={}, public_access=public_access)
    except HttpResponseError as e:
        if e.error_code == "PublicAccessNotPermitted":
            sys.exit(f"❌ '{name}' needs public access. In the new storage account, open "
                     "Settings > Configuration, enable 'Allow Blob anonymous access', and re-run.")
        raise

    existing = {blob.name: blob.size for blob in dest.list_blobs()}
    copied = skipped = 0

    for blob in source.list_blobs(include=["metadata"]):
        if existing.get(blob.name) == blob.size:
            skipped += 1
            continue

        data = source.download_blob(blob.name).readall()
        dest.upload_blob(
            blob.name,
            data,
            overwrite=True,
            content_settings=blob.content_settings,
            metadata=blob.metadata,
        )
        copied += 1
        print(f"  {blob.name}")

    source_count = sum(1 for _ in source.list_blobs())
    dest_count = sum(1 for _ in dest.list_blobs())
    status = "✅" if dest_count >= source_count else "⚠️"
    print(f"{status} '{name}' ({public_access or 'private'}): {copied} copied, {skipped} already there, "
          f"{dest_count}/{source_count} blobs in destination")

    return dest_count >= source_count


def main():
    # Windows consoles default to a codepage that can't print the status emoji
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()

    source_conn = os.getenv("SOURCE_AZURE_STORAGE_CONNECTION_STRING")
    dest_conn = os.getenv("DEST_AZURE_STORAGE_CONNECTION_STRING")
    if not source_conn or not dest_conn:
        sys.exit("❌ Set SOURCE_AZURE_STORAGE_CONNECTION_STRING and DEST_AZURE_STORAGE_CONNECTION_STRING.")

    containers = sys.argv[1:] or [
        os.getenv("AZURE_CONTAINER_NAME") or "pdf-stories",
        os.getenv("AZURE_BACKUP_CONTAINER_NAME") or "pdf-stories-backups",
    ]

    source_service = BlobServiceClient.from_connection_string(source_conn)
    dest_service = BlobServiceClient.from_connection_string(dest_conn)

    ok = True
    for name in containers:
        print(f"Copying '{name}' ...")
        ok = copy_container(source_service, dest_service, name) and ok

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
