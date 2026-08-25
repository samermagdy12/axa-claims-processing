from pathlib import Path
from uuid import UUID, uuid4


def store_claim_document(upload_dir: str, claim_id: UUID, original_file_name: str, content: bytes) -> tuple[Path, str]:
    safe_name = Path(original_file_name).name
    if safe_name in {"", ".", ".."}:
        raise ValueError("The uploaded file must have a valid file name")
    suffix = Path(safe_name).suffix.lower()
    document_id = uuid4()
    relative_path = Path("claims") / str(claim_id) / f"{document_id}{suffix}"
    destination = Path(upload_dir) / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_suffix(f"{destination.suffix}.tmp")
    temporary_path.write_bytes(content)
    temporary_path.replace(destination)
    return destination, relative_path.as_posix()
