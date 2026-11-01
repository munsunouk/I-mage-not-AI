"""Optional learned image-similarity metrics with offline-only model loading."""
from __future__ import annotations

import hashlib
import importlib.metadata
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _directory_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    files = sorted(item for item in path.rglob("*") if item.is_file())
    if not files:
        raise ValueError(f"model directory has no files: {path}")
    for item in files:
        hasher.update(item.relative_to(path).as_posix().encode("utf-8"))
        hasher.update(bytes.fromhex(_digest(item)))
    return hasher.hexdigest()


def _base_report(reference: Path, candidate: Path, metric: str) -> dict[str, Any]:
    reference = reference.resolve(strict=True)
    candidate = candidate.resolve(strict=True)
    with Image.open(reference) as first, Image.open(candidate) as second:
        first.load()
        second.load()
        if first.size != second.size:
            raise ValueError("reference and candidate images must have identical dimensions")
        width, height = first.size
    return {
        "schema_version": "1", "status": "INCONCLUSIVE", "completeness": "INCOMPLETE",
        "metric": metric,
        "reference": {"path": str(reference), "sha256": _digest(reference), "width": width, "height": height},
        "candidate": {"path": str(candidate), "sha256": _digest(candidate), "width": width, "height": height},
    }


def compare_lpips(reference: Path, candidate: Path, *, network: str = "alex",
                  max_distance: float | None = None, weight_cache: Path | None = None) -> dict[str, Any]:
    """Compute official LPIPS distance using cached local weights only."""
    report = _base_report(reference, candidate, "lpips")
    if max_distance is not None and (not math.isfinite(max_distance) or max_distance < 0):
        raise ValueError("max_distance must be a finite non-negative number")
    if network not in {"alex", "vgg", "squeeze"}:
        raise ValueError("LPIPS network must be alex, vgg, or squeeze")
    try:
        import torch  # type: ignore[import-not-found]
        import lpips  # type: ignore[import-not-found]
    except ImportError as exc:
        report["reason"] = f"optional LPIPS dependencies are unavailable: {exc.name}"
        return report

    cache = (weight_cache or Path.home() / ".cache" / "torch").expanduser().resolve()
    checkpoint_names = {"alex": "alexnet-owt-7be5be79.pth",
                        "vgg": "vgg16-397923af.pth",
                        "squeeze": "squeezenet1_0-b66bff10.pth"}
    backbone_weights = cache / "checkpoints" / checkpoint_names[network]
    package_weights = Path(lpips.__file__).resolve().parent / "weights" / "v0.1" / f"{network}.pth"
    if not backbone_weights.is_file() or not package_weights.is_file():
        report["reason"] = "required LPIPS and torchvision weights are not present in the local cache; network downloads are disabled"
        report["required_local_files"] = [str(backbone_weights), str(package_weights)]
        return report

    try:
        torch.hub.set_dir(str(cache))
        torch.use_deterministic_algorithms(True)
        torch.set_num_threads(1)
        model = lpips.LPIPS(net=network, version="0.1", pretrained=True, eval_mode=True)
        model.to("cpu")
        with Image.open(report["reference"]["path"]) as image:
            reference_pixels = np.asarray(image.convert("RGB"), dtype=np.float32).copy() / 127.5 - 1.0
        with Image.open(report["candidate"]["path"]) as image:
            candidate_pixels = np.asarray(image.convert("RGB"), dtype=np.float32).copy() / 127.5 - 1.0
        reference_tensor = torch.from_numpy(reference_pixels).permute(2, 0, 1).unsqueeze(0)
        candidate_tensor = torch.from_numpy(candidate_pixels).permute(2, 0, 1).unsqueeze(0)
        with torch.inference_mode():
            distance = float(model(reference_tensor, candidate_tensor).reshape(-1)[0].item())
    except (OSError, RuntimeError, ValueError) as exc:
        report["reason"] = f"LPIPS inference unavailable: {exc}"
        return report

    if not math.isfinite(distance):
        report["reason"] = "LPIPS returned a non-finite distance"
        return report
    report.update({
        "status": "INCONCLUSIVE" if max_distance is None else ("PASS" if distance <= max_distance else "FAIL"),
        "completeness": "COMPLETE" if max_distance is not None else "INCOMPLETE",
        "measured": {"distance": distance, "network": network, "lpips_version": "0.1"},
        "threshold": {"max_distance": max_distance},
        "formula": "LPIPS v0.1 learned weighted distance over normalized deep feature activations; lower is more similar",
        "provenance": {"backend": "richzhang/PerceptualSimilarity", "torch_version": torch.__version__,
                       "lpips_package_version": importlib.metadata.version("lpips"), "device": "cpu",
                       "deterministic_algorithms": True, "backbone_weights_sha256": _digest(backbone_weights),
                       "lpips_weights_sha256": _digest(package_weights)},
    })
    return report


