import json

from htp.passes.contracts import AnalysisOutput, PassContract


def test_analysis_pass_declares_outputs_and_preserves_ast():
    contract = PassContract.analysis(
        pass_id="pkg::warp_role_plan@1",
        owner="pkg",
        provides=("Analysis.WarpRolePlan@1",),
        analysis_produces=(
            AnalysisOutput(
                analysis_id="pkg::WarpRolePlan@1",
                schema="htp.analysis.warp_role_plan.v1",
                path_hint="analysis/warp_role_plan.json",
            ),
        ),
        outputs=("analysis.index", "analysis.result"),
    )

    assert contract.kind == "analysis"
    assert contract.ast_effect == "preserves"
    assert contract.outputs == ("analysis.index", "analysis.result")
    assert contract.analysis_produces == (
        AnalysisOutput(
            analysis_id="pkg::WarpRolePlan@1",
            schema="htp.analysis.warp_role_plan.v1",
            path_hint="analysis/warp_role_plan.json",
        ),
    )
    assert json.loads(json.dumps(contract.to_json())) == {
        "schema": "htp.pass_contract.v1",
        "pass_id": "pkg::warp_role_plan@1",
        "owner": "pkg",
        "kind": "analysis",
        "ast_effect": "preserves",
        "requires": [],
        "provides": ["Analysis.WarpRolePlan@1"],
        "invalidates": [],
        "requires_layout_invariants": [],
        "requires_effect_invariants": [],
        "establishes_layout_invariants": [],
        "establishes_effect_invariants": [],
        "analysis_requires": [],
        "analysis_produces": [
            {
                "analysis_id": "pkg::WarpRolePlan@1",
                "schema": "htp.analysis.warp_role_plan.v1",
                "path_hint": "analysis/warp_role_plan.json",
            }
        ],
        "inputs": [],
        "outputs": ["analysis.index", "analysis.result"],
        "runnable_py": {
            "status": "preserves",
            "modes": ["sim"],
        },
        "deterministic": True,
        "diagnostics": [],
    }
