from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
DOCUMENT_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "webp"}


@dataclass
class StorageError:
    field: str
    message: str


def get_storage_root() -> Path:
    root = Path(current_app.config["STORAGE_LOCAL_ROOT"])
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_uploaded_file(
    *,
    upload: FileStorage | None,
    folder: str,
    allowed_extensions: set[str],
) -> tuple[dict | None, StorageError | None]:
    if upload is None or not upload.filename:
        return None, StorageError("file", "file is required.")

    filename = secure_filename(upload.filename)
    if not filename or "." not in filename:
        return None, StorageError("file", "file must include a valid filename and extension.")

    extension = filename.rsplit(".", 1)[1].lower()
    if extension not in allowed_extensions:
        return None, StorageError(
            "file",
            f"Unsupported file type. Allowed: {', '.join(sorted(allowed_extensions))}.",
        )

    upload.stream.seek(0, 2)
    size = upload.stream.tell()
    upload.stream.seek(0)
    max_size = current_app.config["STORAGE_MAX_UPLOAD_BYTES"]
    if size > max_size:
        return None, StorageError("file", "file exceeds the maximum upload size.")

    relative_folder = Path(folder.strip("/"))
    unique_name = f"{uuid4().hex}.{extension}"
    relative_path = relative_folder / unique_name
    absolute_path = get_storage_root() / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    upload.save(absolute_path)

    return {
        "storage_path": relative_path.as_posix(),
        "url": build_public_storage_url(relative_path.as_posix()),
        "filename": filename,
        "size": size,
    }, None


def delete_stored_file(storage_path: str | None) -> None:
    if not storage_path:
        return
    absolute_path = get_storage_root() / storage_path
    if absolute_path.exists():
        absolute_path.unlink()


def build_public_storage_url(storage_path: str) -> str:
    public_base = current_app.config["STORAGE_PUBLIC_BASE_URL"].rstrip("/")
    return f"{public_base}/{storage_path.lstrip('/')}"
