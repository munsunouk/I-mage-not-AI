"""Typed, versioned manifest and evidence contracts."""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Origin = Literal["user_spec", "project_config", "source_native", "agent_inferred"]

class Provenance(BaseModel):
    model_config = ConfigDict(extra="allow")
    origin: Origin

class AssetRef(BaseModel):
    model_config = ConfigDict(extra="allow")
    path: str
    id: str | None = None
    format: str | None = None
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")

class FeatureGeometry(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    path: str | None = None

class Feature(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(min_length=1)
    role: str
    parent_id: str | None = None
    geometry: FeatureGeometry | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance | None = None

class FeatureManifest(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: Literal["0.1", "0.5"]
    asset: AssetRef
    features: list[Feature]
    intent: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    overlap_constraints: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_feature_relations(self):
        if self.schema_version == "0.5" and not self.asset.sha256:
            raise ValueError("schema_version 0.5 requires asset.sha256")
        ids=[feature.id for feature in self.features]
        if len(ids)!=len(set(ids)): raise ValueError("feature IDs must be unique")
        known=set(ids)
        for feature in self.features:
            if feature.parent_id is not None and feature.parent_id not in known:
                raise ValueError(f"feature {feature.id}: unknown parent_id {feature.parent_id}")
        return self

class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str | None = None
    source_sha256: str
    data_type: str
    coordinate_system: str | None = None
    color_space: str | None = None
    unit: str | None = None
    provenance: Origin
    adapter_id: str
    adapter_version: str

class ReviewFinding(BaseModel):
    model_config = ConfigDict(extra="allow")
    rule_id: str
    feature_id: str | None = None
    status: Literal["PASS", "FAIL", "INCONCLUSIVE", "SKIPPED"]
    algorithm: str
    measured: Any
    threshold: Any = None
    formula: str
    region: Any = None

class TemporalSample(BaseModel):
    """Reusable typed temporal evidence record; the executable JSON trace is in game.py."""
    model_config = ConfigDict(extra="forbid")
    frame_index: int | None = None
    timestamp: float
    timebase: str
    coordinate_system: str
    units: str
    transform_hierarchy: list[str] = Field(default_factory=list)
    interpolation_policy: str
    random_seed: int | None = None
    value: Any

class TemporalTrack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str
    samples: list[TemporalSample]

class EventTrack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str
    events: list[TemporalSample]

class ParticleTrack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str
    spawn: TemporalSample
    death: TemporalSample | None = None
