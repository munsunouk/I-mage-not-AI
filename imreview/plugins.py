"""Explicitly allowlisted, in-process extension contracts; no plugin discovery/loading."""
from __future__ import annotations

import json
import hashlib
import os
import re
import stat
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

PLUGIN_API_VERSION="1"
_ID=re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")


class PluginDescriptor(BaseModel):
    """Metadata supplied by a trusted host before it imports plugin code."""
    model_config=ConfigDict(extra="forbid", frozen=True)
    plugin_id: str
    algorithm_id: str
    version: str
    api_version: str=PLUGIN_API_VERSION
    sha256: str=Field(pattern=r"^[0-9a-f]{64}$")
    capabilities: frozenset[str]=frozenset()

    @model_validator(mode="after")
    def validate_contract(self):
        if not _ID.fullmatch(self.plugin_id) or not _ID.fullmatch(self.algorithm_id):
            raise ValueError("plugin_id and algorithm_id must be stable lowercase identifiers")
        if self.api_version!=PLUGIN_API_VERSION: raise ValueError(f"unsupported plugin API version {self.api_version}")
        if not self.version.strip(): raise ValueError("plugin algorithm version must be non-empty")
        return self


@runtime_checkable
class AlgorithmPlugin(Protocol):
    plugin_id: str
    algorithm_id: str
    version: str
    capabilities: frozenset[str]
    def supports(self, evidence_type: str, requirements: frozenset[str]) -> bool: ...
    def measure(self, evidence: Mapping[str,Any], parameters: Mapping[str,Any]) -> Mapping[str,Any]: ...


def verify_plugin_file(path:Path, plugin_id:str, trusted_hashes:Mapping[str,str], max_bytes:int=1_000_000)->str:
    """Check a regular local plugin file against an explicit digest allowlist."""
    if plugin_id not in trusted_hashes: raise ValueError(f"plugin {plugin_id} is not allowlisted")
    try:
        descriptor=os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
        with os.fdopen(descriptor,"rb") as source:
            info=os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size>max_bytes: raise ValueError("plugin source must be a regular file within the size limit")
            digest=hashlib.sha256(source.read(max_bytes+1)).hexdigest()
    except OSError as exc: raise ValueError(f"cannot read plugin source: {exc}") from exc
    if digest!=trusted_hashes[plugin_id].lower(): raise ValueError(f"plugin {plugin_id} digest does not match allowlist")
    return digest


class PluginRegistry:
    """Registry that executes only objects explicitly supplied by a trusted host.

    The core CLI never discovers Python modules. The host must import an extension,
    provide its approved digest, and name its plugin ID in ``trusted_hashes`` first.
    """
    def __init__(self, trusted_hashes: Mapping[str,str]|None=None, builtin_algorithms: frozenset[str]=frozenset()):
        self._trusted={key:value.lower() for key,value in (trusted_hashes or {}).items()}
        self._builtins=builtin_algorithms
        self._plugins:dict[str,tuple[PluginDescriptor,AlgorithmPlugin]]={}

    def register(self, descriptor: PluginDescriptor, plugin: AlgorithmPlugin) -> None:
        if descriptor.plugin_id not in self._trusted:
            raise ValueError(f"plugin {descriptor.plugin_id} is not allowlisted")
        if self._trusted[descriptor.plugin_id]!=descriptor.sha256:
            raise ValueError(f"plugin {descriptor.plugin_id} digest does not match allowlist")
        if descriptor.plugin_id in self._plugins: raise ValueError(f"plugin already registered: {descriptor.plugin_id}")
        if descriptor.algorithm_id in self._builtins or any(d.algorithm_id==descriptor.algorithm_id for d,_ in self._plugins.values()):
            raise ValueError(f"algorithm ID is already registered: {descriptor.algorithm_id}")
        if any(not hasattr(plugin,name) for name in ("plugin_id","algorithm_id","version","capabilities")):
            raise ValueError("plugin is missing required descriptor metadata")
        if (plugin.plugin_id,plugin.algorithm_id,plugin.version,frozenset(plugin.capabilities)) != (
                descriptor.plugin_id,descriptor.algorithm_id,descriptor.version,descriptor.capabilities):
            raise ValueError("plugin object metadata does not match its descriptor")
        if not callable(getattr(plugin,"supports",None)) or not callable(getattr(plugin,"measure",None)):
            raise ValueError("plugin must implement supports() and measure()")
        self._plugins[descriptor.algorithm_id]=(descriptor,plugin)

    def resolve(self, algorithm_id: str) -> tuple[PluginDescriptor,AlgorithmPlugin]|None:
        return self._plugins.get(algorithm_id)

    def measure(self, algorithm_id: str, evidence_type: str, evidence: Mapping[str,Any],
                parameters: Mapping[str,Any], requirements: frozenset[str]=frozenset()) -> dict[str,Any]:
        item=self.resolve(algorithm_id)
        if item is None: raise KeyError(f"plugin algorithm is not registered: {algorithm_id}")
        descriptor,plugin=item
        if not requirements<=descriptor.capabilities: raise ValueError("plugin does not provide required capabilities")
        if not plugin.supports(evidence_type,requirements): raise ValueError("plugin does not support this evidence")
        try: result=dict(plugin.measure(evidence,parameters))
        except Exception as exc: raise ValueError(f"plugin measurement failed: {exc}") from exc
        if not result: raise ValueError("plugin measurement result must not be empty")
        try: serialized=json.dumps(result,allow_nan=False)
        except (TypeError,ValueError) as exc: raise ValueError("plugin result must be finite JSON data") from exc
        if len(serialized.encode("utf-8"))>1_000_000: raise ValueError("plugin result exceeds 1 MiB")
        return {"algorithm_id":descriptor.algorithm_id,"algorithm_version":descriptor.version,
                "plugin_id":descriptor.plugin_id,"plugin_api_version":descriptor.api_version,"measured":json.loads(serialized)}

    @property
    def registered_algorithms(self)->tuple[str,...]:
        return tuple(sorted(self._plugins))
