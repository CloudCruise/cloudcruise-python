from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union

# COMPONENT_CALL type scaffold. Source of truth (copy from, do not diverge):
# monorepo packages/types/globalTypes/workflow/workflow-types.ts
# (ComponentReference, ComponentCallParameters, ComponentImport,
# ComponentDefinition, ComponentIOSchema). Names kept identical in spirit to the
# JS SDK types for cross-SDK symmetry. Implementation gated until the API
# contract locks.

ComponentVersionRef = Union[int, str]  # positive int (pin) | "latest"

ComponentIOSchema = Dict[str, Any]  # JSON-Schema; credential params use x-cc-type: "credential"


@dataclass
class ComponentReference:
    type: Literal["global", "local"]
    ref: str
    version: Optional[ComponentVersionRef] = None


@dataclass
class ComponentCallParameters:
    component: ComponentReference
    arguments: Dict[str, str]
    output_mappings: Optional[Dict[str, str]] = None
    allowed_components: Optional[List[ComponentReference]] = None


@dataclass
class ComponentCallNode:
    id: str
    name: str
    action: str  # "COMPONENT_CALL"
    parameters: ComponentCallParameters
    description: Optional[str] = None


@dataclass
class ComponentImport:
    id: str
    version: ComponentVersionRef
    alias: Optional[str] = None


@dataclass
class ComponentVaultSchemaCredential:
    type: str  # "credential"
    domain: str
    example: Optional[str] = None


@dataclass
class ComponentDefinition:
    id: str
    name: str
    nodes: List[Dict[str, Any]]
    edges: Dict[str, Any]
    input_schema: Optional[ComponentIOSchema] = None
    output_schema: Optional[ComponentIOSchema] = None
    vault_schema: Optional[Dict[str, ComponentVaultSchemaCredential]] = None
    popup_xpaths: Optional[List[str]] = None
