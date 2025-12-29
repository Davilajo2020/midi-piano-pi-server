"""MIDI file upload and management endpoints."""

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from ...core.config import get_settings

router = APIRouter(prefix="/api/v1/files", tags=["files"])


class FileInfo(BaseModel):
    """Information about an uploaded file."""
    id: str
    name: str
    size: int
    uploaded_at: str
    path: str


class FileListResponse(BaseModel):
    """Response containing list of files."""
    files: list[FileInfo]
    total: int


def get_upload_dir() -> Path:
    """Get the upload directory, creating it if needed."""
    settings = get_settings()
    upload_dir = Path(settings.uploads.directory)

    if not upload_dir.exists():
        upload_dir.mkdir(parents=True, exist_ok=True)

    return upload_dir


def is_valid_extension(filename: str) -> bool:
    """Check if file has a valid extension."""
    settings = get_settings()
    ext = Path(filename).suffix.lower()
    return ext in settings.uploads.allowed_extensions


@router.get("", response_model=FileListResponse)
async def list_files():
    """List all uploaded MIDI files."""
    upload_dir = get_upload_dir()

    files = []
    for file_path in upload_dir.iterdir():
        if file_path.is_file() and is_valid_extension(file_path.name):
            stat = file_path.stat()
            # Use filename without extension as ID
            file_id = file_path.stem

            files.append(FileInfo(
                id=file_id,
                name=file_path.name,
                size=stat.st_size,
                uploaded_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                path=str(file_path),
            ))

    # Sort by upload time, newest first
    files.sort(key=lambda f: f.uploaded_at, reverse=True)

    return FileListResponse(files=files, total=len(files))


@router.post("/upload", response_model=FileInfo)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a MIDI or KAR file.

    Accepts .mid, .midi, and .kar files.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not is_valid_extension(file.filename):
        settings = get_settings()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {settings.uploads.allowed_extensions}"
        )

    # Check file size
    settings = get_settings()
    max_size = settings.uploads.max_file_size_mb * 1024 * 1024

    # Read file content
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.uploads.max_file_size_mb}MB"
        )

    # Generate unique filename
    upload_dir = get_upload_dir()
    ext = Path(file.filename).suffix.lower()
    base_name = Path(file.filename).stem

    # Sanitize filename
    safe_name = "".join(c for c in base_name if c.isalnum() or c in "._- ")[:100]
    if not safe_name:
        safe_name = str(uuid.uuid4())[:8]

    # Add timestamp to avoid collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_name = f"{safe_name}_{timestamp}{ext}"
    file_path = upload_dir / final_name

    # Write file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    stat = file_path.stat()

    return FileInfo(
        id=file_path.stem,
        name=final_name,
        size=stat.st_size,
        uploaded_at=datetime.now().isoformat(),
        path=str(file_path),
    )


@router.get("/{file_id}", response_model=FileInfo)
async def get_file(file_id: str):
    """Get information about a specific file."""
    upload_dir = get_upload_dir()

    # Find file with matching ID (stem)
    for file_path in upload_dir.iterdir():
        if file_path.stem == file_id and is_valid_extension(file_path.name):
            stat = file_path.stat()
            return FileInfo(
                id=file_id,
                name=file_path.name,
                size=stat.st_size,
                uploaded_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                path=str(file_path),
            )

    raise HTTPException(status_code=404, detail="File not found")


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """Delete an uploaded file."""
    upload_dir = get_upload_dir()

    # Find and delete file with matching ID
    for file_path in upload_dir.iterdir():
        if file_path.stem == file_id and is_valid_extension(file_path.name):
            file_path.unlink()
            return {"success": True, "deleted": file_id}

    raise HTTPException(status_code=404, detail="File not found")
