"""Core typed IR substrate."""

from .analysis import AnalysisRecord, analysis_record_from_payload
from .aspects import EffectsAspect, LayoutAspect, ScheduleAspect, TypesAspect
from .identity import BindingTable, EntityTable, RewriteMap
from .ids import BindingRegistry, EntityRegistry, binding_id, entity_id, node_id
from .layout import DistributionFacet
from .maps import BindingMap, EntityMap
from .semantics import KernelIR, WorkloadIR

__all__ = [
    "AnalysisRecord",
    "BindingMap",
    "BindingRegistry",
    "BindingTable",
    "DistributionFacet",
    "EffectsAspect",
    "EntityMap",
    "EntityRegistry",
    "EntityTable",
    "KernelIR",
    "LayoutAspect",
    "RewriteMap",
    "ScheduleAspect",
    "TypesAspect",
    "WorkloadIR",
    "analysis_record_from_payload",
    "binding_id",
    "entity_id",
    "node_id",
]
