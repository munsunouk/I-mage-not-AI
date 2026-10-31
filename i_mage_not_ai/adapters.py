"""Read-only source adapter contracts and built-in capability registry."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Any
import hashlib
import xml.etree.ElementTree as ET
from PIL import Image

class SourceAdapter(Protocol):
    id: str
    version: str
    capabilities: frozenset[str]
    def supports(self, source: Path, requirements: set[str]) -> bool: ...
    def extract(self, source: Path, requirements: set[str]) -> Any: ...

class FeatureAdapter(Protocol):
    id: str
    version: str
    def supports(self, evidence: Any, requirements: set[str]) -> bool: ...
    def extract(self, evidence: Any, requirements: set[str]) -> Any: ...

@dataclass(frozen=True)
class MaskFeatureAdapter:
    id: str = "raster_mask"
    version: str = "1.0"
    capabilities: frozenset[str] = frozenset({"feature_mask", "mask_geometry"})
    def supports(self, feature: dict[str,Any], requirements: set[str]) -> bool:
        return feature.get("geometry",{}).get("type") in {"mask","alpha_mask"} and requirements <= self.capabilities
    def extract(self, source: Path, expected_size: tuple[int,int]):
        with Image.open(source) as opened:
            if opened.size!=expected_size: raise ValueError(f"mask size {opened.size} differs from asset {expected_size}")
            return opened.convert("L")

@dataclass(frozen=True)
class AdapterDescriptor:
    id: str
    version: str
    extensions: frozenset[str]
    capabilities: frozenset[str]
    def supports(self, source: Path, requirements: set[str]) -> bool:
        return source.suffix.lower() in self.extensions and requirements <= self.capabilities
    def extract(self, source: Path, requirements: set[str] | None = None) -> dict[str, Any]:
        """Decode source-level facts into a small normalized evidence record."""
        requirements = requirements or set()
        if not self.supports(source, requirements):
            raise ValueError(f"adapter {self.id} does not support {source.suffix} with {sorted(requirements)}")
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        if self.id=="raster":
            with Image.open(source) as image:
                if image.width*image.height>50_000_000: raise ValueError("image exceeds 50 million pixel safety limit")
                image.load(); alpha=image.convert("RGBA").getchannel("A")
                alpha_bbox=alpha.getbbox()
                return {"adapter":self.id,"version":self.version,"sha256":digest,"format":image.format,
                        "width":image.width,"height":image.height,"mode":image.mode,
                        "alpha_present":"A" in image.getbands() or "transparency" in image.info,
                        "alpha_bbox":list(alpha_bbox) if alpha_bbox is not None else None}
        if self.id=="svg":
            root=ET.parse(source).getroot()
            return {"adapter":self.id,"version":self.version,"sha256":digest,"format":"SVG",
                    "viewBox":root.attrib.get("viewBox")}
        if self.id in {"game_trace","godot_trace","unity_trace"}:
            from .game import load_trace
            trace=load_trace(source); engine=trace.engine
            if (self.id=="godot_trace" and engine!="godot") or (self.id=="unity_trace" and engine!="unity"):
                raise ValueError(f"{self.id} cannot read engine={engine}")
            return {"adapter":self.id,"version":self.version,"sha256":digest,"format":"GAME_TRACE_JSON",
                    "engine":engine,"engine_version":trace.engine_version,"schema_version":trace.schema_version,"timebase":trace.timebase,
                    "track_count":len(trace.tracks),"event_count":len(trace.events),"particle_count":len(trace.particles),
                    "contact_count":len(trace.contacts),"anchor_count":len(trace.anchors),"frame_count":len(trace.frames)}
        raise ValueError(f"adapter {self.id} has no extractor")

ADAPTERS={
    "raster":AdapterDescriptor("raster","1.0",frozenset({".png",".jpg",".jpeg",".webp"}),
        frozenset({"raster_pixels","alpha_channel","feature_mask","color_metrics","geometry_metrics","frequency_metrics"})),
    "svg":AdapterDescriptor("svg","1.0",frozenset({".svg"}),frozenset({"svg_structure","svg_path_geometry"})),
    "game_trace":AdapterDescriptor("game_trace","1.0",frozenset({".json"}),
        frozenset({"temporal_tracks","event_tracks","particle_tracks","pose_tracks","rotation_tracks","contact_tracks","frame_layers","alpha_channel","trace_schema_v1"})),
    "godot_trace":AdapterDescriptor("godot_trace","1.0",frozenset({".json"}),
        frozenset({"temporal_tracks","event_tracks","particle_tracks","pose_tracks","rotation_tracks","contact_tracks","frame_layers","alpha_channel","trace_schema_v1"})),
    "unity_trace":AdapterDescriptor("unity_trace","1.0",frozenset({".json"}),
        frozenset({"temporal_tracks","event_tracks","particle_tracks","pose_tracks","rotation_tracks","contact_tracks","frame_layers","alpha_channel","trace_schema_v1"})),
}
FEATURE_ADAPTERS={"mask":MaskFeatureAdapter()}
