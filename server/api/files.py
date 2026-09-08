"""File listing API endpoint — reads directory listings from the filesystem."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from config.backend.logger import get_api_logger
import os
import stat
import time

logger = get_api_logger("files")

router = APIRouter(prefix="/api/files", tags=["files"])

# Whitelist of base directories that can be browsed
ALLOWED_BASES = [
    os.path.expanduser("~/Documents/agents-vault"),
    os.path.expanduser("~/Documents/technology"),
    os.path.expanduser("~/Documents/notes"),
]

# File extensions that can be previewed inline
PREVIEW_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".ts", ".vue", ".html", ".css",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".sh", ".bash", ".zshrc", ".env", ".xml", ".svg", ".sql",
    ".log", ".mdx", ".rst", ".tex", ".c", ".h", ".cpp", ".hpp",
    ".rs", ".go", ".java", ".kt", ".swift", ".rb", ".php", ".pl",
    ".lua", ".r", ".m", ".mm",
}


def resolve_path(requested: str) -> str:
    """Resolve and validate a requested path.

    Joins the first allowed base with the requested subpath.
    Returns the resolved absolute path, or raises HTTPException.
    """
    # Clean the requested path — strip leading slashes, prevent traversal
    clean = requested.lstrip("/")
    if not clean:
        clean = "."

    # Try each allowed base
    for base in ALLOWED_BASES:
        candidate = os.path.normpath(os.path.join(base, clean))
        # Must be within the allowed base
        if not candidate.startswith(base):
            continue
        if not os.path.exists(candidate):
            continue
        return candidate

    raise HTTPException(
        status_code=404,
        detail=f"Path not found or not allowed: {requested}",
    )


def list_bases() -> list[dict]:
    """List the top-level allowed base directories."""
    results = []
    for base in ALLOWED_BASES:
        name = os.path.basename(base)
        if os.path.isdir(base):
            results.append({
                "name": name,
                "path": "",
                "type": "directory",
                "size": 0,
                "modified": os.path.getmtime(base),
                "abs_path": base,
            })
    return results


@router.get("/list")
async def list_files(path: str = Query("", description="Relative path within allowed bases")):
    """List files and directories at the given path.

    If path is empty, returns the top-level allowed base directories.
    """
    try:
        if not path:
            return {"entries": list_bases(), "base": ""}

        resolved = resolve_path(path)

        if not os.path.isdir(resolved):
            raise HTTPException(status_code=400, detail=f"Not a directory: {path}")

        entries = []
        for entry in sorted(os.listdir(resolved), key=lambda x: (not os.path.isdir(os.path.join(resolved, x)), x.lower())):
            full = os.path.join(resolved, entry)
            try:
                st = os.stat(full)
                is_dir = os.path.isdir(full)
                _, ext = os.path.splitext(entry)
                entries.append({
                    "name": entry,
                    "path": os.path.join(path, entry) if path else entry,
                    "type": "directory" if is_dir else "file",
                    "size": st.st_size if not is_dir else 0,
                    "modified": st.st_mtime,
                    "ext": ext.lower() if not is_dir else "",
                    "previewable": ext.lower() in PREVIEW_EXTENSIONS,
                })
            except OSError:
                # Skip entries we can't stat
                continue

        return {"entries": entries, "base": path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files at '{path}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/raw")
async def raw_file(path: str = Query(..., description="Relative path within allowed bases")):
    """Serve a raw file for preview or download."""
    try:
        resolved = resolve_path(path)

        if not os.path.isfile(resolved):
            raise HTTPException(status_code=400, detail=f"Not a file: {path}")

        _, ext = os.path.splitext(resolved)

        # Determine media type
        media_types = {
            ".md": "text/markdown; charset=utf-8",
            ".txt": "text/plain; charset=utf-8",
            ".py": "text/x-python; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".ts": "text/typescript; charset=utf-8",
            ".vue": "text/html; charset=utf-8",
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".json": "application/json",
            ".yaml": "text/yaml; charset=utf-8",
            ".yml": "text/yaml; charset=utf-8",
            ".xml": "application/xml; charset=utf-8",
            ".svg": "image/svg+xml",
            ".log": "text/plain; charset=utf-8",
            ".sh": "text/x-shellscript; charset=utf-8",
            ".toml": "text/toml; charset=utf-8",
        }

        media_type = media_types.get(ext.lower(), "application/octet-stream")
        return FileResponse(resolved, media_type=media_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving raw file '{path}': {e}")
        raise HTTPException(status_code=500, detail=str(e))