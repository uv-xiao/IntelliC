from __future__ import annotations

import pytest

from htp.ir.frontends import FrontendSpec
from htp.ir.frontends.rules import FrontendBuildContext, FrontendRule, FrontendRuleResult
from htp.ir.program.module import ProgramModule


class DemoSurface:
    def __init__(self, entry: str) -> None:
        self.entry = entry


def test_frontend_rule_builds_program_module() -> None:
    def build_demo(context: FrontendBuildContext) -> FrontendRuleResult:
        module = ProgramModule.from_program_dict(
            {
                "entry": context.surface.entry,
                "canonical_ast": {
                    "schema": "htp.program_ast.v1",
                    "program": {"entry": context.surface.entry},
                },
                "kernel_ir": {},
                "workload_ir": {},
            },
            meta={"source_surface": "demo.rule"},
        )
        return FrontendRuleResult(module=module)

    spec = FrontendSpec(
        frontend_id="demo.surface",
        dialect_id="htp.core",
        surface_type=DemoSurface,
        rule=FrontendRule(name="build_demo", build=build_demo),
    )

    module = spec.build(DemoSurface("demo_entry"))

    assert isinstance(module, ProgramModule)
    assert module.to_state_dict()["entry"] == "demo_entry"
    assert module.meta["source_surface"] == "demo.rule"


def test_frontend_rule_rejects_non_program_module_results() -> None:
    def bad_build(context: FrontendBuildContext) -> FrontendRuleResult:
        return FrontendRuleResult(module={"bad": True})  # type: ignore[arg-type]

    spec = FrontendSpec(
        frontend_id="demo.bad",
        dialect_id="htp.core",
        surface_type=DemoSurface,
        rule=FrontendRule(name="bad_build", build=bad_build),
    )

    with pytest.raises(TypeError, match="ProgramModule"):
        spec.build(DemoSurface("broken"))
