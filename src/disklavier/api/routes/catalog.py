"""MIDI file catalog endpoints - browse and play from pre-existing MIDI libraries."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...core.config import get_settings
from ...core.midi_player import get_midi_player

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


class CatalogFile(BaseModel):
    """Information about a catalog file."""
    id: str  # URL-safe identifier (relative path with / replaced)
    name: str  # Display name (filename)
    path: str  # Full path
    relative_path: str  # Path relative to catalog root
    size: int
    modified_at: str
    extension: str
    directory: str  # Parent directory name


class CatalogDirectory(BaseModel):
    """Information about a directory in the catalog."""
    name: str
    path: str
    file_count: int


class CatalogListResponse(BaseModel):
    """Response containing catalog files."""
    files: list[CatalogFile]
    directories: list[CatalogDirectory]
    total_files: int
    current_path: str


def get_catalog_dirs() -> list[Path]:
    """Get configured catalog directories."""
    settings = get_settings()
    dirs = []
    for dir_path in settings.catalog.directories:
        path = Path(dir_path).expanduser()
        if path.exists() and path.is_dir():
            dirs.append(path)
    return dirs


def is_valid_extension(filename: str) -> bool:
    """Check if file has a valid extension."""
    settings = get_settings()
    ext = Path(filename).suffix.lower()
    return ext in settings.catalog.allowed_extensions


def path_to_id(path: Path, base: Path) -> str:
    """Convert a file path to a URL-safe ID."""
    rel_path = path.relative_to(base)
    return str(rel_path).replace("/", "__").replace("\\", "__")


def id_to_path(file_id: str, base: Path) -> Path:
    """Convert a URL-safe ID back to a path."""
    rel_path = file_id.replace("__", "/")
    return base / rel_path


def scan_catalog(base_dir: Path, subdir: Optional[str] = None, scan_subdirs: bool = True) -> tuple[list[CatalogFile], list[CatalogDirectory]]:
    """Scan a catalog directory for MIDI files."""
    files = []
    directories = []

    # Determine the directory to scan
    if subdir:
        scan_dir = base_dir / subdir
        if not scan_dir.exists() or not scan_dir.is_dir():
            return files, directories
        # Security check - ensure we're still within base_dir
        try:
            scan_dir.resolve().relative_to(base_dir.resolve())
        except ValueError:
            return files, directories
    else:
        scan_dir = base_dir

    # Scan for files and directories
    try:
        for entry in sorted(scan_dir.iterdir()):
            if entry.name.startswith('.'):
                continue

            if entry.is_dir():
                # Count files in subdirectory
                file_count = 0
                if scan_subdirs:
                    for f in entry.rglob("*"):
                        if f.is_file() and is_valid_extension(f.name):
                            file_count += 1
                else:
                    for f in entry.iterdir():
                        if f.is_file() and is_valid_extension(f.name):
                            file_count += 1

                if file_count > 0:
                    directories.append(CatalogDirectory(
                        name=entry.name,
                        path=str(entry.relative_to(base_dir)),
                        file_count=file_count
                    ))

            elif entry.is_file() and is_valid_extension(entry.name):
                stat = entry.stat()
                rel_path = entry.relative_to(base_dir)

                files.append(CatalogFile(
                    id=path_to_id(entry, base_dir),
                    name=entry.stem,  # Filename without extension
                    path=str(entry),
                    relative_path=str(rel_path),
                    size=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    extension=entry.suffix.lower(),
                    directory=entry.parent.name if entry.parent != base_dir else ""
                ))
    except PermissionError:
        pass

    # Sort files by name
    files.sort(key=lambda f: f.name.lower())
    directories.sort(key=lambda d: d.name.lower())

    return files, directories


@router.get("", response_model=CatalogListResponse)
async def list_catalog(
    path: Optional[str] = Query(None, description="Subdirectory path to browse"),
    search: Optional[str] = Query(None, description="Search term to filter files")
):
    """
    List MIDI files in the catalog.

    Optionally browse a subdirectory or search for files.
    """
    settings = get_settings()
    catalog_dirs = get_catalog_dirs()

    if not catalog_dirs:
        return CatalogListResponse(
            files=[],
            directories=[],
            total_files=0,
            current_path=path or ""
        )

    all_files = []
    all_directories = []

    for base_dir in catalog_dirs:
        files, directories = scan_catalog(base_dir, path, settings.catalog.scan_subdirs)
        all_files.extend(files)
        all_directories.extend(directories)

    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        all_files = [f for f in all_files if search_lower in f.name.lower()]

    return CatalogListResponse(
        files=all_files,
        directories=all_directories,
        total_files=len(all_files),
        current_path=path or ""
    )


@router.get("/search")
async def search_catalog(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results")
):
    """Search for MIDI files across all catalog directories."""
    settings = get_settings()
    catalog_dirs = get_catalog_dirs()

    results = []
    search_lower = q.lower()

    for base_dir in catalog_dirs:
        # Recursively search
        pattern = "**/*" if settings.catalog.scan_subdirs else "*"
        for entry in base_dir.glob(pattern):
            if entry.is_file() and is_valid_extension(entry.name):
                if search_lower in entry.name.lower() or search_lower in entry.stem.lower():
                    stat = entry.stat()
                    rel_path = entry.relative_to(base_dir)

                    results.append(CatalogFile(
                        id=path_to_id(entry, base_dir),
                        name=entry.stem,
                        path=str(entry),
                        relative_path=str(rel_path),
                        size=stat.st_size,
                        modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        extension=entry.suffix.lower(),
                        directory=entry.parent.name if entry.parent != base_dir else ""
                    ))

                    if len(results) >= limit:
                        break

        if len(results) >= limit:
            break

    results.sort(key=lambda f: f.name.lower())
    return {"results": results, "total": len(results), "query": q}


@router.get("/{file_id}")
async def get_catalog_file(file_id: str):
    """Get information about a specific catalog file."""
    catalog_dirs = get_catalog_dirs()

    for base_dir in catalog_dirs:
        file_path = id_to_path(file_id, base_dir)
        if file_path.exists() and file_path.is_file() and is_valid_extension(file_path.name):
            # Security check
            try:
                file_path.resolve().relative_to(base_dir.resolve())
            except ValueError:
                continue

            stat = file_path.stat()
            rel_path = file_path.relative_to(base_dir)

            return CatalogFile(
                id=file_id,
                name=file_path.stem,
                path=str(file_path),
                relative_path=str(rel_path),
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                extension=file_path.suffix.lower(),
                directory=file_path.parent.name if file_path.parent != base_dir else ""
            )

    raise HTTPException(status_code=404, detail="File not found in catalog")


@router.post("/{file_id}/play")
async def play_catalog_file(file_id: str):
    """Load and play a MIDI file from the catalog."""
    catalog_dirs = get_catalog_dirs()
    player = get_midi_player()

    for base_dir in catalog_dirs:
        file_path = id_to_path(file_id, base_dir)
        if file_path.exists() and file_path.is_file() and is_valid_extension(file_path.name):
            # Security check
            try:
                file_path.resolve().relative_to(base_dir.resolve())
            except ValueError:
                continue

            # Load and play the file
            try:
                file_info = player.load(file_path)
                player.play()
                return {
                    "success": True,
                    "file": file_path.name,
                    "duration_ms": file_info.duration_ms,
                    "tracks": file_info.track_count
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to play file: {str(e)}")

    raise HTTPException(status_code=404, detail="File not found in catalog")