def compare_dinov2(reference: Path, candidate: Path, *, model_dir: Path,
                   min_similarity: float | None = None) -> dict[str, Any]:
    """Compare local DINOv2 CLS embeddings; model files are never downloaded."""
    report = _base_report(reference, candidate, "dinov2_cosine_similarity")
    if min_similarity is not None and (not math.isfinite(min_similarity) or not -1 <= min_similarity <= 1):
        raise ValueError("min_similarity must be a finite number between -1 and 1")
    model_dir = model_dir.expanduser().resolve()
    if not model_dir.is_dir():
        report["reason"] = f"local DINOv2 model directory does not exist: {model_dir}"
        return report
    try:
        import torch  # type: ignore[import-not-found]
        from transformers import AutoImageProcessor, AutoModel  # type: ignore[import-not-found]
    except ImportError as exc:
        report["reason"] = f"optional DINOv2 dependencies are unavailable: {exc.name}"
        return report

    try:
        torch.use_deterministic_algorithms(True)
        torch.set_num_threads(1)
        processor = AutoImageProcessor.from_pretrained(str(model_dir), local_files_only=True)
        model = AutoModel.from_pretrained(str(model_dir), local_files_only=True).to("cpu").eval()
        tensors = []
        for path in (Path(report["reference"]["path"]), Path(report["candidate"]["path"])):
            with Image.open(path) as image:
                inputs = processor(images=image.convert("RGB"), return_tensors="pt")
            tensors.append(inputs["pixel_values"])
        with torch.inference_mode():
            vectors = [model(pixel_values=pixels).last_hidden_state[:, 0, :] for pixels in tensors]
            first = torch.nn.functional.normalize(vectors[0].float(), dim=-1)
            second = torch.nn.functional.normalize(vectors[1].float(), dim=-1)
            similarity = float(torch.sum(first * second, dim=-1)[0].item())
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        report["reason"] = f"local DINOv2 inference unavailable: {exc}"
        return report

    if not math.isfinite(similarity):
        report["reason"] = "DINOv2 returned a non-finite cosine similarity"
        return report
    report.update({
        "status": "INCONCLUSIVE" if min_similarity is None else ("PASS" if similarity >= min_similarity else "FAIL"),
        "completeness": "COMPLETE" if min_similarity is not None else "INCOMPLETE",
        "measured": {"cosine_similarity": similarity, "embedding": "CLS token"},
        "threshold": {"min_similarity": min_similarity},
        "formula": "dot(normalize(DINOv2_CLS(reference)), normalize(DINOv2_CLS(candidate))); higher is more similar",
        "provenance": {"backend": "facebookresearch/dinov2 via local Hugging Face model files",
                       "model_dir": str(model_dir), "model_files_sha256": _directory_digest(model_dir),
                       "transformers_version": importlib.metadata.version("transformers"),
                       "torch_version": torch.__version__, "device": "cpu", "deterministic_algorithms": True},
    })
    return report
