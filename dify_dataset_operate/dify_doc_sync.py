#!/usr/bin/env python3
import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Optional

from dify_dataset_base import DifyDatasetBaseClient
from dify_dataset_db import DifyDatasetDBClient
from dify_dataset_doc import DifyDatasetDocClient

# Calculate SHA256 hash of a file
def _sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# Load manifest from a JSON file
def _load_manifest(manifest_path: Path) -> Dict[str, Dict[str, str]]:
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))

# Save manifest to a JSON file
def _save_manifest(manifest_path: Path, manifest: Dict[str, Dict[str, str]]) -> None:
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

# Collect all files in a directory recursively
def _collect_files(doc_dir: Path) -> list[Path]:
    return [p for p in doc_dir.rglob("*") if p.is_file()]

# Sync documents to Dify dataset
# doc_dir: Directory containing documents to sync
# manifest_path: Path to the manifest file
# dry_run: If True, only show actions without uploading

def sync_docs(doc_dir: Path, manifest_path: Path, dry_run: bool = False) -> None:
    db_client = DifyDatasetDBClient()
    doc_client = DifyDatasetDocClient()

    logging.info("scan_dir=%s", doc_dir)
    manifest = _load_manifest(manifest_path)

    name_to_id = {item.get("name"): item.get("id") for item in db_client.list_all_documents()}

    updated = 0
    skipped = 0

    for file_path in _collect_files(doc_dir):
        rel_path = str(file_path.relative_to(doc_dir))
        file_hash = _sha256(file_path)
        previous = manifest.get(rel_path, {})

        if previous.get("sha256") == file_hash:
            skipped += 1
            logging.info("skip unchanged: %s", rel_path)
            continue

        doc_id = previous.get("document_id") or name_to_id.get(file_path.name)
        if dry_run:
            logging.info("dry_run %s: %s", "update" if doc_id else "create", rel_path)
            continue

        if doc_id:
            logging.info("update: %s (document_id=%s)", rel_path, doc_id)
            resp = doc_client.update_by_file(doc_id, str(file_path))
        else:
            logging.info("create: %s", rel_path)
            resp = doc_client.create_by_file(str(file_path))
            doc_id = (resp.get("document") or {}).get("id") or name_to_id.get(file_path.name)

        manifest[rel_path] = {
            "sha256": file_hash,
            "document_id": doc_id or "",
        }
        updated += 1

    if not dry_run:
        _save_manifest(manifest_path, manifest)

    logging.info("sync_done updated=%s skipped=%s", updated, skipped)


def main() -> None:
    parser = argparse.ArgumentParser(description="Incremental sync docs to Dify dataset")
    parser.add_argument("--doc-dir", default="../doc", help="Doc directory path (default: ../doc)")
    parser.add_argument(
        "--manifest",
        default=".dify_doc_manifest.json",
        help="Manifest file path (default: .dify_doc_manifest.json)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show actions without uploading")
    args = parser.parse_args()

    log_path = DifyDatasetBaseClient.configure_logging()
    logging.info("log_file=%s", log_path)

    doc_dir = Path(args.doc_dir).resolve()
    manifest_path = Path(args.manifest).resolve()

    if not doc_dir.exists() or not doc_dir.is_dir():
        raise RuntimeError(f"doc dir not found: {doc_dir}")

    sync_docs(doc_dir, manifest_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
