"""Record or refresh ONNX weight hashes for the fox XAL export (reproducibility)."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
REVISION_PATH = ROOT / "inference-weights-revision.json"
CANDIDATES_PATH = ROOT / "candidates" / "fox-forest.png.candidates.json"
HASH_LIMIT = 536_870_912


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    if path.stat().st_size > HASH_LIMIT:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_weight_path(work_dir: Path, export_entry: dict) -> Path | None:
    raw = export_entry.get("path")
    if not isinstance(raw, str):
        return None
    name = Path(raw.replace("\\", "/")).name
    candidate = work_dir / "models" / "groundingdino_swint_sam2_large-r20240806" / name
    if candidate.is_file():
        return candidate
    fallback = work_dir / name
    return fallback if fallback.is_file() else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="X-AnyLabeling model data directory containing downloaded ONNX weights",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Rewrite inference-weights-revision.json with newly computed hashes and bumped revision",
    )
    args = parser.parse_args()

    revision = json.loads(REVISION_PATH.read_text(encoding="utf-8"))
    export = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    weights = export.get("inference", {}).get("weights", {})

    report: dict[str, object] = {"revision": revision.get("revision"), "files": []}
    if args.work_dir:
        work_dir = args.work_dir.expanduser().resolve()
        for item in revision.get("weight_files", []):
            role = item["role"]
            key = {
                "grounding_dino": "model_path",
                "sam2_encoder": "encoder_model_path",
                "sam2_decoder": "decoder_model_path",
            }.get(role)
            export_entry = weights.get(key or "", {})
            path = resolve_weight_path(work_dir, export_entry if isinstance(export_entry, dict) else {})
            digest = sha256_file(path) if path else None
            report["files"].append(
                {
                    "role": role,
                    "path": str(path) if path else None,
                    "sha256": digest,
                    "sha256_note": None if digest else item.get("sha256_note"),
                }
            )
            if args.update and digest:
                item["sha256"] = digest
                item.pop("sha256_note", None)

        if args.update:
            revision["revision"] = int(revision.get("revision", 0)) + 1
            revision["recorded_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            REVISION_PATH.write_text(json.dumps(revision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Updated {REVISION_PATH} to revision {revision['revision']}")
    else:
        report["note"] = "Pass --work-dir to verify local ONNX hashes against the recorded revision."

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
