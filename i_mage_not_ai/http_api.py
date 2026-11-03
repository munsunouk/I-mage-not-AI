"""Optional FastAPI surface for inspect and advisory endpoints."""
import asyncio
import tempfile
from pathlib import Path
from typing import Any

from .advisory_provenance import detect_advisory_image
from .core import inspect_image

try:
    from fastapi import FastAPI, File, UploadFile
    from fastapi.responses import JSONResponse
except ImportError:  # pragma: no cover - exercised via create_app guard
    FastAPI = None  # type: ignore[misc, assignment]
    File = None  # type: ignore[misc, assignment]
    UploadFile = Any  # type: ignore[misc, assignment]
    JSONResponse = Any  # type: ignore[misc, assignment]


def create_app() -> Any:
    if FastAPI is None or File is None:
        raise ImportError("install optional API dependencies: pip install -e '.[api]'")

    app = FastAPI(title="i-mage-not-ai", version="0.5.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/inspect")
    async def inspect_upload(file: UploadFile = File(...)) -> JSONResponse:
        suffix = Path(file.filename or "upload.bin").suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(await file.read())
            temp_path = Path(handle.name)
        try:
            report = await asyncio.to_thread(inspect_image, temp_path, report_path=file.filename)
            return JSONResponse(report)
        finally:
            temp_path.unlink(missing_ok=True)

    @app.post("/advisory/detect")
    async def advisory_upload(
        file: UploadFile = File(...),
        backend: str = "univfd",
        threshold: float = 0.5,
    ) -> JSONResponse:
        suffix = Path(file.filename or "upload.bin").suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(await file.read())
            temp_path = Path(handle.name)
        try:
            report = await asyncio.to_thread(
                detect_advisory_image,
                temp_path,
                backend=backend,
                threshold=threshold,
            )
            return JSONResponse(report)
        finally:
            temp_path.unlink(missing_ok=True)

    return app
