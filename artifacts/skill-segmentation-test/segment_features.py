"""Build approved feature masks from X-AnyLabeling candidates (Skill steps 2–5).

Mask geometry comes from Codex-reviewed XAL exports under
``artifacts/xal-fox-candidates-01/``. This script does not substitute hand-traced
polygons when XAL is unavailable — run XAL ``segment`` first.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops
from scipy import ndimage

ROOT = Path(__file__).parent
REPO = ROOT.parents[1]
SOURCE = ROOT / "fox-forest.png"
OUT = ROOT / "masks"
XAL_ROOT = REPO / "artifacts" / "xal-fox-candidates-01"
XAL_META_PATH = XAL_ROOT / "candidates" / "fox-forest.png.candidates.json"
XAL_MASK_DIR = XAL_ROOT / "masks" / "fox-forest.png"

def load_candidate(candidate_id: str, height: int, width: int) -> np.ndarray:
    path = XAL_MASK_DIR / f"{candidate_id}.png"
    with Image.open(path) as im:
        array = np.asarray(im.convert("L"))
    if array.shape != (height, width):
        raise ValueError(f"{candidate_id} mask dimensions differ from source")
    return array > 0


def main() -> None:
    if not XAL_META_PATH.is_file():
        raise SystemExit(
            f"Missing XAL candidates at {XAL_META_PATH}. "
            "Run X-AnyLabeling segment (Skill step 2) before regenerating masks."
        )

    OUT.mkdir(exist_ok=True)
    raw_meta = json.loads(XAL_META_PATH.read_text(encoding="utf-8"))
    source = Image.open(SOURCE).convert("RGB")
    width, height = source.size

    char = load_candidate("candidate-0001", height, width)
    head = load_candidate("candidate-0003", height, width) & char
    tail = load_candidate("candidate-0006", height, width) & char
    scarf = load_candidate("candidate-0007", height, width) & char
    flower = load_candidate("candidate-0008", height, width)
    mushroom = load_candidate("candidate-0009", height, width)
    sky = load_candidate("candidate-0011", height, width)
    mountains = load_candidate("candidate-0013", height, width)
    distant = sky | mountains

    body = char & ~head & ~tail & ~scarf
    body_labels, body_count = ndimage.label(body, structure=np.ones((3, 3), dtype=np.uint8))
    if body_count:
        body_sizes = np.bincount(body_labels.ravel())
        body_sizes[0] = 0
        body = body_labels == int(np.argmax(body_sizes))

    head = np.asarray(
        ImageChops.subtract(
            Image.fromarray((head.astype(np.uint8) * 255), mode="L"),
            Image.fromarray((scarf.astype(np.uint8) * 255), mode="L"),
        )
    ) > 0
    body = np.asarray(
        ImageChops.subtract(
            Image.fromarray((body.astype(np.uint8) * 255), mode="L"),
            Image.fromarray((scarf.astype(np.uint8) * 255), mode="L"),
        )
    ) > 0
    tail = np.asarray(
        ImageChops.subtract(
            Image.fromarray((tail.astype(np.uint8) * 255), mode="L"),
            Image.fromarray((body.astype(np.uint8) * 255), mode="L"),
        )
    ) > 0
    mushroom = np.asarray(
        ImageChops.subtract(
            Image.fromarray((mushroom.astype(np.uint8) * 255), mode="L"),
            Image.fromarray((tail.astype(np.uint8) * 255), mode="L"),
        )
    ) > 0

    mask_arrays = {
        "fox_head": head,
        "fox_body": body,
        "fox_tail": tail,
        "fox_scarf": scarf,
        "pink_flower": flower,
        "blue_mushroom": mushroom,
        "distant_sky_and_mountain": distant,
    }
    fox = char.copy()
    for part in ("fox_head", "fox_body", "fox_tail", "fox_scarf"):
        fox = fox | mask_arrays[part]
    mask_arrays["fox_character"] = fox

    for feature_id, mask in mask_arrays.items():
        Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(OUT / f"{feature_id}.png")

    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    raw_by_id = {c["id"]: c for c in raw_meta["candidates"]}

    def inventory_for(
        feature_id: str,
        description: str,
        approved_id: str | None,
        *,
        extra_rejected: list[str] | None = None,
        extra_approved: list[str] | None = None,
        derived_from: list[str] | None = None,
    ) -> dict:
        candidates: list[dict] = []
        if derived_from:
            candidates.append({"candidate_id": "codex-derived-from-xal", "status": "approved"})
            for cid in derived_from:
                candidates.append({"candidate_id": cid, "status": "approved"})
        elif approved_id:
            candidates.append({"candidate_id": approved_id, "status": "approved"})
        for cid in extra_approved or []:
            candidates.append({"candidate_id": cid, "status": "approved"})
        for cid in extra_rejected or []:
            candidates.append({"candidate_id": cid, "status": "rejected"})
        return {
            "id": f"inv-{feature_id}",
            "description": description,
            "status": "approved",
            "feature_id": feature_id,
            "candidates": candidates,
        }

    specs = [
        (
            "fox_character",
            "character",
            None,
            "Whole fox from XAL candidate-0001; part masks refine interior boundaries.",
            {"min_occupancy_ratio": 0.18, "max_silhouette_components": 3, "max_connected_components": 3},
            inventory_for(
                "fox_character",
                "Whole fox from XAL candidate-0001.",
                "candidate-0001",
                extra_rejected=["candidate-0002", "candidate-0004", "candidate-0005", "candidate-0010"],
            ),
            "candidate-0001",
        ),
        (
            "fox_head",
            "head",
            "fox_character",
            "Head and ears from candidate-0003, clipped to character and minus scarf.",
            {"min_occupancy_ratio": 0.04, "max_connected_components": 3},
            inventory_for(
                "fox_head",
                "Head/isolated from prompt fox head (candidate-0003).",
                "candidate-0003",
                extra_rejected=["candidate-0002"],
            ),
            "candidate-0003",
        ),
        (
            "fox_body",
            "body",
            "fox_character",
            "Torso/legs derived from whole fox minus approved head, tail, and scarf.",
            {"min_occupancy_ratio": 0.05, "max_connected_components": 3},
            inventory_for(
                "fox_body",
                "Derived from candidate-0001 minus head/tail/scarf masks.",
                None,
                derived_from=["candidate-0001", "candidate-0003", "candidate-0006", "candidate-0007"],
                extra_rejected=["candidate-0004"],
            ),
            None,
        ),
        (
            "fox_tail",
            "tail",
            "fox_character",
            "Tail from candidate-0006, clipped to character and minus body overlap.",
            {"min_occupancy_ratio": 0.04, "max_connected_components": 3},
            inventory_for(
                "fox_tail",
                "Tail from prompt fox tail (candidate-0006).",
                "candidate-0006",
                extra_rejected=["candidate-0005"],
            ),
            "candidate-0006",
        ),
        (
            "fox_scarf",
            "clothing",
            "fox_character",
            "Teal scarf from candidate-0007, clipped to character silhouette.",
            {"min_occupancy_ratio": 0.015, "max_connected_components": 3},
            inventory_for("fox_scarf", "Scarf from prompt teal scarf (candidate-0007).", "candidate-0007"),
            "candidate-0007",
        ),
        (
            "pink_flower",
            "flower",
            None,
            "Flower from candidate-0008.",
            {"min_occupancy_ratio": 0.003, "max_connected_components": 3},
            inventory_for("pink_flower", "Pink flower prompt (candidate-0008).", "candidate-0008"),
            "candidate-0008",
        ),
        (
            "blue_mushroom",
            "mushroom",
            None,
            "Mushroom from candidate-0009; tail-occluded pixels removed.",
            {"min_occupancy_ratio": 0.008, "max_connected_components": 3},
            inventory_for(
                "blue_mushroom",
                "Blue mushroom prompt (candidate-0009).",
                "candidate-0009",
                extra_rejected=["candidate-0010"],
            ),
            "candidate-0009",
        ),
        (
            "distant_sky_and_mountain",
            "background_region",
            None,
            "Union of sky (0011) and mountains (0013); coarse background, not separate semantics.",
            {"min_occupancy_ratio": 0.08, "max_connected_components": 4},
            inventory_for(
                "distant_sky_and_mountain",
                "Sky and mountain XAL prompts merged for a coarse upper background patch.",
                "candidate-0011",
                extra_approved=["candidate-0013"],
                extra_rejected=["candidate-0012", "candidate-0014", "candidate-0015", "candidate-0016", "candidate-0017"],
            ),
            "candidate-0011",
        ),
    ]

    features = []
    inventory = []
    for feature_id, role, parent_id, note, props, inv_entry, xal_id in specs:
        mask_path = OUT / f"{feature_id}.png"
        mask_hash = hashlib.sha256(mask_path.read_bytes()).hexdigest()
        candidate = raw_by_id.get(xal_id) if xal_id else None
        provenance = {
            "origin": "agent_inferred",
            "segmentation_note": note,
            "candidate_stage": "artifacts/xal-fox-candidates-01/candidates/fox-forest.png.candidates.json",
            "model_id": raw_meta["inference"]["model_id"],
            "xal_application": raw_meta["application"],
        }
        if xal_id:
            provenance.update(
                {
                    "candidate_id": xal_id,
                    "prompt": candidate.get("prompt") if candidate else None,
                    "xal_label": candidate.get("label") if candidate else None,
                    "xal_score": candidate.get("score") if candidate else None,
                }
            )
        if feature_id == "fox_body":
            provenance["source_candidate_ids"] = [
                "candidate-0001",
                "candidate-0003",
                "candidate-0006",
                "candidate-0007",
            ]
        if feature_id == "distant_sky_and_mountain":
            provenance["source_candidate_ids"] = ["candidate-0011", "candidate-0013"]

        feature = {
            "id": feature_id,
            "role": role,
            "geometry": {"type": "mask", "path": f"masks/{feature_id}.png", "sha256": mask_hash},
            "properties": props,
            "provenance": provenance,
        }
        if parent_id:
            feature["parent_id"] = parent_id
        features.append(feature)
        inventory.append(inv_entry)

    manifest = {
        "schema_version": "0.6",
        "asset": {"path": "fox-forest.png", "format": "png", "sha256": digest},
        "intent": {
            "kind": "game_asset",
            "style": "storybook",
            "purpose": "Skill trial: XAL candidates reviewed, then v0.6 manifest and CLI review",
            "origin": "agent_inference",
        },
        "overlap_constraints": [
            {"feature_a": "fox_scarf", "feature_b": "fox_tail", "max_overlap_ratio": 0.06},
        ],
        "feature_inventory": inventory,
        "features": features,
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    decisions_src = REPO / "artifacts" / "xal-fox-review-01" / "review-decisions.json"
    if decisions_src.is_file():
        (ROOT / "xal-review-decisions.json").write_text(
            decisions_src.read_text(encoding="utf-8"), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
